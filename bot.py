import asyncio
import datetime
import random
import html

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gifts import calculate_gift_code, get_gift_info
from config import BOT_TOKEN, CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура стартового меню
start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎂 Дар по дате рождения", callback_data="by_date")],
    [InlineKeyboardButton(text="🌞 Дар дня", callback_data="today_gift")],
    [InlineKeyboardButton(text="🌌 Энергия дня", callback_data="energy_gift")]
])

# /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Добро пожаловать!\nВыбери, что хочешь узнать:", reply_markup=start_kb)

# /force_send — ручной запуск рассылки
@dp.message(Command("force_send"))
async def force_send(message: types.Message):
    await send_daily_gift_to_channel()
    await message.answer("📤 Дар дня отправлен в канал.")

# Обработка кнопок
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    if callback.data == "by_date":
        await callback.message.answer("✏️ Напиши дату рождения в формате ДД.ММ.ГГГГ")
    elif callback.data == "today_gift":
        today = datetime.date.today()
        await send_gift(callback.message, day=today.day, month=today.month, year=today.year, title="🌞 Дар дня")
    elif callback.data == "energy_gift":
        a, b = random.randint(1, 9), random.randint(1, 9)
        c = reduce_to_single_digit(a + b)
        code = f"{a}-{b}-{c}"
        await send_gift(callback.message, code=code, title="🌌 Энергия дня")
    await callback.answer()

# Обработка даты
@dp.message(F.text.regexp(r"^\d{1,2}\.\d{1,2}\.\d{4}$"))
async def handle_date(message: types.Message):
    try:
        day, month, year = map(int, message.text.split("."))
    except Exception:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
        return
    await send_gift(message, day=day, month=month, year=year, title="🎁 Твой дар")

# Заглушка
@dp.message()
async def catch_all(message: types.Message):
    await message.answer("😅 Я тебя не понял. Используй кнопки или напиши дату рождения в формате ДД.ММ.ГГГГ")

# Отправка дара пользователю
async def send_gift(message, day=None, month=None, year=None, title="Дар", code=None):
    if code is None:
        code = calculate_gift_code(day, month, year)
    gift = get_gift_info(code)

    if not gift:
        await message.answer(f"⚠️ Дар с кодом {code} пока не найден.")
        return

    try:
        name = html.escape(gift.get("name", ""))
        ma_ji_kun = html.escape(gift.get("ma_ji_kun", ""))
        description = html.escape(gift.get("description", ""))
        caption = f"<b>{title}: {name}</b>\n\n{ma_ji_kun}\n\n{description}"

        if gift.get("getgems_url"):
            caption += f"\n\n<a href=\"{html.escape(gift['getgems_url'])}\">Узнать подробнее</a>"

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=gift["image_url"],
            caption=caption,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[Ошибка отправки дара] {e}")
        await message.answer("⚠️ Не удалось отправить изображение дара.")

# Автоматическая рассылка дара дня в канал
def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="UTC")

    # 5:00 UTC = 9:00 по Тбилиси
    @scheduler.scheduled_job("cron", hour=5, minute=0)
    async def scheduled_send():
        await send_daily_gift_to_channel()

    scheduler.start()

# Функция отправки дара дня в канал
async def send_daily_gift_to_channel():
    today = datetime.date.today()
    code = calculate_gift_code(today.day, today.month, today.year)
    gift = get_gift_info(code)

    if not gift:
        print(f"[AUTO] Дар не найден: {code}")
        return

    try:
        name = html.escape(gift.get("name", ""))
        ma_ji_kun = html.escape(gift.get("ma_ji_kun", ""))
        description = html.escape(gift.get("description", ""))
        caption = f"<b>🌞 Дар дня: {name}</b>\n\n{ma_ji_kun}\n\n{description}\n\nВ <a href=\"https://t.me/yup64dara_bot\">боте</a> вы можете узнать больше о дарах"

        if gift.get("getgems_url"):
            caption += f"\n\n<a href=\"{html.escape(gift['getgems_url'])}\">Узнать подробнее</a>"

        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=gift["image_url"],
            caption=caption,
            parse_mode="HTML"
        )
        print("📤 Дар дня отправлен в канал.")
    except Exception as e:
        print(f"[AUTO ERROR] {e}")

# Утилита: сведение числа к одной цифре
def reduce_to_single_digit(num):
    while num > 9:
        num = sum(int(d) for d in str(num))
    return num

# Запуск бота
async def main():
    setup_scheduler()
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)
