import os, secrets, time
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import boto3
# إعدادات AWS Cognito اللي طلعناها
COGNITO_USER_POOL_ID = "eu-central-1_61kHuKfU3"
COGNITO_CLIENT_ID = "6njag5ke4ps7sar3ecp31r1h4v"
AWS_REGION = "eu-central-1"
cognito_client = boto3.client('cognito-idp', region_name=AWS_REGION)


ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
TOKEN_TTL = 7 * 24 * 3600
FREE_SHIPPING_FROM, SHIPPING, PROMO_CODE, PROMO_RATE = 300, 9.99, "SAATI10", 0.10

app = Flask(__name__)
CORS(app, origins=ORIGINS)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

PRODUCTS = {p[0]: dict(id=p[0], name=p[1], type=p[2], price=p[3]) for p in [
    (1, "Orion", "smart", 249), (2, "Nova", "smart", 199), (3, "Pulse", "smart", 149),
    (7, "Vega", "smart", 279), (8, "Atlas", "smart", 329), (9, "Zenith", "smart", 189),
    (4, "Heritage", "classic", 229), (5, "Meridian", "classic", 179), (6, "Regent", "classic", 289),
    (10, "Oxford", "classic", 159), (11, "Sovereign", "classic", 349), (12, "Aurora", "classic", 209)]}

# --- تخزين البيانات في الذاكرة (In-Memory Storage) بدلاً من SQLite ---
USERS = {}     # Format: {email: {"name": name, "pw": hashed_pw}}
SESSIONS = {}  # Format: {token: {"email": email, "expires": timestamp}}
ORDERS = []    # Format: [{"id": oid, "email": email, "items": [...], "total": total, ...}]


def err(msg, code=400):
    return jsonify(error=msg), code


def new_session(email):
    t = secrets.token_hex(24)
    SESSIONS[t] = {"email": email, "expires": time.time() + TOKEN_TTL}
    return t


def current_user():
    t = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    session = SESSIONS.get(t)
    if session and session["expires"] > time.time():
        return session["email"]
    return None


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
    try:
        cognito_client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            Password=pw,
            UserAttributes=[{'Name': 'name', 'Value': name}]
        )
    except Exception as e:
        return err(str(e), 400)
    return jsonify(token=new_session(email), name=name)


@app.post("/api/signin")
@limiter.limit("5 per minute")
def signin():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    
    try:
        # التحقق من البيانات عبر AWS Cognito
        response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': pw
            }
        )
    except Exception:
        return err("Email or password is incorrect.", 401)
        
    return jsonify(token=new_session(email), name=email.split('@')[0])


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
    
    ORDERS.append({
        "id": oid,
        "email": email,
        "items": [{"id": p["id"], "q": q} for p, q in lines],
        "total": total,
        "address": address,
        "method": method,
        "created": time.time()
    })
    return jsonify(order_id=oid, total=total)


@app.get("/api/orders")
def orders():
    email = current_user()
    if not email:
        return err("Please sign in.", 401)
    user_orders = [
        {k: v for k, v in o.items() if k not in ("email", "address")}
        for o in reversed(ORDERS) if o["email"] == email
    ]
    return jsonify(user_orders)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))