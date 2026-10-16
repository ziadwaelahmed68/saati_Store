import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.aws import get_dynamodb_client, get_dynamodb_resource
from shared.config import Config

INITIAL_PRODUCTS = [
    ("1", "Orion", "smart", Decimal("249.00"), "Titanium-cased smartwatch with AMOLED sapphire display and 7-day battery."),
    ("2", "Nova", "smart", Decimal("199.00"), "Ultra-thin fitness and notification smartwatch with heart-rate tracking."),
    ("3", "Pulse", "smart", Decimal("149.00"), "Everyday active smartwatch with waterproof casing and GPS."),
    ("4", "Heritage", "classic", Decimal("229.00"), "Automatic mechanical dress watch with brushed steel case."),
    ("5", "Meridian", "classic", Decimal("179.00"), "Minimalist dual-time classic timepiece with Italian leather strap."),
    ("6", "Regent", "classic", Decimal("289.00"), "Chronograph classic watch with domed sapphire crystal."),
    ("7", "Vega", "smart", Decimal("279.00"), "Solar-assisted multisport smartwatch with barometer and compass."),
    ("8", "Atlas", "smart", Decimal("329.00"), "Flagship dive-rated smartwatch with ECG and blood oxygen sensors."),
    ("9", "Zenith", "smart", Decimal("189.00"), "Sleek hybrid smartwatch with concealed OLED display."),
    ("10", "Oxford", "classic", Decimal("159.00"), "Classic Roman-numeral dial watch with mesh stainless bracelet."),
    ("11", "Sovereign", "classic", Decimal("349.00"), "Swiss-movement gold-bezel timepiece with exhibition caseback."),
    ("12", "Aurora", "classic", Decimal("209.00"), "Mother-of-pearl dial classic watch with rose-brass accents."),
]


def wait_for_dynamodb(client, retries: int = 20, delay: float = 1.5):
    for attempt in range(1, retries + 1):
        try:
            return client.list_tables().get("TableNames", [])
        except Exception as exc:
            print(f"Waiting for DynamoDB to be ready (attempt {attempt}/{retries})...")
            if attempt == retries:
                raise exc
            time.sleep(delay)
    return []


def ensure_tables():
    client = get_dynamodb_client()
    existing = wait_for_dynamodb(client)

    if Config.PRODUCTS_TABLE not in existing:
        client.create_table(
            TableName=Config.PRODUCTS_TABLE,
            KeySchema=[{"AttributeName": "productId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "productId", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
                {"AttributeName": "entityType", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "CategoryCreatedAtIndex",
                    "KeySchema": [
                        {"AttributeName": "category", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "EntityCreatedAtIndex",
                    "KeySchema": [
                        {"AttributeName": "entityType", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=Config.PRODUCTS_TABLE)

    if Config.ORDERS_TABLE not in existing:
        client.create_table(
            TableName=Config.ORDERS_TABLE,
            KeySchema=[{"AttributeName": "orderId", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "orderId", "AttributeType": "S"},
                {"AttributeName": "customerEmail", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
                {"AttributeName": "entityType", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "CustomerOrdersIndex",
                    "KeySchema": [
                        {"AttributeName": "customerEmail", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "StatusCreatedAtIndex",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "EntityCreatedAtIndex",
                    "KeySchema": [
                        {"AttributeName": "entityType", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=Config.ORDERS_TABLE)

    if Config.USERS_TABLE not in existing:
        client.create_table(
            TableName=Config.USERS_TABLE,
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=Config.USERS_TABLE)


def seed_initial_products():
    ddb = get_dynamodb_resource()
    table = ddb.Table(Config.PRODUCTS_TABLE)
    now_iso = datetime.now(timezone.utc).isoformat()

    for pid, name, category, price, desc in INITIAL_PRODUCTS:
        table.put_item(
            Item={
                "productId": pid,
                "entityType": "PRODUCT",
                "name": name,
                "category": category,
                "price": price,
                "description": desc,
                "stockQuantity": 25,
                "imageKey": f"products/{name.lower()}.jpg",
                "rating": Decimal("4.8"),
                "createdAt": now_iso,
                "updatedAt": now_iso,
            }
        )


def seed_admin_from_env():
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@saati.com").strip().lower()
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD", "Admin123!")
    if not admin_email or not admin_password:
        return

    ddb = get_dynamodb_resource()
    table = ddb.Table(Config.USERS_TABLE)
    now_iso = datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            "email": admin_email,
            "name": os.environ.get("INITIAL_ADMIN_NAME", "SAATI Admin"),
            "passwordHash": generate_password_hash(admin_password),
            "role": "admin",
            "createdAt": now_iso,
            "updatedAt": now_iso,
        }
    )


if __name__ == "__main__":
    ensure_tables()
    seed_initial_products()
    seed_admin_from_env()
    print("✅ DynamoDB tables verified, 12 watches seeded, and admin user created.")