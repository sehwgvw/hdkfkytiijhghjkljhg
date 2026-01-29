import os
import shutil
import uuid
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import database as db
import keyboards as kb
from session_manager import SessionManager, SESSIONS_DIR

router = Router()

# Состояния FSM
class AddCategory(StatesGroup):
    waiting_name = State()

class AddProduct(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_desc = State()
    waiting_price = State()
    waiting_image = State()

class AddSessionItem(StatesGroup):
    waiting_product = State()
    waiting_file = State()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- Главное меню админа ---
@router.message(Command("admin"))
async def admin_start(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🛠 <b>Админ-панель PhonixShop</b>", reply_markup=kb.admin_menu(), parse_mode="HTML")

# --- Просмотр товаров ---
@router.callback_query(F.data == "admin_list_prods")
async def list_products(callback: types.CallbackQuery):
    prods = await db.get_all_products()
    if not prods:
        await callback.message.edit_text("Товаров нет.", reply_markup=kb.admin_menu())
        return
    
    text = "📋 <b>Список товаров (ID | Название | Цена):</b>\n\n"
    for p in prods:
        count = await db.get_available_count(p[0])
        text += f"🆔 <b>{p[0]}</b> | {p[1]} | {p[2]}₽ | (В наличии: {count})\n"
    
    await callback.message.edit_text(text, reply_markup=kb.admin_menu(), parse_mode="HTML")

# --- Добавление Категории ---
@router.callback_query(F.data == "admin_add_cat")
async def start_add_cat(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название категории:")
    await state.set_state(AddCategory.waiting_name)

@router.message(AddCategory.waiting_name)
async def finish_add_cat(message: types.Message, state: FSMContext):
    await db.add_category(message.text)
    await message.answer(f"✅ Категория '{message.text}' создана!")
    await state.clear()
    await message.answer("Меню:", reply_markup=kb.admin_menu())

# --- Добавление Товара ---
@router.callback_query(F.data == "admin_add_prod")
async def start_add_prod(callback: types.CallbackQuery, state: FSMContext):
    cats = await db.get_categories()
    if not cats:
        await callback.answer("Сначала создайте категории!", show_alert=True)
        return
    
    # Клавиатура выбора категории
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for cat in cats:
        builder.button(text=cat[1], callback_data=f"setcat_{cat[0]}")
    await callback.message.answer("Выберите категорию:", reply_markup=builder.as_markup())
    await state.set_state(AddProduct.waiting_category)

@router.callback_query(AddProduct.waiting_category, F.data.startswith("setcat_"))
async def set_prod_cat(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    await state.update_data(cat_id=cat_id)
    await callback.message.answer("Введите название товара:")
    await state.set_state(AddProduct.waiting_name)

@router.message(AddProduct.waiting_name)
async def set_prod_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание товара:")
    await state.set_state(AddProduct.waiting_desc)

@router.message(AddProduct.waiting_desc)
async def set_prod_desc(message: types.Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Введите цену (число):")
    await state.set_state(AddProduct.waiting_price)

@router.message(AddProduct.waiting_price)
async def set_prod_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Отправьте фото товара (или напишите 'skip'):")
        await state.set_state(AddProduct.waiting_image)
    except:
        await message.answer("Пожалуйста, введите число.")

@router.message(AddProduct.waiting_image)
async def set_prod_image(message: types.Message, state: FSMContext):
    image_id = None
    if message.photo:
        image_id = message.photo[-1].file_id
    elif message.text and message.text.lower() != 'skip':
        await message.answer("Нужно отправить фото или 'skip'.")
        return

    data = await state.get_data()
    prod_id = await db.add_product(data['cat_id'], data['name'], data['desc'], data['price'], image_id)
    
    await message.answer(
        f"✅ Товар успешно создан!\n\n🆔 <b>ID товара: {prod_id}</b>\n(Используйте этот ID для загрузки аккаунтов)", 
        reply_markup=kb.admin_menu(), parse_mode="HTML"
    )
    await state.clear()

# --- Загрузка Аккаунтов (Умная загрузка) ---
@router.callback_query(F.data == "admin_add_item")
async def start_add_item(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введите ID товара (из списка), к которому вы хотите загрузить аккаунты:")
    await state.set_state(AddSessionItem.waiting_product)

@router.message(AddSessionItem.waiting_product)
async def wait_file_item(message: types.Message, state: FSMContext):
    try:
        prod_id = int(message.text)
        # Проверим, существует ли товар
        prod = await db.get_product_details(prod_id)
        if not prod:
             await message.answer("Товар с таким ID не найден.")
             return
             
        await state.update_data(prod_id=prod_id)
        await message.answer(
            f"Выбран товар: <b>{prod[2]}</b>\n\n"
            f"📤 <b>Отправьте файл .session</b> (можно несколько по очереди).\n"
            f"Бот автоматически проверит валидность и сохранит номер.", 
            parse_mode="HTML"
        )
        await state.set_state(AddSessionItem.waiting_file)
    except ValueError:
        await message.answer("Введите числовой ID.")

@router.message(AddSessionItem.waiting_file, F.document)
async def process_file_upload(message: types.Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith(".session"):
        await message.answer("❌ Это не .session файл!")
        return
    
    status_msg = await message.answer("⏳ Скачиваю и проверяю...")
    
    # 1. Скачиваем во временный файл
    temp_filename = f"temp_{uuid.uuid4()}.session"
    await bot.download(message.document, destination=temp_filename)
    
    # 2. Проверяем валидность через Telethon
    phone = await SessionManager.get_phone_from_session(temp_filename)
    
    if not phone:
        await status_msg.edit_text("❌ <b>Ошибка:</b> Сессия невалидна (auth key unset) или требует 2FA пароль.")
        os.remove(temp_filename)
        return
    
    # 3. Сохраняем в базу и переносим файл
    data = await state.get_data()
    prod_id = data['prod_id']
    
    # Добавляем запись в БД
    # Сначала генерируем уникальное имя для хранилища, чтобы не было конфликтов
    final_filename = f"{uuid.uuid4()}.session"
    final_path = os.path.join(SESSIONS_DIR, final_filename)
    
    # Перемещаем файл
    shutil.move(temp_filename, final_path)
    
    # Записываем в БД
    await db.add_item_session(prod_id, final_path, phone)
    
    await status_msg.edit_text(
        f"✅ <b>Успешно добавлено!</b>\n"
        f"📱 Номер: <code>{phone}</code>\n"
        f"📁 Файл сохранен.", 
        parse_mode="HTML"
    )
    # Состояние не сбрасываем, чтобы админ мог кидать следующие файлы