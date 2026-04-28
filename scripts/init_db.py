import os
import sqlite3
import random
from datetime import datetime, timedelta


DB_PATH = "./data/db/chatbi.db"
os.makedirs("./data/db", exist_ok=True)
random.seed(42)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# 模拟真实数仓命名规范：事实表 + 多张维度表。
cur.executescript("""
DROP TABLE IF EXISTS dwd_trade_order;
DROP TABLE IF EXISTS dim_user_info;
DROP TABLE IF EXISTS dim_sku_info;
DROP TABLE IF EXISTS dim_region_info;
DROP TABLE IF EXISTS dim_channel_info;

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

-- 维度表：地区信息
CREATE TABLE dim_region_info (
    region_id INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL,    -- 大区，如华东/华南
    province_name TEXT NOT NULL,
    city_name TEXT NOT NULL
);

-- 维度表：渠道信息
CREATE TABLE dim_channel_info (
    channel_id INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL    -- APP/小程序/直播/门店等
);

-- 明细表：交易订单
CREATE TABLE dwd_trade_order (
    order_id INTEGER PRIMARY KEY,
    uid INTEGER NOT NULL,
    sku_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    pay_amount REAL NOT NULL,       -- 实际支付金额 (GMV计算依据)
    discount_amount REAL DEFAULT 0, -- 优惠金额
    order_status INTEGER NOT NULL,  -- 10:待支付, 20:已支付, 30:已发货, 40:退款/售后
    create_time TEXT NOT NULL,
    FOREIGN KEY(uid) REFERENCES dim_user_info(uid),
    FOREIGN KEY(sku_id) REFERENCES dim_sku_info(sku_id),
    FOREIGN KEY(region_id) REFERENCES dim_region_info(region_id),
    FOREIGN KEY(channel_id) REFERENCES dim_channel_info(channel_id)
);
""")

# 1. 灌入用户数据
users = []
user_start = datetime(2023, 1, 1)
for i in range(1, 501):
    vip_level = random.choices([0, 1, 2, 3], weights=[60, 25, 10, 5])[0]
    is_deleted = 1 if random.random() < 0.05 else 0
    reg_time = (user_start + timedelta(days=random.randint(0, 360))).strftime("%Y-%m-%d %H:%M:%S")
    users.append((i, f"user_mock_{i}", vip_level, reg_time, is_deleted))
cur.executemany("INSERT INTO dim_user_info VALUES (?, ?, ?, ?, ?)", users)

# 2. 灌入商品数据
skus = [
    (1001, "iPhone 15 Pro", "3C数码", 7999, 1),
    (1002, "MacBook Air", "3C数码", 8999, 1),
    (1003, "索尼降噪耳机", "3C数码", 1999, 1),
    (2001, "SK-II神仙水", "美妆护肤", 1590, 1),
    (2002, "雅诗兰黛小棕瓶", "美妆护肤", 900, 1),
    (3001, "三只松鼠坚果大礼包", "零食生鲜", 129, 1),
    (3002, "智利车厘子礼盒", "零食生鲜", 299, 1),
    (4001, "飞天茅台53度", "酒水饮料", 2999, 0),
    (5001, "人体工学椅", "家居生活", 1399, 1),
    (5002, "扫地机器人", "家居生活", 2599, 1),
]
cur.executemany("INSERT INTO dim_sku_info VALUES (?, ?, ?, ?, ?)", skus)

# 3. 灌入地区数据
regions = [
    (1, "华东", "上海市", "上海"),
    (2, "华东", "浙江省", "杭州"),
    (3, "华东", "江苏省", "南京"),
    (4, "华南", "广东省", "广州"),
    (5, "华南", "广东省", "深圳"),
    (6, "华北", "北京市", "北京"),
    (7, "华北", "天津市", "天津"),
    (8, "西南", "四川省", "成都"),
]
cur.executemany("INSERT INTO dim_region_info VALUES (?, ?, ?, ?)", regions)

# 4. 灌入渠道数据
channels = [
    (1, "APP"),
    (2, "小程序"),
    (3, "直播间"),
    (4, "官网"),
    (5, "线下门店"),
]
cur.executemany("INSERT INTO dim_channel_info VALUES (?, ?)", channels)

# 5. 灌入订单明细
orders = []
start_date = datetime(2024, 1, 1)
for order_id in range(10000, 18000):
    uid = random.randint(1, len(users))
    sku = random.choice(skus)
    sku_id = sku[0]
    list_price = sku[3]
    region_id = random.choices([r[0] for r in regions], weights=[16, 13, 13, 16, 14, 11, 7, 10])[0]
    channel_id = random.choices([c[0] for c in channels], weights=[35, 25, 18, 12, 10])[0]

    discount = round(random.uniform(0, min(500, list_price * 0.2)), 2)
    pay_amount = max(0, list_price - discount)
    status = random.choices([10, 20, 30, 40], weights=[10, 42, 38, 10])[0]
    day_offset = random.randint(0, 180)
    create_time = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d %H:%M:%S")

    orders.append(
        (order_id, uid, sku_id, region_id, channel_id, pay_amount, discount, status, create_time)
    )

cur.executemany("INSERT INTO dwd_trade_order VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", orders)
conn.commit()
conn.close()

print("企业级电商 ChatBI Mock 库初始化完成：用户/商品/地区/渠道/订单维度已写入。")
