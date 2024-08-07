import sqlite3
from flask import session


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_check():
    if session.get("user_id") is None:
        return False
    return True