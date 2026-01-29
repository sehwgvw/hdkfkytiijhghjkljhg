import aiosqlite
import time
from config import DB_NAME

async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:
        # Категории
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        
        # Товары
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                image_id TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """)

        # Единицы товара (аккаунты)
        # file_path: путь к .session файлу
        # phone_number: номер телефона (вытаскивается автоматически)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                file_path TEXT, 
                phone_number TEXT,
                is_sold BOOLEAN DEFAULT 0,
                buyer_id INTEGER,
                sold_at REAL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        
        # Пользователи (с балансом)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                join_date REAL
            )
        """)
        
        # История транзакций (пополнения)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                system TEXT, 
                status TEXT, 
                created_at REAL
            )
        """)
        
        await db.commit()

# --- Пользователи и Баланс ---

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, balance, join_date) VALUES (?, ?, 0, ?)", 
                         (user_id, username, time.time()))
        await db.commit()

async def get_user_balance(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 0.0

async def top_up_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

# --- Управление Товарами (Админ) ---

async def add_category(name):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        await db.commit()

async def get_categories():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM categories") as cursor:
            return await cursor.fetchall()

async def add_product(category_id, name, description, price, image_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("INSERT INTO products (category_id, name, description, price, image_id) VALUES (?, ?, ?, ?, ?)", 
                                  (category_id, name, description, price, image_id))
        await db.commit()
        return cursor.lastrowid

async def get_all_products():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name, price FROM products") as cursor:
            return await cursor.fetchall()

async def get_products_by_category(category_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name, price FROM products WHERE category_id = ?", (category_id,)) as cursor:
            return await cursor.fetchall()

async def get_product_details(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            return await cursor.fetchone()

# --- Управление Единицами Товара (Items) ---

async def add_item_session(product_id, file_path, phone_number):
    """Добавляет сессию в базу"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("INSERT INTO items (product_id, file_path, phone_number) VALUES (?, ?, ?)", 
                         (product_id, file_path, phone_number))
        await db.commit()
        return cursor.lastrowid

async def get_available_count(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM items WHERE product_id = ? AND is_sold = 0", (product_id,)) as cursor:
            res = await cursor.fetchone()
            return res[0]

# --- Покупка ---

async def buy_item_balance(user_id, product_id, price):
    """Транзакция покупки: проверка баланса -> списание -> выдача товара"""
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Проверяем баланс
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            balance = res[0] if res else 0
        
        if balance < price:
            return "no_balance"
        
        # 2. Ищем свободный товар
        async with db.execute("SELECT id FROM items WHERE product_id = ? AND is_sold = 0 LIMIT 1", (product_id,)) as cursor:
            item = await cursor.fetchone()
        
        if not item:
            return "no_stock"
            
        item_id = item[0]
        
        # 3. Атомарная операция списания и выдачи
        try:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
            await db.execute("UPDATE items SET is_sold = 1, buyer_id = ?, sold_at = ? WHERE id = ?", (user_id, time.time(), item_id))
            await db.commit()
            return item_id
        except Exception as e:
            print(f"Error in buy transaction: {e}")
            return "error"

# --- Инвентарь ---

async def get_user_inventory(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Возвращаем список покупок (ID товара, Название товара, Дата покупки)
        query = """
            SELECT i.id, p.name, i.sold_at, i.phone_number
            FROM items i 
            JOIN products p ON i.product_id = p.id 
            WHERE i.buyer_id = ? 
            ORDER BY i.sold_at DESC
        """
        async with db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_item_full_info(item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            return await cursor.fetchone()