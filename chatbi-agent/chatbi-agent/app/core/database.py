import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./data/db/chatbi.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
