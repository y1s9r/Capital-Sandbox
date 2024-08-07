from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from helper import login_check, get_db_connection
import requests

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

headers = {
    "Accept-Encoding": "gzip, deflate",
    "Authorization": "Bearer fbeb3e0c-a16c-4726-8f7b-242918872dc9"
}


@app.route("/")
def main():
    if not login_check():
        return redirect("/login")
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"]) # DESIGN PAGE
def login():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        if not name or not password:
            return redirect("/login")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (name,))
        data = cursor.fetchone()
        conn.close()
        if data is None or not check_password_hash(data["hash"], password):
            return render_template("error.html", errorcode=400, message="Incorrect Username or Password")
        session["user_id"] = data["id"]
        return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"]) # DESIGN PAGE
def register():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if not name or not password or not confirm:
            return redirect("/register")
        if password != confirm:
            return render_template("error.html", errorcode="400", message="Password does not match") # DESIGN PAGE
        passhash = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, hash) VALUES(?, ?)", (name, passhash))
        except ValueError:
            return render_template("error.html", errorcode=400, message="Username is Already taken")
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE username = ?", (name,))
        id = cursor.fetchone()
        conn.close()
        session["user_id"] = id["id"]
        return redirect("/")
    return render_template("register.html")


@app.route("/quote", methods = ["GET", "POST"]) # DESIGN PAGE
def quote():
    if not login_check():
        return redirect("/login")
    if request.method == "POST":
        crypto = request.form.get("crypto").lower()
        if not crypto:
            return redirect("/quote")
        url = f"https://api.coincap.io/v2/assets/{crypto}"
        response = requests.get(url, headers=headers)
        if not response:
            return render_template("error.html", errorcode="404", message="no response")
        data = response.json()
        print(data)
        price = data["data"]["priceUsd"] # ADD FUNCTIONALITY TO DISPLAY ALL THE INFO NOT JUST PRICE
        return render_template("quoted.html", crypto=crypto, price=price)
    return render_template("quote.html")


@app.route("/buy", methods = ["GET", "POST"])
def buy():
    if not login_check:
        return redirect("/")
    if request.method == "POST":
        name = request.form.get("name")
        quantity = request.form.get("quantity")
        if not name or quantity:
            return redirect ("/buy")
        url = f"https://api.coincap.io/v2/assets/{symbol}"
        response = requests.get(url, headers=headers)