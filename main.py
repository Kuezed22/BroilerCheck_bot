import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiohttp import web

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8834233399:AAFw-byiVENh_IXXasYCzHP0wSHPILfH18M"
GROUP_ID = -1004487553351  # ID твоей группы
ADMIN_ID = 1061986288      # Твой Telegram ID
EXAMPLE_PHOTO_PATH = "example.jpg"  # Файл с примером кабинета в папке проекта
# ===================================================

logging.basicConfig(level=logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TEXT_INSTRUCTION = (
    "Привіт! 👋\n\n"
    "Щоб отримати доступ до групи першокурсників, "
    "<b>надішли сюди фото або скріншот</b> свого профілю абітурієнта.\n\n"
    "👆 <i>Приклад того, як має виглядати ваш профіль, показано на фото вище. "
    "Стрілочками показано що має бути обов'язково на фото — це дата підтвердження та час, "
    "всі інші дані можете замазати.</i>\n\n"
    "❓ Якщо виникли питання або проблеми з входом — пиши: @Kueze_d"
)

# Проверка участника в группе
async def is_user_in_group(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception:
        pass
    return False

# 1. /start
@dp.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message):
    if await is_user_in_group(message.from_user.id):
        await message.answer("Ви вже є учасником групи! 🎉")
        return

    try:
        photo = FSInputFile(EXAMPLE_PHOTO_PATH)
        await message.answer_photo(
            photo=photo,
            caption=TEXT_INSTRUCTION,
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(TEXT_INSTRUCTION, parse_mode="HTML")

# 2. Заявка на вступ
@dp.chat_join_request()
async def on_join_request(request: types.ChatJoinRequest):
    if await is_user_in_group(request.from_user.id):
        return

    try:
        photo = FSInputFile(EXAMPLE_PHOTO_PATH)
        await bot.send_photo(
            chat_id=request.from_user.id,
            photo=photo,
            caption=TEXT_INSTRUCTION,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не вдалося надіслати повідомлення {request.from_user.id}: {e}")

# 3. Прием фото
@dp.message((F.photo | F.document), F.chat.type == "private")
async def handle_photo(message: types.Message):
    user = message.from_user

    if await is_user_in_group(user.id):
        await message.answer("Ви вже є учасником групи! Повторно надсилати фото не потрібно.")
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        is_document = False
    else:
        file_id = message.document.file_id
        is_document = True

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{user.id}")
        ]
    ])

    user_caption = f"\n<b>Подпись:</b> {message.caption}" if message.caption else ""

    caption = (
        f"📩 <b>Новая заявка (ФОТО)!</b>\n\n"
        f"<b>Студент:</b> {user.full_name}\n"
        f"<b>Юзернейм:</b> @{user.username or 'отсутствует'}\n"
        f"<b>ID:</b> <code>{user.id}</code>"
        f"{user_caption}"
    )

    if is_document:
        await bot.send_document(
            chat_id=ADMIN_ID,
            document=file_id,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )

    await message.answer("Дякуємо! Фото надіслано на перевірку. Чекайте на затвердження заявки.")

# 4. Прием текста
@dp.message(F.text, F.chat.type == "private")
async def handle_text(message: types.Message):
    user = message.from_user

    if await is_user_in_group(user.id):
        await message.answer("Ви вже є учасником групи! Якщо виникли питання, пишіть контакту з опису.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{user.id}")
        ]
    ])

    text_to_admin = (
        f"📩 <b>Новая заявка (ТЕКСТ)!</b>\n\n"
        f"<b>Студент:</b> {user.full_name}\n"
        f"<b>Юзернейм:</b> @{user.username or 'отсутствует'}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n\n"
        f"<b>Текст сообщения:</b>\n{message.text}"
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=text_to_admin,
        reply_markup=kb,
        parse_mode="HTML"
    )

    await message.answer("Дякуємо! Ваше повідомлення надіслано на перевірку. Чекайте на рішення.")

# 5. Одобрение заявки админом
@dp.callback_query(F.data.startswith("approve:"))
async def approve_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        await bot.approve_chat_join_request(chat_id=GROUP_ID, user_id=user_id)
        try:
            await bot.send_message(
                chat_id=user_id,
                text="🎉 Ваша заявка схвалена! Ласкаво просимо до групи."
            )
        except Exception:
            pass
    except Exception:
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=GROUP_ID,
                member_limit=1
            )
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 Ваша заявка схвалена! Ось ваше особисте посилання для входу в групу:\n{invite_link.invite_link}"
            )
        except Exception as e:
            await callback.answer(f"⚠️ Не вдалося надіслати посилання: {e}", show_alert=True)
            return

    if callback.message.caption:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text=callback.message.text + "\n\n✅ <b>ОДОБРЕНО</b>",
            reply_markup=None,
            parse_mode="HTML"
        )

    await callback.answer("Успешно одобрено!")

# 6. Отклонение заявки админом
@dp.callback_query(F.data.startswith("decline:"))
async def decline_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        await bot.decline_chat_join_request(chat_id=GROUP_ID, user_id=user_id)
    except Exception:
        pass

    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ На жаль, ваша заявка відхилена, перевірте чи все правильно на фото."
        )
    except Exception:
        pass

    if callback.message.caption:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text=callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>",
            reply_markup=None,
            parse_mode="HTML"
        )

    await callback.answer("Заявка отклонена!")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
