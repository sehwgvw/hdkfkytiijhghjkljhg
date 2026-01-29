from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from config import SUPPORT_LINK

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Каталог товаров", callback_data="catalog_start")
    kb.button(text="👤 Профиль / Баланс", callback_data="profile")
    kb.button(text="📦 Мои покупки", callback_data="inventory")
    kb.button(text="👨‍💼 Поддержка", url=SUPPORT_LINK)
    kb.adjust(2, 2)
    return kb.as_markup()

# --- ПРОФИЛЬ И ПОПОЛНЕНИЕ ---
def profile_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Пополнить баланс", callback_data="topup_menu")
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def topup_methods_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 CryptoBot (USDT)", callback_data="pay_crypto")
    kb.button(text="🌐 TON (Tonkeeper)", callback_data="pay_ton")
    kb.button(text="⭐ Telegram Stars", callback_data="pay_stars")
    kb.button(text="🔙 Назад", callback_data="profile")
    kb.adjust(1)
    return kb.as_markup()

def payment_action_kb(url, check_data):
    kb = InlineKeyboardBuilder()
    if url:
        kb.button(text="🔗 Перейти к оплате", url=url)
    kb.button(text="✅ Проверить оплату", callback_data=check_data)
    kb.button(text="❌ Отмена", callback_data="profile")
    kb.adjust(1)
    return kb.as_markup()

# --- КАТАЛОГ И ПОКУПКА ---
def catalog_kb(categories):
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.button(text=cat[1], callback_data=f"cat_{cat[0]}")
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(2)
    return kb.as_markup()

def products_kb(prods, cat_id):
    kb = InlineKeyboardBuilder()
    for prod in prods:
        # prod: id, name, price
        kb.button(text=f"{prod[1]} — {prod[2]}₽", callback_data=f"prod_{prod[0]}")
    kb.button(text="🔙 Назад к категориям", callback_data="catalog_start")
    kb.adjust(1)
    return kb.as_markup()

def buy_kb(prod_id, price):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"💳 Купить за {price}₽", callback_data=f"buy_{prod_id}")
    kb.button(text="🔙 Назад", callback_data="catalog_start")
    kb.adjust(1)
    return kb.as_markup()

# --- ИНВЕНТАРЬ И УПРАВЛЕНИЕ АККАУНТАМИ ---
def inventory_kb(items):
    kb = InlineKeyboardBuilder()
    if not items:
        kb.button(text="Список пуст 😔 В каталог", callback_data="catalog_start")
    else:
        for item in items:
            # item: id, name, sold_at, phone
            kb.button(text=f"📱 {item[1]} (#{item[0]})", callback_data=f"myitem_{item[0]}")
        kb.button(text="🔙 В меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def item_control_kb(item_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="📩 Скачать .session", callback_data=f"dl_sess_{item_id}")
    kb.button(text="🗂 Скачать TData (Zip)", callback_data=f"dl_tdata_{item_id}")
    kb.button(text="🔑 Получить SMS код", callback_data=f"get_code_{item_id}")
    kb.button(text="🔙 Назад", callback_data="inventory")
    kb.adjust(1)
    return kb.as_markup()

def get_code_kb(item_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить (проверить)", callback_data=f"get_code_{item_id}")
    kb.button(text="🔙 Назад к товару", callback_data=f"myitem_{item_id}")
    kb.adjust(1)
    return kb.as_markup()

# --- АДМИН-ПАНЕЛЬ ---
def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить категорию", callback_data="admin_add_cat")
    kb.button(text="➕ Добавить товар", callback_data="admin_add_prod")
    kb.button(text="📥 Загрузить .session", callback_data="admin_add_sess")
    kb.button(text="📊 Список товаров", callback_data="admin_list_prods")
    kb.button(text="🏠 В главное меню", callback_data="main_menu")
    kb.adjust(2)
    return kb.as_markup()