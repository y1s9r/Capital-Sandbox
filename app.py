from flask import Flask, render_template, request, session, flash, redirect
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

sqliteConnection = sqlite3.connect('database.db')
cursor = sqliteConnection.cursor()


@app.route("/")
def main():
    return


@app.route("/login")
def login():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        if not name or not password:
            return redirect("/login")
        cursor.execute("SELECT * FROM users WHERE username = ?", name)
        data = cursor.fetchall()
        if len(data) != 1 or not check_password_hash(data[0]["hash"], password):
            return render_template("error.html", errorcode=400, message="Incorrect Username or Password")
        session["user_id"] = data[0]["id"]
        return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/register")
def register():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if not name or not password or not confirm:
            return redirect("/")
        if password != confirm:
            return render_template("error.html", errorcode="400", message="Password does not match")
        passhash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, hash) VALUES(?, ?)", name, passhash)
        cursor.execute("SELECT id FROM users WHERE username = ?", name)
        id = cursor.fetchall()
        session["user_id"] = id[0]["id"]
        return redirect("/")
    return render_template("register.html")


sqliteConnection.commit()
sqliteConnection.close()