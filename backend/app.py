import json, os, secrets, sqlite3, time
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get("DB_PATH", "saati.db")
ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
TOKEN_TTL = 7 * 24 * 3600
FREE_SHIPPING_FROM, SHIPPING, PROMO_CODE, PROMO_RATE = 300, 9.99, "SAATI10", 0.10

app = Flask(__name__)
CORS(app, origins=ORIGINS)

PRODUCTS = {p[0]: dict(id=p[0], name=p[1], type=p[2], price=p[3]) for p in [
    (1, "Orion", "smart", 249), (2, "Nova", "smart", 199), (3, "Pulse", "smart", 149),
    (7, "Vega", "smart", 279), (8, "Atlas", "smart", 329), (9, "Zenith", "smart", 189),
    (4, "Heritage", "classic", 229), (5, "Meridian", "classic", 179), (6, "Regent", "classic", 289),
    (10, "Oxford", "classic", 159), (11, "Sovereign", "classic", 349), (12, "Aurora", "classic", 209)]}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init_db():
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, pw TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, email TEXT, expires REAL);
    CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, email TEXT, items TEXT, total REAL,
        address TEXT, method TEXT, created REAL);""")
    c.commit(); c.close()


init_db()


def err(msg, code=400):
    return jsonify(error=msg), code


def new_session(email):
    t = secrets.token_hex(24)
    db().execute("INSERT INTO sessions VALUES(?,?,?)", (t, email, time.time() + TOKEN_TTL))
    db().commit()
    return t


def current_user():
    t = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    row = db().execute("SELECT email FROM sessions WHERE token=? AND expires>?", (t, time.time())).fetchone()
    return row["email"] if row else None


@app.get("/api/health")
def health():
    return "ok"


@app.get("/api/products")
def products():
    t = request.args.get("type")
    return jsonify([p for p in PRODUCTS.values() if not t or p["type"] == t])


@app.post("/api/signup")
def signup():
    d = request.get_json(silent=True) or {}
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
    if not name or "@" not in email or len(pw) < 6:
        return err("Enter your name, a valid email and a password of 6+ characters.")
    if db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        return err("That email already has an account. Sign in instead.", 409)
    db().execute("INSERT INTO users VALUES(?,?,?)", (email, name, generate_password_hash(pw)))
    return jsonify(token=new_session(email), name=name)


@app.post("/api/signin")
def signin():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    u = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or not check_password_hash(u["pw"], d.get("password") or ""):
        return err("Email or password is incorrect.", 401)
    return jsonify(token=new_session(email), name=u["name"])


@app.post("/api/checkout")
def checkout():
    email = current_user()
    if not email:
        return err("Please sign in to place your order.", 401)
    d = request.get_json(silent=True) or {}
    lines = []
    for i in d.get("items") or []:
        p = PRODUCTS.get(i.get("id"))
        q = i.get("q")
        if not p or not isinstance(q, int) or not 1 <= q <= 20:
            return err("Your cart has an invalid item.")
        lines.append((p, q))
    if not lines:
        return err("Your cart is empty.")
    address, method = (d.get("address") or "").strip(), d.get("method")
    if len(address) < 5 or method not in ("card", "cod"):
        return err("Enter a shipping address and a payment method.")
    sub = sum(p["price"] * q for p, q in lines)  # prices always come from the server
    disc = sub * PROMO_RATE if (d.get("promo") or "").upper() == PROMO_CODE else 0
    ship = 0 if sub - disc >= FREE_SHIPPING_FROM else SHIPPING
    total = round(sub - disc + ship, 2)
    oid = "S-" + secrets.token_hex(4).upper()
    db().execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?)", (
        oid, email, json.dumps([{"id": p["id"], "q": q} for p, q in lines]), total, address, method, time.time()))
    db().commit()
    # Payment gateway hook (Stripe / Paymob / Fawry) goes here. Never accept raw card numbers on this server.
    return jsonify(order_id=oid, total=total)


@app.get("/api/orders")
def orders():
    email = current_user()
    if not email:
        return err("Please sign in.", 401)
    rows = db().execute("SELECT id,items,total,method,created FROM orders WHERE email=? ORDER BY created DESC", (email,))
    return jsonify([dict(r, items=json.loads(r["items"])) for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
