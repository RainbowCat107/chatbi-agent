import os
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "./data/db/chatbi.db"
os.makedirs("./data/db", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 模拟真实的数仓命名规范和复杂的业务字段
cur.executescript("""
DROP TABLE IF EXISTS dwd_trade_order;
DROP TABLE IF EXISTS dim_user_info;
DROP TABLE IF EXISTS dim_sku_info;

-- 维度表：用户信息
CREATE TABLE dim_user_info (
    uid INTEGER PRIMARY KEY,
    nick_name TEXT NOT NULL,
    vip_level INTEGER DEFAULT 0,  -- 0:普通, 1:黄金, 2:铂金, 3:钻石
    reg_time TEXT NOT NULL,
    is_deleted INTEGER DEFAULT 0  -- 软删除标记 (0:正常, 1:已注销)
);

-- 维度表：商品信息
CREATE TABLE dim_sku_info (
    sku_id INTEGER PRIMARY KEY,
    spu_name TEXT NOT NULL,
    cat_name TEXT NOT NULL,       -- 类目名
    list_price REAL NOT NULL,     -- 吊牌价
    is_on_sale INTEGER DEFAULT 1  -- 是否上架 (1:上架, 0:下架)
);

-- 明细表：交易订单
CREATE TABLE dwd_trade_order (
    order_id INTEGER PRIMARY KEY,
    uid INTEGER NOT NULL,
    sku_id INTEGER NOT NULL,
    pay_amount REAL NOT NULL,     -- 实际支付金额 (GMV计算依据)
    discount_amount REAL DEFAULT 0, -- 优惠金额
    order_status INTEGER NOT NULL,-- 10:待支付, 20:已支付, 30:已发货, 40:退款/售后
    create_time TEXT NOT NULL,
    FOREIGN KEY(uid) REFERENCES dim_user_info(uid),
    FOREIGN KEY(sku_id) REFERENCES dim_sku_info(sku_id)
);
""")

# 1. 灌入用户数据
users = []
for i in range(1, 301):
    vip_level = random.choices([0, 1, 2, 3], weights=[60, 25, 10, 5])[0]
    is_deleted = 1 if random.random() < 0.05 else 0 # 5%的注销用户
    users.append((i, f"user_mock_{i}", vip_level, "2023-01-01", is_deleted))
cur.executemany("INSERT INTO dim_user_info VALUES (?, ?, ?, ?, ?)", users)

# 2. 灌入商品数据
skus = [
    (1001, "iPhone 15 Pro", "3C数码", 7999, 1),
    (1002, "MacBook Air", "3C数码", 8999, 1),
    (1003, "索尼降噪耳机", "3C数码", 1999, 1),
    (2001, "SK-II神仙水", "美妆护肤", 1590, 1),
    (2002, "雅诗兰黛小棕瓶", "美妆护肤", 900, 1),
    (3001, "三只松鼠坚果大礼包", "零食生鲜", 129, 1),
    (3002, "飞天茅台53度", "酒水饮料", 2999, 0) # 已下架商品
]
cur.executemany("INSERT INTO dim_sku_info VALUES (?, ?, ?, ?, ?)", skus)

# 3. 灌入订单明细 (制造各种状态的订单)
orders = []
start_date = datetime(2024, 1, 1)
for order_id in range(10000, 15000):
    uid = random.randint(1, 300)
    sku = random.choice(skus)
    sku_id = sku[0]
    list_price = sku[3]
    
    # 模拟业务逻辑
    discount = round(random.uniform(0, 200), 2)
    pay_amount = max(0, list_price - discount)
    
    # 制造状态坑：大部分是20(已支付)和30(已发货)，少量10(待支付)和40(退款)
    status = random.choices([10, 20, 30, 40], weights=[10, 40, 40, 10])[0]
    
    day_offset = random.randint(0, 90)
    create_time = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d %H:%M:%S")
    
    orders.append((order_id, uid, sku_id, pay_amount, discount, status, create_time))

cur.executemany("INSERT INTO dwd_trade_order VALUES (?, ?, ?, ?, ?, ?, ?)", orders)
conn.commit()
conn.close()

print("企业级脏数据 Mock 库初始化完成！大模型准备挨锤！")