import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8834233399:AAFw-byiVENh_IXXasYCzHP0wSHPILfH18M"
GROUP_ID = -1004487553351  # ID твоей группы
ADMIN_ID = 1061986288      # Твой Telegram ID
EXAMPLE_PHOTO_PATH = "example.jpg"  # Файл с примером кабинета в папке проекта
# ===================================================

# Логирование только предупреждений и ошибок
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

# Проверка: состоит ли пользователь уже в группе
async def is_user_in_group(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        # Статусы "creator", "administrator", "member" означают, что человек уже в группе
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception:
        pass
    return False


# 1. Если человек зашел в бота и нажал /start (ТОЛЬКО В ЛС)
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


# 2. Если человек подал заявку в группу (бот сам пишет первым с примером в ЛС)
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


# 3. Прием фото или документа (ТОЛЬКО В ЛС И ТОЛЬКО ОТ ТЕХ, КОГО НЕТ В ГРУППЕ)
@dp.message((F.photo | F.document), F.chat.type == "private")
async def handle_photo(message: types.Message):
    user = message.from_user

    # Если человек уже в группе — игнорируем фото и не спамим админу
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


# 4. Прием текста (ТОЛЬКО В ЛС И ТОЛЬКО ОТ ТЕХ, КОГО НЕТ В ГРУППЕ)
@dp.message(F.text, F.chat.type == "private")
async def handle_text(message: types.Message):
    user = message.from_user

    # Если человек уже в группе — игнорируем сообщение и не спамим админу
    if await is_user_in_group(user.id):
        await message.answer("Ви вже є учасником групи! Якщо у вас виникли питання, пишіть контакту з опису.")
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

        await callback.answer("Заявка одобрена!")

    except Exception:
        await callback.answer(
            "⚠️ Ошибка: Активной заявки нет (пользователь уже в группе или отозвал заявку).",
            show_alert=True
        )


# 6. Отклонение заявки админом
@dp.callback_query(F.data.startswith("decline:"))
async def decline_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        await bot.decline_chat_join_request(chat_id=GROUP_ID, user_id=user_id)

        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ На жаль, ваша заявка відхилена. Перевірте інформацію та спробуйте ще раз."
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

    except Exception:
        await callback.answer(
            "⚠️ Ошибка: Активной заявки на вступление нет.",
            show_alert=True
        )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())