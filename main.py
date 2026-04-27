import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import random
import string
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiocryptopay import AioCryptoPay

class DepositState(StatesGroup):
    choosing_currency = State()
    entering_amount = State()

class OrderState(StatesGroup):
    entering_custom_quantity = State()

class AdminState(StatesGroup):
    waiting_for_reject_reason = State()
    waiting_for_broadcast_text = State()
    in_active_chat = State()

def add_deposit_to_db(user_id, amount, currency, comment):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO deposits (user_id, amount, currency, comment, status) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, currency, comment, 'pending')
    )
    conn.commit()
    conn.close()


def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            orders_count INTEGER DEFAULT 0,
            reg_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            admin_name TEXT,
            action_type TEXT,
            target_user_id INTEGER,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            total_price REAL,
            status TEXT DEFAULT 'pending', -- pending, completed
            chat_status INTEGER DEFAULT 0 -- 0 - закрыт, 1 - открыт
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            currency TEXT,
            comment TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()
def get_user(user_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id):
    if not get_user(user_id):
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        reg_date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute('INSERT INTO users (user_id, reg_date) VALUES (?, ?)', (user_id, reg_date))
        conn.commit()
        conn.close()
def add_order_to_db(user_id, item_name, price, quantity, total):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    cur.execute(
        "INSERT INTO orders (user_id, item_name, price, quantity, total, date) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, item_name, price, quantity, total, date_str)
    )
    conn.commit()
    conn.close()

def add_log(admin_id, admin_name, action_type, target_user_id, details):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (admin_id, admin_name, action_type, target_user_id, details) VALUES (?, ?, ?, ?, ?)",
        (admin_id, admin_name, action_type, target_user_id, details)
    )
    conn.commit()
    conn.close()

def quantity_selection_kb(product_id):
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"confirm_buy_{product_id}_{i}")
    
    builder.adjust(5)
    builder.row(types.InlineKeyboardButton(text="Указать свое кол-во", callback_data=f"custom_qty_{product_id}"))
    builder.row(types.InlineKeyboardButton(text="Главное меню", callback_data="back_to_main"))
    return builder.as_markup()

init_db()


ADMIN_ID = 8774787211
TON_ADDRESS = "UQDvbbvy8MjF6j2N6WbfJBvthRjdznHtnHr6HkghMlIlJm68"
USD_TO_TON = 0.77
CHANNEL_ID = "@CrscShop"  
CHANNEL_URL = "https://t.me/CrscShop"


PRODUCTS = {
    "bank_1": {"name": "ЮMoney(Max LvL)", "price": 1.3, "emoji": "5893431652578758294"},
    "bank_2": {"name": "Цупи$", "price": 1.4, "emoji": "5893431652578758294"},
    "bank_3": {"name": "Wb Bank", "price": 2.0, "emoji": "5893431652578758294"},
    "bank_4": {"name": "Ya Pay", "price": 3.0, "emoji": "5893431652578758294"},
    "bank_5": {"name": "Vk Pay", "price": 2.5, "emoji": "5893431652578758294"},


    "exch_1": {"name": "Crypto Bot", "price": 8, "emoji": "5902002809573740949"},
    "exch_2": {"name": "Binance", "price": 8.0, "emoji": "5893072412924187198"},
    "exch_3": {"name": "Bybit", "price": 8.0, "emoji": "5893293174243201165"},
    "exch_4": {"name": "Tg Wallet", "price": 6.0, "emoji": "6039641775377748623"},
    "exch_5": {"name": "Okx", "price": 8.0, "emoji": "5895734085761896734"},
    "exch_6": {"name": "BitGet", "price": 8.0, "emoji": "6041705726206808304"},
    "exch_7": {"name": "CoinBase", "price": 8.0, "emoji": "5893365724830765382"},
    "exch_8": {"name": "Fragment", "price": 1.8, "emoji": "5893161718179173515"},
    "exch_9": {"name": "Mexc", "price": 8.0, "emoji": "5893168654551355607"},
    "exch_10": {"name": "Ru Akk Crypto Bot", "price": 10.0, "emoji": "5893365724830765382"},

    "man_1": {"name": "Аккаунты с рейтингом", "price": 1.0, "emoji": "5893185207355315979"},
    "man_2": {"name": "Звезды без верификации", "price": 0.5, "emoji": "5893034681636491040"},
    "man_3": {"name": "Создание своего тон домена", "price": 1.0, "emoji": "6039802097916974085"},

    "bet_1": {"name": "Par1", "price": 3.0, "emoji": "5902002809573740949"},
    "bet_2": {"name": "BetB00m", "price": 3.0, "emoji": "5893048571560726748"}
}




TOKEN = "8209584390:AAFRVsZ5BDb9GEzdAfmOI7Qp4ziI3IZ4zgI" 

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

init_db()


def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    
    builder.row(types.KeyboardButton(text="Каталог"))
    
    builder.row(
        types.KeyboardButton(text="Профиль"),
        types.KeyboardButton(text="Поддержка")
    )
    
    return builder.as_markup(resize_keyboard=True)

def support_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="Написать в поддержку", 
        url="https://t.me/CrscSupp")
    )
    builder.row(types.InlineKeyboardButton(
        text="Назад", 
        callback_data="back_to_main")
    )
    return builder.as_markup()

def catalog_categories_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Банки", callback_data="cat_banks"))
    builder.row(types.InlineKeyboardButton(text="Биржи", callback_data="cat_exchanges"))
    builder.row(types.InlineKeyboardButton(text="Мануалы", callback_data="cat_manuals"))
    builder.row(types.InlineKeyboardButton(text="Буkмеkерки", callback_data="cat_bet"))
    builder.row(types.InlineKeyboardButton(text="Главное меню", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def admin_panel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Заявки на пополнение", callback_data="admin_deposits_view_0")
    builder.row(types.InlineKeyboardButton(text="Заявки на покупку", callback_data="admin_orders_view_0"))
    builder.row(types.InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast"))
    builder.row(types.InlineKeyboardButton(text="Выгрузка логов", callback_data="admin_logs"))
    builder.row(types.InlineKeyboardButton(text="Закрыть", callback_data="back_to_main"))
    return builder.as_markup()

@dp.message(Command("admin"))
async def admin_main(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        f'<tg-emoji emoji-id="5877485980901971030">⚙️</tg-emoji> <b>Панель управления</b>',
        reply_markup=admin_panel_kb(),
        parse_mode="HTML"
    )




def deposit_currency_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="TON", callback_data="dep_TON"))
    builder.row(types.InlineKeyboardButton(text="USDT", callback_data="dep_USDT"))
    builder.row(types.InlineKeyboardButton(text="Назад", callback_data="back_to_profile"))
    return builder.as_markup()

def payment_kb(pay_url=None):
    builder = InlineKeyboardBuilder()
    if pay_url:
        builder.row(types.InlineKeyboardButton(text="Оплатить", url=pay_url))
    builder.row(types.InlineKeyboardButton(text="Я оплатил", callback_data="check_payment"))
    builder.row(types.InlineKeyboardButton(text="Назад", callback_data="top_up"))
    return builder.as_markup()

def subscribe_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Подписаться", url=CHANNEL_URL))
    builder.row(types.InlineKeyboardButton(text="Я подписался", callback_data="check_subscribe"))
    return builder.as_markup()

def profile_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Пополнить баланс", callback_data="top_up"))
    builder.row(types.InlineKeyboardButton(text="Мои покупки", callback_data="my_orders"))
    builder.row(types.InlineKeyboardButton(text="Главное меню", callback_data="back_to_main"))
    return builder.as_markup()

def products_numbers_kb(category_prefix, count):
    builder = InlineKeyboardBuilder()
    for i in range(1, count + 1):
        builder.button(text=str(i), callback_data=f"select_{category_prefix}_{i}")
    builder.adjust(5)
    builder.row(types.InlineKeyboardButton(text="Назад", callback_data="back_to_catalog"))
    return builder.as_markup()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear() 
    text = (f'<tg-emoji emoji-id="5967456680940671207">📂</tg-emoji> <b>Каталог</b>\n'
            f'<b>Выберите категорию:</b>')
    await callback.message.edit_text(text, reply_markup=catalog_categories_kb())
    await callback.answer()





CRYPTO_TOKEN = "572857:AA2awbWvaBlK6UDWBCGbbGITRcbRtRpR6nY"
crypto = AioCryptoPay(token=CRYPTO_TOKEN)

async def create_order(amount: float):
    invoice = await crypto.create_invoice(asset='USDT', amount=amount)
    return invoice.pay_url, invoice.invoice_id

async def check_order_status(invoice_id: int):
    invoices = await crypto.get_invoices(invoice_ids=invoice_id)
    if invoices:
        return invoices.status == 'paid'
    return False

async def check_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False
    

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    
    if not await check_subscription(message.from_user.id):
        text = (f'<tg-emoji emoji-id="6005775159384870794">🔔</tg-emoji> <b>Прежде чем пользоваться ботом,</b>\n'
                f'<b>подпишитесь на наш канал!</b>')
        await message.answer(text, reply_markup=subscribe_keyboard())
        return
    
    text = f'<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> <b>Добро пожаловать в магазин!</b>'
    await message.answer(text, reply_markup=main_menu_kb())

@dp.callback_query(F.data == "check_subscribe")
async def check_subscribe_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if await check_subscription(user_id):
        text = f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> <b>Спасибо за подписку!</b>\n\n' \
               f'<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> <b>Добро пожаловать в магазин!</b>'
        await callback.message.edit_text(text, reply_markup=None)
        await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())
    else:
        text = (f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Вы не подписались на канал!</b>\n\n'
                f'<tg-emoji emoji-id="6005775159384870794">🔔</tg-emoji> <b>Пожалуйста, подпишитесь и нажмите кнопку снова.</b>')
        await callback.message.answer(text, reply_markup=subscribe_keyboard())
    
    await callback.answer()

@dp.message(F.text == "Каталог")
async def show_catalog(message: types.Message):
    text = (f'<tg-emoji emoji-id="5967456680940671207">📂</tg-emoji> <b>Каталог</b>\n'
            f'<b>Выберите категорию:</b>')
    await message.answer(text, reply_markup=catalog_categories_kb())


@dp.callback_query(F.data == "cat_banks")
async def cat_banks(callback: types.CallbackQuery):
    text = (
        f'<tg-emoji emoji-id="6039641775377748623">💳</tg-emoji> <b>Банки ~ Кошельки</b>\n\n'
        f'<tg-emoji emoji-id="5893168654551355607">🔹</tg-emoji> <b>Товар выдается в формате Госуслуг: номер,пароль,ключ тотп</b>\n'
        f'<tg-emoji emoji-id="5893168654551355607">🔹</tg-emoji> <b>Гарантия 24 часа</b>\n'
        f'<tg-emoji emoji-id="5893168654551355607">🔹</tg-emoji> <b>Моментальная выдача</b>\n'
        f'<tg-emoji emoji-id="5893168654551355607">🔹</tg-emoji> <b>Верификацию выполняете самостоятельно</b>\n\n'
        f'<b>Выберите необходимый товар:</b>\n'
        f'1.<tg-emoji emoji-id="5893431652578758294">⭐</tg-emoji> <b>ЮMoney(Max LvL)</b> - 1.3$\n'
        f'2.<tg-emoji emoji-id="5893431652578758294">⭐</tg-emoji> <b>Цупи$</b> - 1.4$\n'
        f'3.<tg-emoji emoji-id="5893431652578758294">⭐</tg-emoji> <b>Wb Bank</b> - 2$\n'
        f'4.<tg-emoji emoji-id="5893431652578758294">⭐</tg-emoji> <b>Ya Pay</b> - 3$\n'
        f'5.<tg-emoji emoji-id="5893431652578758294">⭐</tg-emoji> <b>Vk Pay</b> - 2.5$'
    )
    await callback.message.edit_text(text, reply_markup=products_numbers_kb("bank", 5))

@dp.callback_query(F.data == "cat_exchanges")
async def cat_exchanges(callback: types.CallbackQuery):
    text = (
        f'<tg-emoji emoji-id="6039802097916974085">📈</tg-emoji> <b>КриптоБиржи ~ TG Сервисы</b>\n\n'
        f'<tg-emoji emoji-id="5893168654551355607">🔹</tg-emoji> <b>Верификации КриптоБирж и TG Сервисов для расширенных возможностей по доступным ценам и хорошей гарантией</b>\n\n'
        f'<b>Выберите необходимый товар:</b>\n'
        f'1.<tg-emoji emoji-id="5902002809573740949">💰</tg-emoji> <b>Crypto Bot</b> - <b>8$</b>\n'
        f'2.<tg-emoji emoji-id="5893072412924187198">💰</tg-emoji> <b>Binance</b> - <b>8$</b>\n'
        f'3.<tg-emoji emoji-id="5893293174243201165">💰</tg-emoji> <b>Bybit</b> - <b>8$</b>\n'
        f'4.<tg-emoji emoji-id="6039641775377748623">💰</tg-emoji> <b>Tg Wallet</b> - <b>6$</b>\n'
        f'5.<tg-emoji emoji-id="5895734085761896734">💰</tg-emoji> <b>Okx</b> - <b>8$</b>\n'
        f'6.<tg-emoji emoji-id="6041705726206808304">💰</tg-emoji> <b>BitGet</b> - <b>8$</b>\n'
        f'7.<tg-emoji emoji-id="5893365724830765382">💰</tg-emoji> <b>CoinBase</b> - <b>8$</b>\n'
        f'8.<tg-emoji emoji-id="5893161718179173515">💰</tg-emoji> <b>Fragment</b> - <b>1.8$</b>\n'
        f'9.<tg-emoji emoji-id="5893168654551355607">💰</tg-emoji> <b>Mexc</b> - <b>8$</b>\n'
        f'10.<tg-emoji emoji-id="5893365724830765382">💰</tg-emoji> <b>Ru Akk Crypto Bot</b> - <b>10$</b>'
    )
    await callback.message.edit_text(text, reply_markup=products_numbers_kb("exch", 10))
    await callback.answer()

@dp.callback_query(F.data == "cat_manuals")
async def cat_manuals(callback: types.CallbackQuery):
    text = (
        f'<tg-emoji emoji-id="5893255507380014983">📖</tg-emoji> <b>Мануалы</b>\n\n'
        f'<b>Выберите необходимый товар:</b>\n'
        f'1.<tg-emoji emoji-id="5893185207355315979">📕</tg-emoji> <b>Аккаунты с рейтингом</b> - <b>1$</b>\n'
        f'2.<tg-emoji emoji-id="5893034681636491040">📕</tg-emoji> <b>Звезды без верификации</b> - <b>0.5$</b>\n'
        f'3.<tg-emoji emoji-id="6039802097916974085">📕</tg-emoji> <b>Создание своего тон домена</b> - <b>1$</b>'
    )
    await callback.message.edit_text(text, reply_markup=products_numbers_kb("man", 3))
    await callback.answer()

@dp.callback_query(F.data == "cat_bet")
async def cat_bet(callback: types.CallbackQuery):
    text = (
        f'<tg-emoji emoji-id="5902002809573740949">🎯</tg-emoji> <b>Букмекерские конторы</b>\n\n'
        f'<b>Выберите необходимый товар:</b>\n'
        f'1.<tg-emoji emoji-id="5902002809573740949">💵</tg-emoji> <b>Par1</b> - <b>3$</b>\n'
        f'2.<tg-emoji emoji-id="5893048571560726748">💵</tg-emoji> <b>BetB00m</b> - <b>3$</b>'
    )
    await callback.message.edit_text(text, reply_markup=products_numbers_kb("bet", 2))
    await callback.answer()

@dp.callback_query(F.data.startswith("select_"))
async def select_product(callback: types.CallbackQuery):
    product_id = callback.data.replace("select_", "") 
    product = PRODUCTS.get(product_id)

    if not product:
        return await callback.answer("Товар не найден")

    text = (
        f'<tg-emoji emoji-id="{product["emoji"]}">📦</tg-emoji> <b>{product["name"]}</b>\n\n'
        f'<b>Цена:</b> {product["price"]}$\n'
        f'<b>В наличии:</b> ∞ шт.'
    )
    await callback.message.edit_text(text, reply_markup=quantity_selection_kb(product_id))


@dp.callback_query(F.data.startswith("custom_qty_"))
async def custom_quantity_start(callback: types.CallbackQuery, state: FSMContext):
    product_id = callback.data.replace("custom_qty_", "")
    await state.update_data(product_id=product_id)
    await state.set_state(OrderState.entering_custom_quantity)
    
    await callback.message.edit_text(
        f'<tg-emoji emoji-id="5877485980901971030">🔘</tg-emoji> <b>Введите необходимое количество (числом):</b>',
        reply_markup=InlineKeyboardBuilder().button(text="Отмена", callback_data="back_to_catalog").as_markup()
    )
    await callback.answer()



@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await cmd_start(callback.message)
    await callback.message.delete()

@dp.message(F.text == "Профиль")
async def profile_menu(message: types.Message):
    user_data = get_user(message.from_user.id)
    
    if not user_data:
        add_user(message.from_user.id)
        user_data = get_user(message.from_user.id)


    user_id = user_data[0]
    balance = user_data[1]
    spent = user_data[2]
    orders = user_data[3]
    reg_date = user_data[4]
    
    text = (
        f'<tg-emoji emoji-id="5879770735999717115">👤</tg-emoji> <b>Профиль</b>\n\n'
        f'<b>├ ID:</b> <code>{user_id}</code>\n'
        f'<b>├ Баланс:</b> {balance:.2f}$\n'
        f'<b>├ Покупок:</b> {orders}\n'
        f'<b>├</b> <tg-emoji emoji-id="6028530359975548369">💸</tg-emoji> <b>Потрачено:</b> {spent:.2f}$\n'
        f'<b>└</b> <tg-emoji emoji-id="5967412305338568701">📅</tg-emoji> <b>Регистрация:</b> {reg_date}'
    )
    
    await message.answer(text, reply_markup=profile_kb())

@dp.callback_query(F.data == "my_orders")
async def show_my_orders(callback: types.CallbackQuery):
    text = (
        f'<tg-emoji emoji-id="5956561916573782596">🛍</tg-emoji> <b>Мои покупки</b>\n\n'
        f'У вас пока нет покупок.'
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "top_up")
async def start_deposit(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (f'<tg-emoji emoji-id="5877485980901971030">💳</tg-emoji> <b>Пополнение баланса</b>\n\n'
            f'Выберите валюту пополнения.')
    await callback.message.edit_text(text, reply_markup=deposit_currency_kb())

@dp.callback_query(F.data.startswith("dep_"))
async def choose_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1]
    await state.update_data(currency=currency)
    await state.set_state(DepositState.entering_amount)
    
    text = (f'<tg-emoji emoji-id="5877485980901971030">💳</tg-emoji> <b>Пополнение баланса в {currency}</b>\n\n'
            f'Введите сумму пополнения в {currency}:')
    await callback.message.edit_text(text, reply_markup=InlineKeyboardBuilder().button(text="Назад", callback_data="top_up").as_markup())


@dp.message(DepositState.entering_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        return await message.answer("Пожалуйста, введите число.")
    
    amount = float(message.text)
    comment = ''.join(random.choices(string.digits, k=8)) 
    
    await state.update_data(amount=amount, comment=comment)
    
    data = await state.get_data()
    currency = data.get("currency")
    
    if currency == "TON":
        usd_amount = round(amount / USD_TO_TON, 2)
        text = (f'<tg-emoji emoji-id="5406976471153545018">💎</tg-emoji> <b>Пополнение через TonKeeper</b>\n\n'
                f'Адрес: <code>{TON_ADDRESS}</code>\n'
                f'<tg-emoji emoji-id="5807499888245612254">💰</tg-emoji> Сумма: <b>{amount} TON</b> ({usd_amount}$)\n'
                f'<tg-emoji emoji-id="5994297722574737553">💬</tg-emoji> Комментарий: <code>{comment}</code>\n\n'
                f'Курс: 1$ = {USD_TO_TON} TON\n'
                f'<tg-emoji emoji-id="5881702736843511327">⚠️</tg-emoji> <b>Обязательно укажите комментарий!</b>\n'
                f'<tg-emoji emoji-id="5893072412924187198">✅</tg-emoji> После оплаты нажмите "Я оплатил"')
        await message.answer(text, reply_markup=payment_kb())

    elif currency == "USDT":
        try:
            invoice = await crypto.create_invoice(asset='USDT', amount=amount)
            text = (f'<tg-emoji emoji-id="5406612507034948020">💵</tg-emoji> <b>Пополнение USDT</b>\n'
                    f'<tg-emoji emoji-id="5807499888245612254">💰</tg-emoji> Сумма: <b>{amount} USDT</b>\n\n'
                    f'Нажмите «Оплатить» и затем «Я оплатил».')
            await message.answer(text, reply_markup=payment_kb(pay_url=invoice.bot_invoice_url))
        except Exception as e:
            print(f"Ошибка CryptoPay: {e}")
            await message.answer("Ошибка связи с Crypto Bot.")

@dp.callback_query(F.data == "check_payment")
async def check_pay(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    amount = user_data.get("amount", 0)
    currency = user_data.get("currency", "USD")
    comment = user_data.get("comment", "Нет комментария")
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO deposits (user_id, amount, currency, comment, status) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, currency, comment, 'pending')
    )
    conn.commit()
    deposit_id = cur.lastrowid 
    conn.close()

    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name

    admin_kb = InlineKeyboardBuilder()
    admin_kb.button(text="Начислить", callback_data=f"approve_{deposit_id}")
    admin_kb.button(text="Отказать", callback_data=f"reject_{deposit_id}")
    admin_kb.adjust(2)

    admin_text = (
        f'<tg-emoji emoji-id="6030861234432121355">🔔</tg-emoji> <b>Новая заявка на пополнение!</b>\n\n'
        f'<tg-emoji emoji-id="5886412370347036129">👤</tg-emoji> Пользователь: <b>{username}</b>\n'
        f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> ID: <code>{user_id}</code>\n'
        f'<tg-emoji emoji-id="5877485980901971030">💳</tg-emoji> Валюта: <b>{currency}</b>\n'
        f'<tg-emoji emoji-id="5985630530111020079">💰</tg-emoji> Сумма: <b>{amount}</b>\n'
        f'<tg-emoji emoji-id="5994297722574737553">💬</tg-emoji> Коммент: <code>{comment}</code>'
    )
    
    try:
        await bot.send_message(8774787211, admin_text, reply_markup=admin_kb.as_markup(), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    await callback.message.edit_text(
        f'<tg-emoji emoji-id="5994297722574737553">📩</tg-emoji> <b>Заявка отправлена.</b>\nОжидайте проверки.',
        reply_markup=InlineKeyboardBuilder().button(text="В меню", callback_data="back_to_main").as_markup(),
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()


@dp.message(AdminState.waiting_for_reject_reason)
async def admin_reject_pay_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("reject_user_id")
    reason = message.text

    try:
        await bot.send_message(
            target_user_id, 
            f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявка на пополнение отклонена.</b>\n\n'
            f'<b>Причина:</b> {reason}'
        )
        await message.answer(f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> Пользователь уведомлен об отказе.')
    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение: {e}")
    add_log(
    admin_id=message.from_user.id,
    admin_name=message.from_user.full_name,
    action_type="Отклонил пополнение",
    target_user_id=target_user_id,
    details=f"Причина: {reason}"
)
    await state.clear()


@dp.callback_query(F.data == "admin_orders_stub")
async def admin_orders_list(callback: types.CallbackQuery):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT order_id, user_id, product_name, total_price FROM orders WHERE status = 'pending'")
    orders = cur.fetchall()
    conn.close()

    if not orders:
        return await callback.message.edit_text(
            f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявок пока нет.</b>',
            reply_markup=admin_panel_kb()
        )

    text = f'<b>Список активных заказов:</b>\n\n'
    kb = InlineKeyboardBuilder()

    for order in orders:
        oid, uid, name, price = order
        text += (f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> <b>Заказ #{oid}</b> | Юзер: <code>{uid}</code>\n'
                 f'└ Товар: <b>{name}</b> ({price}$)\n\n')
        
        kb.button(text=f"Связаться по #{oid}", callback_data=f"order_chat_open_{oid}_{uid}")

    kb.button(text="Закрыть", callback_data="back_to_main")
    kb.adjust(1)

    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_logs")
async def admin_show_logs(callback: types.CallbackQuery):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT admin_name, admin_id, action_type, target_user_id, details FROM logs ORDER BY timestamp DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return await callback.message.edit_text(
            f'<tg-emoji emoji-id="5875206779196935950">📜</tg-emoji> <b>Логи пусты.</b>', 
            reply_markup=admin_panel_kb()
        )

    log_text = f'<tg-emoji emoji-id="5875206779196935950">📜</tg-emoji> <b>Последние 50 действий:</b>\n\n'
    for row in rows:
        admin_name, admin_id, action, target_id, details = row
        log_text += (f'<tg-emoji emoji-id="5886412370347036129">👤</tg-emoji> {action} '
                     f'<b>{admin_name}</b> (<code>{admin_id}</code>)\n'
                     f'└ Юзеру: <code>{target_id}</code> | {details}\n\n')

    await callback.message.edit_text(log_text, reply_markup=admin_panel_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    
    await callback.message.edit_text(
        f'<tg-emoji emoji-id="5960551395730919906">📝</tg-emoji> <b>Введите текст для рассылки:</b>',
        reply_markup=InlineKeyboardBuilder().button(
            text="Отмена", callback_data="admin_main"
        ).as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_broadcast_text)
    await callback.answer()

@dp.message(AdminState.waiting_for_broadcast_text)
async def admin_broadcast_finish(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    broadcast_text = message.text
    await state.clear()

    conn = sqlite3.connect('shop.db')
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()

    status_msg = await message.answer(f'<tg-emoji emoji-id="5931515758952583071">⏳</tg-emoji> <b>Рассылка запущена...</b>')
    
    count = 0
    blocked = 0
    
    for user in users:
        try:
            await bot.send_message(user[0], broadcast_text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05) 
        except:
            blocked += 1
            continue

    await status_msg.edit_text(
        f'<tg-emoji emoji-id="6005775159384870794">📢</tg-emoji> <b>Рассылка завершена!</b>\n\n'
        f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> Доставлено: <b>{count}</b>\n'
        f'<tg-emoji emoji-id="5985346521103604145">🚫</tg-emoji> Заблокировали: <b>{blocked}</b>',
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    category = data[2]
    item_id = data[3]
    quantity = int(data[4])
    
    prod_key = f"{category}_{item_id}"
    product = PRODUCTS.get(prod_key)
    
    if not product:
        return await callback.answer("Товар не найден", show_alert=True)

    total_cost = product['price'] * quantity
    user = get_user(callback.from_user.id)
    
    if user[1] < total_cost:
        await callback.message.answer(
            f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Недостаточно средств!</b>\n'
            f'<tg-emoji emoji-id="5881702736843511327">⚠️</tg-emoji> Пополните через профиль — пополнить баланс.',
            parse_mode="HTML"
        )
        return await callback.answer()

    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()

    cur.execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?", 
                (total_cost, total_cost, callback.from_user.id))
    
    cur.execute("INSERT INTO orders (user_id, product_name, quantity, total_price, status) VALUES (?, ?, ?, ?, ?)",
                (callback.from_user.id, product['name'], quantity, total_cost, 'pending'))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> Вы успешно купили товар <b>{product["name"]}</b> за <b>{total_cost}$</b>\n'
        f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> В течении 15 минут с вами свяжется наш администратор в этом чате. В случае чего - обращайтесь в поддержку.',
        parse_mode="HTML"
    )

    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    admin_text = (
        f'<tg-emoji emoji-id="6030861234432121355">🔔</tg-emoji> <b>Новая заявка на покупку!</b>\n\n'
        f'<tg-emoji emoji-id="5886412370347036129">👤</tg-emoji> Покупатель: <b>{username}</b>\n'
        f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> ID: <code>{callback.from_user.id}</code>\n'
        f'<tg-emoji emoji-id="6041705726206808304">📦</tg-emoji> Товар: <b>{product["name"]} (x{quantity})</b>\n'
        f'<tg-emoji emoji-id="5985630530111020079">💰</tg-emoji> Сумма сделки: <b>{total_cost}$</b>'
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Связаться с покупателем", callback_data=f"order_chat_open_{order_id}_{callback.from_user.id}")
    
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.message(Command("chat"))
async def cmd_chat(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return
    text = args[1]

    if message.from_user.id == ADMIN_ID:
        data = await state.get_data()
        cust_id = data.get("active_customer_id")
        if not cust_id: return await message.answer("Нет активного чата.")
        
        await bot.send_message(cust_id, 
            f'<tg-emoji emoji-id="5879770735999717115">🔔</tg-emoji> <b>Новое сообщение от администратора!</b>\n'
            f'<tg-emoji emoji-id="5960551395730919906">📝</tg-emoji> Текст: {text}\n\n'
            f'<tg-emoji emoji-id="5881702736843511327">⚠️</tg-emoji> Для ответа используйте <code>/chat ваше сообщение</code>',
            parse_mode="HTML")
    else:
        await bot.send_message(ADMIN_ID,
            f'<tg-emoji emoji-id="5879770735999717115">🔔</tg-emoji> <b>Новое сообщение от покупателя!</b>\n'
            f'<tg-emoji emoji-id="5886412370347036129">👤</tg-emoji> Имя: <b>{message.from_user.full_name}</b>\n'
            f'<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> Username: @{message.from_user.username} ({message.from_user.id})\n'
            f'<tg-emoji emoji-id="5960551395730919906">📝</tg-emoji> Текст: {text}\n\n'
            f'<tg-emoji emoji-id="5881702736843511327">⚠️</tg-emoji> Для ответа используйте <code>/chat ваше сообщение</code>',
            parse_mode="HTML")

@dp.callback_query(F.data.startswith("order_complete_"))
async def order_complete(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    order_id, cust_id = data[2], int(data[3])
    
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT total_price FROM orders WHERE order_id = ?", (order_id,))
    price = cur.fetchone()[0]
    cur.execute("UPDATE orders SET status = 'completed' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

    await state.clear()


    await callback.message.edit_text(
        f'<tg-emoji emoji-id="6039641775377748623">🤝</tg-emoji> <b>Сделка подтверждена.</b>\n'
        f'<tg-emoji emoji-id="5985630530111020079">💰</tg-emoji> Вы заработали: <b>{price}$</b>',
        parse_mode="HTML"
    )
    await bot.send_message(cust_id,
        f'<tg-emoji emoji-id="6039641775377748623">🤝</tg-emoji> <b>Сделка подтверждена администратором!</b>\n'
        f'<tg-emoji emoji-id="5994750571041525522">✨</tg-emoji> Ждем вас еще!',
        parse_mode="HTML")


@dp.callback_query(F.data.startswith("order_chat_open_"))
async def admin_open_chat(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() == AdminState.in_active_chat:
        return await callback.answer("Вы уже ведете одну сделку!", show_alert=True)

    data = callback.data.split("_")
    order_id, target_id = data[3], int(data[4])

    await state.update_data(active_customer_id=target_id, active_order_id=order_id)
    await state.set_state(AdminState.in_active_chat)

    conn = sqlite3.connect('shop.db')
    conn.execute("UPDATE orders SET chat_status = 1 WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()


    await bot.send_message(target_id, 
        f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> Администратор связывается с вами через чат в боте.\n'
        f'<tg-emoji emoji-id="5994297722574737553">📩</tg-emoji> Формат общения: <code>/chat ваше сообщение</code>',
        parse_mode="HTML")

    await callback.message.answer(f'<tg-emoji emoji-id="5902002809573740949">🌀</tg-emoji> Успешно! Используйте <code>/chat</code> для общения.')
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Закрыть чат", callback_data=f"order_chat_close_{order_id}_{target_id}"))
    kb.row(types.InlineKeyboardButton(text="🤝 Подтвердить сделку", callback_data=f"order_complete_{order_id}_{target_id}"))
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("order_chat_close_"))
async def admin_close_chat(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    order_id = callback.data.split("_")[3]
    conn = sqlite3.connect('shop.db')
    conn.execute("UPDATE orders SET chat_status = 0 WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

    await callback.message.answer(f'<tg-emoji emoji-id="5902002809573740949">🌀</tg-emoji> Чат успешно закрыт!')
    await callback.answer()

@dp.message(OrderState.entering_custom_quantity)
async def process_custom_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer(f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> Пожалуйста, введите целое число.')
    
    qty = int(message.text)
    data = await state.get_data()
    product_id = data.get("product_id")
    product = PRODUCTS.get(product_id)
    
    if not product:
        await state.clear()
        return await message.answer("Товар не найден.")

    total_price = round(product["price"] * qty, 2)
    category, item_id = product_id.split("_")

    text = (
        f"<b>Подтверждение заказа:</b>\n\n"
        f"Товар: <b>{product['name']}</b>\n"
        f"Количество: <b>{qty} шт.</b>\n"
        f"Итого к оплате: <b>{total_price}$</b>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить с баланса", callback_data=f"confirm_buy_{category}_{item_id}_{qty}")
    kb.button(text="Отмена", callback_data="back_to_catalog")
    kb.adjust(1)
    
    await message.answer(text, reply_markup=kb.as_markup())
    await state.clear()

@dp.callback_query(F.data.startswith("admin_orders_view_"))
async def admin_orders_pager(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT order_id, user_id, product_name, total_price, chat_status FROM orders WHERE status = 'pending'")
    orders = cur.fetchall()
    conn.close()

    if not orders:
        return await callback.message.edit_text(
            f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявок пока нет.</b>',
            reply_markup=InlineKeyboardBuilder().button(text="В меню", callback_data="back_to_main").as_markup()
        )

    if page >= len(orders): page = 0
    if page < 0: page = len(orders) - 1

    oid, uid, name, price, chat_status = orders[page]
    
    text = (f'<b>Заявка {page + 1} из {len(orders)}</b>\n\n'
            f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> <b>Заказ #{oid}</b>\n'
            f'└ Покупатель: <code>{uid}</code>\n'
            f'└ Товар: <b>{name}</b>\n'
            f'└ Сумма: <b>{price}$</b>')

    kb = InlineKeyboardBuilder()
    
    if chat_status == 0:
        kb.row(types.InlineKeyboardButton(text="Открыть чат", callback_data=f"order_chat_open_{oid}_{uid}"))
    else:
        kb.row(types.InlineKeyboardButton(text="Закрыть чат", callback_data=f"order_chat_close_{oid}_{uid}"))
    
    kb.row(types.InlineKeyboardButton(text="Подтвердить сделку", callback_data=f"order_complete_{oid}_{uid}"))
    
    kb.row(
        types.InlineKeyboardButton(text="Назад", callback_data=f"admin_orders_view_{page - 1}"),
        types.InlineKeyboardButton(text="Дальше", callback_data=f"admin_orders_view_{page + 1}")
    )
    kb.row(types.InlineKeyboardButton(text="В главное меню", callback_data="back_to_main"))

    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@dp.message(F.text == "Поддержка")
async def support_handler(message: types.Message):
    text = (
        f'<tg-emoji emoji-id="5873121512445187130">❓</tg-emoji> <b>Есть вопросы? Нужна замена?</b>\n'
        f'<tg-emoji emoji-id="5771887475421090729">📩</tg-emoji> <b>Пиши нам!</b>'
    )
    
    await message.answer(
        text, 
        reply_markup=support_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin_deposits_view_"))
async def admin_deposits_pager(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    page = int(data_parts[3]) if len(data_parts) >= 4 else 0
    
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, amount, currency, comment FROM deposits WHERE status = 'pending'")
    deposits = cur.fetchall()
    conn.close()

    if not deposits:
        kb = InlineKeyboardBuilder().button(text="В админ-панель", callback_data="back_to_main")
        no_deposits_text = f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявок пока нет.</b>'
        
        try:
            await callback.message.edit_text(no_deposits_text, reply_markup=kb.as_markup(), parse_mode="HTML")
        except Exception:
            await callback.answer("Все заявки обработаны")
        return

    if page >= len(deposits): page = 0
    if page < 0: page = len(deposits) - 1

    dep_id, uid, amount, currency, comment = deposits[page]
    
    try:
        chat = await callback.bot.get_chat(uid)
        username = f"@{chat.username}" if chat.username else "Нет юзернейма"
    except:
        username = "Скрыт/Не найден"

    text = (
        f"<b>Заявка на пополнение {page + 1} из {len(deposits)}</b>\n\n"
        f'<tg-emoji emoji-id="5886412370347036129">👤</tg-emoji> Пользователь: <b>{uid}</b>\n'
        f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> {username} (<code>{uid}</code>)\n'
        f'<tg-emoji emoji-id="5877485980901971030">💳</tg-emoji> Способ оплаты: <b>{currency}</b>\n'
        f'<tg-emoji emoji-id="5985630530111020079">💰</tg-emoji> Сумма: <b>{amount}$</b>\n'
    )
    if currency.upper() == "TON":
        text += f'<tg-emoji emoji-id="5994297722574737553">💬</tg-emoji> Комментарий: <code>{comment}</code>'

    kb = InlineKeyboardBuilder()
    kb.row(
        types.InlineKeyboardButton(text="Начислить", callback_data=f"approve_{dep_id}"),
        types.InlineKeyboardButton(text="Отказать", callback_data=f"reject_{dep_id}")
    )
    kb.row(
        types.InlineKeyboardButton(text="Назад", callback_data=f"admin_deposits_view_{page - 1}"),
        types.InlineKeyboardButton(text="Дальше", callback_data=f"admin_deposits_view_{page + 1}")
    )
    kb.row(types.InlineKeyboardButton(text="В админ-панель", callback_data="back_to_main"))

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("Список обновлен")
        else:
            print(f"Ошибка: {e}")
    
    await callback.answer()


@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve_deposit(callback: types.CallbackQuery):
    deposit_id = int(callback.data.split("_")[1])

    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, amount FROM deposits WHERE id = ? AND status = 'pending'", (deposit_id,))
    res = cur.fetchone()
    
    if not res:
        conn.close()
        return await callback.answer("Заявка уже обработана!", show_alert=True)

    uid, amount = res
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
    cur.execute("UPDATE deposits SET status = 'completed' WHERE id = ?", (deposit_id,))
    conn.commit()
    
    cur.execute("SELECT count(*) FROM deposits WHERE status = 'pending'")
    remaining = cur.fetchone()[0]
    conn.close()

    try:
        await bot.send_message(
            uid, 
            f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> <b>Баланс пополнен на {amount}$!</b>',
            parse_mode="HTML"
        )
        add_log(callback.from_user.id, callback.from_user.full_name, "Одобрил пополнение", uid, f"Сумма: {amount}$")
    except: pass

    await callback.answer("Баланс начислен!", show_alert=False)

    if remaining > 0:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="Следующая заявка", callback_data="admin_deposits_view_0"))
        kb.row(types.InlineKeyboardButton(text="В админ-панель", callback_data="back_to_main"))
        
        await callback.message.edit_text(
            f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> <b>Заявка одобрена!</b>\n\n'
            f'Пользователь: <code>{uid}</code>\n'
            f'Сумма: <b>{amount}$</b>\n\n'
            f'Осталось заявок: {remaining}',
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        final_admin_text = (
            f'<tg-emoji emoji-id="5985596818912712352">✅</tg-emoji> <b>Заявка обработана!</b>\n\n'
            f'<tg-emoji emoji-id="5936017305585586269">🆔</tg-emoji> Пользователь: <code>{uid}</code>\n'
            f'<tg-emoji emoji-id="5985630530111020079">💰</tg-emoji> Сумма: <b>{amount}$</b>\n\n'
            f'<tg-emoji emoji-id="6030861234432121355">🔔</tg-emoji> <b>Заявок больше нет!</b>'
        )
        kb = InlineKeyboardBuilder().button(text="В админ-панель", callback_data="back_to_main")
        await callback.message.edit_text(text=final_admin_text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    deposit_id = callback.data.split("_")[1]
    
    await state.update_data(reject_deposit_id=deposit_id)
    await state.set_state(AdminState.waiting_for_reject_reason)
    
    await callback.message.answer(
        f'<tg-emoji emoji-id="5960551395730919906">🔘</tg-emoji> <b>Введите причину отказа:</b>\n'
        f'Она будет отправлена пользователю.'
    )
    await callback.answer()

@dp.message(AdminState.waiting_for_reject_reason)
async def admin_reject_deposit_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dep_id = data.get("reject_deposit_id")
    reason = message.text

    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, amount FROM deposits WHERE id = ?", (dep_id,))
    res = cur.fetchone()
    
    if res:
        uid, amount = res
        cur.execute("UPDATE deposits SET status = 'rejected' WHERE id = ?", (dep_id,))
        conn.commit()
        
        final_text = (
            f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявка отклонена!</b>\n\n'
            f'<b>ID:</b> <code>{uid}</code>\n'
            f'<b>Причина:</b> {reason}'
        )
        
        try:
            await bot.send_message(uid, f'<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> <b>Заявка отклонена.</b>\n<b>Причина:</b> {reason}')
        except: pass
        
        kb = InlineKeyboardBuilder()
        kb.button(text="К списку заявок", callback_data="admin_deposits_view_0")
        kb.button(text="В меню", callback_data="back_to_main")
        kb.adjust(1)
        
        await message.answer(final_text, reply_markup=kb.as_markup(), parse_mode="HTML")
    
    conn.close()
    await state.clear()


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
