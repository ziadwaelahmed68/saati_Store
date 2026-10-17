import logging
import os
from datetime import datetime, timezone
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

from shared.aws import get_cognito_client, get_dynamodb_resource
from shared.config import Config
from shared.http import configure_logging, err
from shared.security import issue_token, require_auth

configure_logging("auth-service")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=Config.ALLOWED_ORIGINS)

def _users_table():
    return get_dynamodb_resource().Table(Config.USERS_TABLE)


def _resolve_cognito_role(email: str) -> tuple[str, str]:
    """Fetch user attributes and Cognito group membership from backend-controlled Cognito."""
    cognito = get_cognito_client()
    role = "customer"
    name = email.split("@")[0]

    try:
        user_resp = cognito.admin_get_user(
            UserPoolId=Config.COGNITO_USER_POOL_ID, Username=email
        )
        for attr in user_resp.get("UserAttributes", []):
            if attr["Name"] == "name":
                name = attr["Value"]
            elif attr["Name"] == "custom:role" and attr["Value"] == "admin":
                role = "admin"

        groups_resp = cognito.admin_list_groups_for_user(
            Username=email, UserPoolId=Config.COGNITO_USER_POOL_ID
        )
        group_names = {g["GroupName"].lower() for g in groups_resp.get("Groups", [])}
        if "admin" in group_names or "admins" in group_names:
            role = "admin"
    except Exception as exc:
        logger.warning("Failed to inspect Cognito groups for user: %s", type(exc).__name__)

    return name, role


@app.get("/api/health")
def health():
    return jsonify(status="ok", service="auth"), 200


@app.post("/api/signup")
def signup():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""

    if not name or "@" not in email or len(pw) < 6:
        return err("Enter your name, a valid email and a password of 6+ characters.", 400)

    # Public signup strictly creates 'customer' accounts; client-supplied role is ignored.
    role = "customer"

    if Config.AUTH_PROVIDER == "cognito":
        try:
            cognito = get_cognito_client()
            cognito.sign_up(
                ClientId=Config.COGNITO_CLIENT_ID,
                Username=email,
                Password=pw,
                UserAttributes=[{"Name": "name", "Value": name}],
            )
        except Exception as exc:
            logger.info("Cognito signup rejected: %s", type(exc).__name__)
            return err("Unable to create account. The email may already be registered.", 400)
    else:
        table = _users_table()
        existing = table.get_item(Key={"email": email}).get("Item")
        if existing:
            return err("That email already has an account. Sign in instead.", 409)

        now_iso = datetime.now(timezone.utc).isoformat()
        table.put_item(
            Item={
                "email": email,
                "name": name,
                "passwordHash": generate_password_hash(pw),
                "role": role,
                "createdAt": now_iso,
                "updatedAt": now_iso,
            },
            ConditionExpression="attribute_not_exists(email)",
        )

    token = issue_token(email=email, name=name, role=role)
    return jsonify(
        token=token,
        name=name,
        email=email,
        role=role,
        redirectTo="/",
    ), 201


@app.post("/api/signin")
def signin():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""

    if not email or not pw:
        return err("Email and password are required.", 400)

    if Config.AUTH_PROVIDER == "cognito":
        try:
            cognito = get_cognito_client()
            cognito.initiate_auth(
                ClientId=Config.COGNITO_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={"USERNAME": email, "PASSWORD": pw},
            )
            name, role = _resolve_cognito_role(email)
        except Exception:
            return err("Email or password is incorrect.", 401)
    else:
        table = _users_table()
        user_item = table.get_item(Key={"email": email}).get("Item")
        if not user_item or not check_password_hash(user_item.get("passwordHash", ""), pw):
            return err("Email or password is incorrect.", 401)
        name = user_item.get("name") or email.split("@")[0]
        # Role comes strictly from backend DynamoDB record
        role = "admin" if user_item.get("role") == "admin" else "customer"

    token = issue_token(email=email, name=name, role=role)
    redirect_to = "/admin" if role == "admin" else "/"
    return jsonify(
        token=token,
        name=name,
        email=email,
        role=role,
        redirectTo=redirect_to,
    ), 200


@app.get("/api/me")
@require_auth
def me():
    u = g.current_user
    return jsonify(
        email=u["sub"],
        name=u.get("name"),
        role=u.get("role", "customer"),
    ), 200


@app.post("/api/signout")
def signout():
    return jsonify(status="signed_out"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))