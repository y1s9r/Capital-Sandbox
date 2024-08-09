import sqlite3
from flask import session
from yahoo_fin import stock_info
import numpy


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
    except (ValueError, TypeError, AssertionError) as e:
        print(f"Error retrieving data for {symbol}: {e}")
        return None