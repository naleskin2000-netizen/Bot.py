import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

BOT_TOKEN = "9165469558:AAFkzyUjnbx6QmWQ21y4OzAYOKzaOgB4Uq4" 
WEBAPP_URL = "https://naleskin2000-netizen.github.io/index.html/" 
ADMIN_ID = 8880934795  

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База данных
db = sqlite3.connect("/tmp/rubup_clone.db", check_same_thread=False) # /tmp/ чтобы Render не удалял базу
db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000)")
db.commit()

def get_balance(uid):
    row = db.execute("SELECT balance FROM users WHERE tg_id = ?", (uid,)).fetchone()
    if not row:
        db.execute("INSERT INTO users (tg_id, balance) VALUES (?, ?)", (uid, 1000))
        db.commit()
        return 1000
    return row[0]

def add_balance(uid, amount):
    get_balance(uid) 
    db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, uid))
    db.commit()

# --- ВЕБ-СЕРВЕР ДЛЯ ИГРЫ (API) ---
async def api_get_balance(request):
    uid = request.query.get('user_id')
    if not uid: return web.json_response({"error": "no id"}, status=400)
    bal = get_balance(int(uid))
    return web.json_response({"balance": bal})

async def api_play(request):
    data = await request.json()
    uid = data.get('user_id')
    cost = data.get('cost', 100)
    
    current_bal = get_balance(int(uid))
    if current_bal < cost:
        return web.json_response({"success": False, "msg": "Недостаточно звезд", "balance": current_bal})
    
    add_balance(int(uid), -cost)
    # Здесь можно добавить логику выпадения предмета и его сохранения
    return web.json_response({"success": True, "balance": current_bal - cost})

# --- БОТ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    balance = get_balance(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer(f"👋 Твой баланс: <b>{balance}</b> ⭐\n\nКрути кейсы!", reply_markup=kb)

async def main():
    # Запускаем веб-сервер для API параллельно с ботом
    app = web.Application()
    app.router.add_get('/api/balance', api_get_balance)
    app.router.add_post('/api/play', api_play)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"API запущено на порту {port}")

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

