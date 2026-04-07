import os
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "./data/db/chatbi.db"
os.makedirs("./data/db", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS regions;
""")

cur.executescript("""
CREATE TABLE regions (
    region_id INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL,
    province TEXT NOT NULL
);

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    user_name TEXT NOT NULL,
    gender TEXT,
    age INTEGER,
    city TEXT,
    register_date TEXT
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT,
    brand TEXT,
    price REAL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    sales_amount REAL NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id),
    FOREIGN KEY(region_id) REFERENCES regions(region_id)
);
""")

regions = [
    (1, "华东", "上海"),
    (2, "华东", "江苏"),
    (3, "华南", "广东"),
    (4, "华北", "北京"),
    (5, "西南", "四川"),
]

products = [
    (1, "iPhone 15", "手机", "高端手机", "Apple", 5999),
    (2, "Mate 60", "手机", "旗舰手机", "Huawei", 4999),
    (3, "小米14", "手机", "性价比手机", "Xiaomi", 3999),
    (4, "MacBook Pro", "电脑", "笔记本", "Apple", 12999),
    (5, "ThinkPad X1", "电脑", "商务本", "Lenovo", 9999),
    (6, "AirPods Pro", "耳机", "无线耳机", "Apple", 1899),
    (7, "华为 FreeBuds", "耳机", "无线耳机", "Huawei", 999),
    (8, "戴森吹风机", "家电", "个护电器", "Dyson", 2999),
    (9, "小米空气净化器", "家电", "空气净化", "Xiaomi", 1499),
    (10, "机械键盘", "外设", "键盘", "Keychron", 699),
]

users = []
for i in range(1, 201):
    gender = random.choice(["男", "女"])
    age = random.randint(18, 45)
    city = random.choice(["上海", "南京", "广州", "北京", "成都", "苏州", "深圳"])
    register_date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d")
    users.append((i, f"user_{i}", gender, age, city, register_date))

cur.executemany("INSERT INTO regions VALUES (?, ?, ?)", regions)
cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)", products)
cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", users)

orders = []
start_date = datetime(2024, 1, 1)

for order_id in range(1, 5001):
    user_id = random.randint(1, 200)
    product = random.choice(products)
    product_id = product[0]
    category = product[2]
    base_price = product[5]
    region_id = random.randint(1, 5)

    day_offset = random.randint(0, 364)
    order_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

    quantity = random.randint(1, 3)

    seasonal_factor = 1.0
    month = int(order_date[5:7])

    if category == "家电" and month in [6, 7, 8]:
        seasonal_factor = 1.2
    elif category == "电脑" and month in [9, 10]:
        seasonal_factor = 1.15
    elif category == "耳机" and month in [11, 12]:
        seasonal_factor = 1.25

    noise = random.uniform(0.85, 1.15)
    sales_amount = round(base_price * quantity * seasonal_factor * noise, 2)

    orders.append((order_id, user_id, product_id, region_id, order_date, quantity, sales_amount))

cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", orders)

cur.executescript("""
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_product ON orders(product_id);
CREATE INDEX idx_orders_region ON orders(region_id);
""")

conn.commit()
conn.close()

print(f"Database initialized at: {DB_PATH}")
print("Inserted:")
print(f"- {len(regions)} regions")
print(f"- {len(users)} users")
print(f"- {len(products)} products")
print(f"- {len(orders)} orders")
