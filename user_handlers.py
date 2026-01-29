import os
import uuid
import aiohttp
import time
import shutil
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import (
    CRYPTOBOT_TOKEN, STAR_RATE, 
    TON_ADDRESS, TON_EXCHANGE_RATE, TONCENTER_API_KEY
)
from session_manager import SessionManager

router = Router()

class FillBalance(StatesGroup):
    waiting_for_amount = State() # Сумма в рублях (для TON/Crypto)
    waiting_for_stars = State()  # Количество звезд

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await db.add_user(message.from_user.id, message.from_user.username)
    await message.answer(f"👋 Привет, {message.from_user.first_name}!\nДобро пожаловать в PhonixShop.", reply_markup=kb.main_menu())

@router.callback_query(F.data == "main_menu")
async def back_home(callback: types.CallbackQuery):
    await callback.message.edit_text("🏠 Главное меню:", reply_markup=kb.main_menu())

# --- ПРОФИЛЬ И ПОПОЛНЕНИЕ ---

@router.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    balance = await db.get_user_balance(callback.from_user.id)
    text = (f"👤 <b>Личный кабинет</b>\n🆔 Ваш ID: <code>{callback.from_user.id}</code>\n💰 Баланс: <b>{balance}₽</b>")
    await callback.message.edit_text(text, reply_markup=kb.profile_kb(), parse_mode="HTML")

@router.callback_query(F.data == "topup_menu")
async def topup_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("💸 <b>Выберите способ пополнения:</b>", reply_markup=kb.topup_methods_kb(), parse_mode="HTML")

# --- ЛОГИКА ВВОДА СУММЫ (TON / CRYPTO) ---

@router.callback_query(F.data.in_({"pay_crypto", "pay_ton"}))
async def prompt_amount(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(method=callback.data)
    await callback.message.edit_text("💰 Введите сумму пополнения в <b>рублях</b>:")
    await state.set_state(FillBalance.waiting_for_amount)

@router.message(FillBalance.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите целое число.")
    
    amount = int(message.text)
    user_data = await state.get_data()
    method = user_data.get('method')
    await state.clear()

    if method == "pay_crypto":
        async with aiohttp.ClientSession() as session:
            headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN}
            # Конвертация рубль -> USDT (курс ~95)
            payload = {'asset': 'USDT', 'amount': str(round(amount / 95, 2)), 'allow_comments': False}
            async with session.post('https://pay.crypt.bot/api/createInvoice', json=payload, headers=headers) as resp:
                res = await resp.json()
                if res.get('ok'):
                    data = res['result']
                    await message.answer(
                        f"💎 <b>Оплата CryptoBot</b>\nСумма: {amount}₽ (~{data['amount']} USDT)",
                        reply_markup=kb.payment_action_kb(data['pay_url'], f"check_cry_{data['invoice_id']}_{amount}"),
                        parse_mode="HTML"
                    )

    elif method == "pay_ton":
        ton_amount = round(amount / TON_EXCHANGE_RATE, 4)
        comment = f"ID{message.from_user.id}X{uuid.uuid4().hex[:4]}"
        ton_url = f"ton://transfer/{TON_ADDRESS}?amount={int(ton_amount * 10**9)}&text={comment}"
        
        text = (
            f"🌐 <b>Пополнение через TON</b>\n\n"
            f"💵 Сумма: <code>{ton_amount}</code> TON (~{amount}₽)\n"
            f"👛 Адрес: <code>{TON_ADDRESS}</code>\n"
            f"📝 Комментарий: <code>{comment}</code>\n\n"
            f"⚠️ Отправьте монеты с указанным комментарием!"
        )
        await message.answer(text, reply_markup=kb.payment_action_kb(ton_url, f"check_ton_{comment}_{amount}"), parse_mode="HTML")

# --- ЛОГИКА TELEGRAM STARS (ИСПРАВЛЕНО) ---

@router.callback_query(F.data == "pay_stars")
async def pay_stars_prompt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⭐ Введите количество <b>Telegram Stars</b> (XTR), которое хотите потратить:")
    await state.set_state(FillBalance.waiting_for_stars)

@router.message(FillBalance.waiting_for_stars)
async def process_stars(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ Введите целое число.")
    
    stars_count = int(message.text)
    if stars_count <= 0:
        return await message.answer("❌ Минимум 1 звезда.")
        
    amount_rub = round(stars_count * STAR_RATE, 2)
    await state.clear()
    
    # Отправляем инвойс
    prices = [types.LabeledPrice(label="Звезды PhonixShop", amount=stars_count)]
    
    await message.answer_invoice(
        title="Пополнение баланса ⭐",
        description=f"Зачисление {amount_rub}₽ на ваш баланс в боте.",
        prices=prices,
        payload=f"stars_refill_{amount_rub}", # Важно для обработки платежа
        currency="XTR", # Код валюты для звезд
        start_parameter="topup_stars"
    )

@router.pre_checkout_query()
async def process_pre_checkout(query: types.PreCheckoutQuery):
    # Обязательный ответ в течение 10 секунд
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def on_successful_payment(message: types.Message):
    # Извлекаем сумму из payload
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_refill_"):
        amount_rub = float(payload.split("_")[-1])
        await db.top_up_balance(message.from_user.id, amount_rub)
        await message.answer(f"✅ Успешно! Вы потратили {message.successful_payment.total_amount} ⭐.\nНа ваш баланс зачислено <b>{amount_rub}₽</b>.", parse_mode="HTML")

# --- ПРОВЕРКА TON / CRYPTO ---

@router.callback_query(F.data.startswith("check_ton_"))
async def check_ton_payment(callback: types.CallbackQuery):
    _, _, comment, amount = callback.data.split("_")
    url = f"https://toncenter.com/api/v2/getTransactions?address={TON_ADDRESS}&limit=15"
    if TONCENTER_API_KEY: url += f"&api_key={TONCENTER_API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("ok"):
                for tx in data["result"]:
                    msg = tx.get("in_msg", {})
                    if msg.get("message") == comment:
                        await db.top_up_balance(callback.from_user.id, float(amount))
                        await callback.message.edit_text(f"✅ Успешно! На баланс зачислено {amount}₽")
                        return
            await callback.answer("⏳ Платеж пока не найден в сети TON.", show_alert=True)

@router.callback_query(F.data.startswith("check_cry_"))
async def check_crypto_payment(callback: types.CallbackQuery):
    _, _, invoice_id, amount = callback.data.split("_")
    async with aiohttp.ClientSession() as session:
        headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN}
        async with session.get(f'https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}', headers=headers) as resp:
            res = await resp.json()
            if res.get('ok') and res['result']['items']:
                if res['result']['items'][0]['status'] == 'paid':
                    await db.top_up_balance(callback.from_user.id, float(amount))
                    await callback.message.edit_text(f"✅ Оплата подтверждена! Зачислено {amount}₽")
                    return
            await callback.answer("⏳ Оплата еще не произведена.", show_alert=True)

# --- МАГАЗИН И ИНВЕНТАРЬ ---

@router.callback_query(F.data == "catalog_start")
async def show_categories(callback: types.CallbackQuery):
    categories = await db.get_categories()
    await callback.message.edit_text("🛒 <b>Каталог товаров:</b>", reply_markup=kb.catalog_kb(categories), parse_mode="HTML")

@router.callback_query(F.data.startswith("cat_"))
async def show_products(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    products = await db.get_products_by_category(cat_id)
    await callback.message.edit_text("📦 <b>Выберите товар:</b>", reply_markup=kb.products_kb(products, cat_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("prod_"))
async def product_detail(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    prod = await db.get_product_info(prod_id)
    text = f"<b>{prod[2]}</b>\n\n{prod[3]}\n\n💰 Цена: {prod[4]}₽"
    await callback.message.edit_text(text, reply_markup=kb.buy_kb(prod_id, prod[4]), parse_mode="HTML")

@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    result = await db.process_buy(callback.from_user.id, prod_id)
    
    if result == "low_balance":
        await callback.answer("❌ Недостаточно средств на балансе!", show_alert=True)
    elif result == "no_stock":
        await callback.answer("❌ К сожалению, этот товар закончился.", show_alert=True)
    elif isinstance(result, int):
        await callback.message.edit_text("✅ Покупка совершена! Аккаунт добавлен в ваши покупки.", reply_markup=kb.main_menu())
    else:
        await callback.answer("❌ Произошла системная ошибка.", show_alert=True)

@router.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    items = await db.get_user_inventory(callback.from_user.id)
    await callback.message.edit_text("📦 <b>Ваши покупки:</b>", reply_markup=kb.inventory_kb(items), parse_mode="HTML")

@router.callback_query(F.data.startswith("myitem_"))
async def item_details(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    item = await db.get_item_full_info(item_id)
    text = f"📱 <b>Товар:</b> {item[1]}\n📞 <b>Номер:</b> {item[3]}\n📅 <b>Дата:</b> {time.ctime(item[6])}"
    await callback.message.edit_text(text, reply_markup=kb.item_control_kb(item_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("dl_sess_"))
async def download_session(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    item = await db.get_item_full_info(item_id)
    if os.path.exists(item[2]):
        await callback.message.answer_document(types.FSInputFile(item[2]), caption=f"Сессия: {item[3]}")
    else:
        await callback.answer("Файл не найден на сервере.", show_alert=True)

@router.callback_query(F.data.startswith("dl_tdata_"))
async def dl_tdata(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    item = await db.get_item_full_info(item_id)
    zip_path = SessionManager.get_tdata_zip_path(item[2], item_id)
    if os.path.exists(zip_path):
        await callback.message.answer_document(types.FSInputFile(zip_path), caption=f"TData (Zip): {item[3]}")
    else:
        await callback.answer("Ошибка при создании архива.", show_alert=True)

@router.callback_query(F.data.startswith("get_code_"))
async def get_sms_code(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[-1])
    item = await db.get_item_full_info(item_id)
    await callback.message.edit_text("📡 <b>Подключаюсь к сессии для получения кода...</b>", parse_mode="HTML")
    code_text = await SessionManager.get_latest_code(item[2])
    await callback.message.edit_text(code_text, reply_markup=kb.get_code_kb(item_id), parse_mode="HTML")