import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9165469558:AAFkzyUjnbx6QmWQ21y4OzAYOKzaOgB4Uq4" 
WEBAPP_URL = "https://naleskin2000-netizen.github.io/index.html/" 
ADMIN_ID = 8880934795  

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- База данных ---
db = sqlite3.connect("rubup_clone.db")
db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0
    )
""")
db.commit()

def get_balance(uid):
    row = db.execute("SELECT balance FROM users WHERE tg_id = ?", (uid,)).fetchone()
    if not row:
        db.execute("INSERT INTO users (tg_id, balance) VALUES (?, ?)", (uid, 0))
        db.commit()
        return 0
    return row[0]

def add_balance(uid, amount):
    get_balance(uid) 
    db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, uid))
    db.commit()

PACKAGES = {
    "pack10": {"real": 10, "virtual": 1000, "title": "1 000 ⭐"},
    "pack50": {"real": 50, "virtual": 5000, "title": "5 000 ⭐"},
    "pack5000": {"real": 5000, "virtual": 500000, "title": "500 000 ⭐"},
}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    balance = get_balance(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="show_packages")],
        [InlineKeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Твой текущий баланс: <b>{balance}</b> ⭐\n\n"
        f"Пополни баланс, чтобы крутить кейсы:",
        reply_markup=kb
    )

@dp.message(Command("balance"))
async def admin_give_balance(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ У вас нет прав для этой команды.")

    args = message.text.split()
    if len(args) != 3:
        return await message.answer("⚠️ Неверный формат.\nИспользование: <code>/balance ID СУММА</code>")

    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        return await message.answer("⚠️ ID и сумма должны быть числами.")

    add_balance(target_id, amount)
    new_balance = get_balance(target_id)

    await message.answer(f"✅ Успешно!\nПользователю <code>{target_id}</code> начислено <b>{amount} ⭐</b>.\nЕго текущий баланс: <b>{new_balance} ⭐</b>.")
    
    try:
        await bot.send_message(target_id, f"🎁 Вам начислено <b>{amount} ⭐</b> от администратора!")
    except Exception:
        pass 

@dp.callback_query(F.data == "show_packages")
async def show_packages(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['title']} за {p['real']} Stars", callback_data=f"buy_{k}")]
        for k, p in PACKAGES.items()
    ])
    await c.message.edit_text("Выбери пакет пополнения:", reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(c: CallbackQuery):
    pack_key = c.data.split("_")[1]
    pack = PACKAGES.get(pack_key)
    if not pack: return await c.answer("Пакет не найден")

    await c.answer()
    await bot.send_invoice(
        chat_id=c.from_user.id,
        title=f"Пополнение: {pack['title']}",
        description="Внутренняя валюта для игры",
        payload=f"topup_{pack_key}",
        provider_token="", 
        currency="XTR", 
        prices=[LabeledPrice(label="Пакет", amount=pack['real'])],
    )

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@dp.message(F.successful_payment)
async def on_payment(m: Message):
    payload = m.successful_payment.invoice_payload
    pack_key = payload.split("_")[1]
    pack = PACKAGES[pack_key]
    
    uid = m.from_user.id
    add_balance(uid, pack["virtual"])
    new_balance = get_balance(uid)
    
    await m.answer(
        f"✅ <b>Оплата получена!</b>\n"
        f"Зачислено: {pack['virtual']} ⭐\n"
        f"Твой новый баланс: {new_balance} ⭐\n\n"
        f"Возвращайся в игру!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 В игру", web_app=WebAppInfo(url=WEBAPP_URL))]
        ])
    )

async def main():
    print("Бот запущен...")
    # Render требует, чтобы бот не завершался и слушал порт
    port = int(os.environ.get("PORT", 8080))
    from aiohttp import web
    async def handle(request):
        return web.Response(text="Bot is running")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
