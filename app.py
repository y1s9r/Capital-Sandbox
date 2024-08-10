from flask import Flask, render_template, request, session, redirect
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from helper import login_check, get_db_connection, lookup, get_wallet, usd


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.jinja_env.filters["usd"] = usd


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def main():
    if not login_check():
        return redirect("/login")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, SUM(shares) AS total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0 ORDER BY symbol asc", (session["user_id"],))
    holdings = cursor.fetchall()
    conn.close()
    wallet = get_wallet()
    total = 0.0 + wallet
    for i in range(len(holdings)):
        symbol, total_shares = holdings[i]
        price_info = lookup(symbol)
        if price_info is not None:
            total_price = float(float(price_info['price']) * int(total_shares))
            total = total + total_price
            holdings[i] = (symbol, total_shares, total_price)
        else:
            holdings[i] = (symbol, total_shares, "N/A")
    return render_template("index.html", holdings=holdings, wallet=wallet, total=total)


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
        symbol = request.form.get("symbol")
        if not symbol:
            return redirect("/quote")
        data = lookup(symbol)
        if not data:
            return render_template("error.html", errorcode="400", message="Invalid Stock")
        price = data["price"]
        return render_template("quoted.html", symbol=symbol.upper(), price=price)
    return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
def buy():
    if not login_check():
        return redirect("/login")
    if request.method == "POST":
        symbol = request.form.get("symbol").lower()
        quantity = request.form.get("quantity")
        if not symbol or not quantity:
            return redirect("/buy")
        try:
            quantity = int(quantity)
            if quantity <= 0:
                return render_template("error.html", errorcode="400", message="Invalid quantity of Stock")
        except ValueError:
            return render_template("error.html", errorcode="400", message="Quantity must be a valid number")
        
        data = lookup(symbol)
        if not data:
            return render_template("error.html", errorcode="400", message="Invalid stock symbol")
        wallet = get_wallet()
        price = float(data["price"]) * quantity
        if price > wallet:
            return render_template("error.html", errorcode="400", message="You do not have enough money to buy these many shares")
        wallet -= price
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, symbol, shares, cost) VALUES (?, ?, ?, ?)", (session["user_id"], data["symbol"], quantity, price))
        cursor.execute("UPDATE users SET cash = ? WHERE id = ?", (wallet, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
def sell():
    if not login_check():
        return redirect("/login")
    
    if request.method == "POST":
        symbol = request.form.get("symbol").lower()
        shares = request.form.get("shares")
        if not symbol or not shares:
            return redirect("/sell")
        try:
            shares = int(shares)
            if shares <= 0:
                return render_template("error.html", errorcode="400", message="Invalid number of shares")
        except ValueError:
            return render_template("error.html", errorcode="400", message="Shares must be a valid number")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(shares) AS total_shares FROM transactions WHERE user_id = ? AND symbol = ?", (session["user_id"], symbol))
        holding_row = cursor.fetchone()
        conn.close()
        if not holding_row or holding_row[0] is None or int(holding_row[0]) < shares:
            return render_template("error.html", errorcode="400", message="You do not own that many shares")
        data = lookup(symbol)
        if not data:
            return render_template("error.html", errorcode="400", message="Invalid stock symbol")
        price = data["price"]
        total_sale_value = float(price) * shares
        wallet = get_wallet()
        wallet += total_sale_value
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, symbol, shares, cost) VALUES (?, ?, ?, ?)", (session["user_id"], symbol, -shares, -total_sale_value))
        cursor.execute("UPDATE users SET cash = ? WHERE id = ?", (wallet, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("sell.html")


@app.route("/history")
def history():
    if not login_check:
        return redirect("/login")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, shares, cost, timestamp FROM transactions WHERE user_id = ? LIMIT 20", (session["user_id"],))
    data = cursor.fetchall()
    conn.close()
    return render_template("history.html", transactions=data)


@app.route("/addmoney", methods=["GET","POST"])
def addmoney():
    if not login_check:
        return redirect("/login")
    if request.method == "POST":
        money = request.form.get("money")
        if not money or float(money) <= 0:
            return render_template("error.html", errorcode="400", message="Invalid amount of money")
        if float(money) > 25000:
            return render_template("error.html", errorcode="400", message="You can not add more than $25000 at once")
        wallet = get_wallet()
        wallet += float(money)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET cash = ? WHERE id = ?", (wallet, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("addmoney.html")
