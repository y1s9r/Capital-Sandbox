import sqlite3
from flask import session
from yahoo_fin import stock_info
import numpy
from flask import session


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def login_check():
    if session.get("user_id") is None:
        return False
    return True


def lookup(symbol):
    try:
        price = stock_info.get_live_price(symbol)
        price = round(price, 2)
        if numpy.isnan(price):
            return None
        return {"price": price, "symbol": symbol}
    except (ValueError, TypeError, AssertionError, KeyError) as e:
        print(f"Error retrieving data for {symbol}: {e}")
        return None
    

def get_wallet():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
        wallet_row = cursor.fetchone()
        if not wallet_row:
            conn.close()
            return None
        wallet = float(wallet_row[0])  # Ensure wallet is a float
        conn.close()
        return wallet


def usd(value):
    return f"${value:,.2f}"