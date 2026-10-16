import io
import os
import pytest
import boto3
from moto import mock_aws
from werkzeug.security import generate_password_hash

os.environ["AWS_REGION"] = "eu-central-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AUTH_PROVIDER"] = "dynamodb"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-for-hmac-signing-32bytes"
os.environ["S3_BUCKET_NAME"] = "test-saati-images-bucket"
os.environ["CLOUDFRONT_DOMAIN"] = "d111111abcdef8.cloudfront.net"

from app import app as flask_app
from backend.scripts.migrate_dynamodb import ensure_tables, seed_initial_products
from backend.shared.config import Config


@pytest.fixture()
def client():
    with mock_aws():
        ensure_tables()
        seed_initial_products()
        s3 = boto3.client("s3", region_name="eu-central-1")
        s3.create_bucket(
            Bucket=Config.S3_BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
        )
        ddb = boto3.resource("dynamodb", region_name="eu-central-1")
        ddb.Table(Config.USERS_TABLE).put_item(
            Item={
                "email": "admin@saati.test",
                "name": "Admin User",
                "passwordHash": generate_password_hash("AdminPass123!"),
                "role": "admin",
            }
        )
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as c:
            yield c


def test_customer_signup_signin_and_redirect(client):
    res = client.post(
        "/api/signup",
        json={"name": "Ziad", "email": "customer@saati.test", "password": "Password123", "role": "admin"},
    )
    assert res.status_code == 201
    data = res.get_json()
    # Role supplied by client must be ignored; always customer
    assert data["role"] == "customer"
    assert data["redirectTo"] == "/"

    login_res = client.post(
        "/api/signin",
        json={"email": "customer@saati.test", "password": "Password123"},
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["redirectTo"] == "/"


def test_admin_login_and_redirect(client):
    res = client.post(
        "/api/signin",
        json={"email": "admin@saati.test", "password": "AdminPass123!"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["role"] == "admin"
    assert data["redirectTo"] == "/admin"


def test_invalid_credentials_rejected(client):
    res = client.post(
        "/api/signin",
        json={"email": "admin@saati.test", "password": "WrongPassword"},
    )
    assert res.status_code == 401


def test_customer_rejected_from_admin_endpoints(client):
    signup = client.post(
        "/api/signup",
        json={"name": "User", "email": "user@saati.test", "password": "Password123"},
    ).get_json()
    headers = {"Authorization": f"Bearer {signup['token']}"}

    assert client.get("/api/admin/orders", headers=headers).status_code == 403
    assert client.get("/api/admin/stats", headers=headers).status_code == 403
    assert client.post("/api/admin/products", json={}, headers=headers).status_code == 403
    assert client.put("/api/admin/products/1", json={}, headers=headers).status_code == 403
    assert client.delete("/api/admin/products/1", headers=headers).status_code == 403


def test_admin_product_crud_and_dynamodb_retrieval(client):
    admin_token = client.post(
        "/api/signin",
        json={"email": "admin@saati.test", "password": "AdminPass123!"},
    ).get_json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create product
    create_res = client.post(
        "/api/admin/products",
        headers=headers,
        json={
            "name": "Chronos Pro",
            "category": "smart",
            "price": 399.50,
            "stockQuantity": 10,
            "description": "Titanium dive watch",
            "imageKey": "products/chronos.jpg",
        },
    )
    assert create_res.status_code == 201
    prod = create_res.get_json()
    pid = prod["productId"]
    assert prod["imageUrl"] == "https://d111111abcdef8.cloudfront.net/products/chronos.jpg"

    # Edit product
    upd_res = client.put(
        f"/api/admin/products/{pid}",
        headers=headers,
        json={"price": 420.00, "stockQuantity": 8},
    )
    assert upd_res.status_code == 200
    assert upd_res.get_json()["price"] == 420.0

    # Delete product
    del_res = client.delete(f"/api/admin/products/{pid}", headers=headers)
    assert del_res.status_code == 200
    assert client.get(f"/api/products/{pid}").status_code == 404


def test_image_upload_validation_and_presigned_url(client):
    admin_token = client.post(
        "/api/signin",
        json={"email": "admin@saati.test", "password": "AdminPass123!"},
    ).get_json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Reject invalid MIME type
    bad = client.post(
        "/api/admin/images/upload-url",
        headers=headers,
        json={"filename": "hack.exe", "contentType": "application/x-msdownload", "fileSize": 1024},
    )
    assert bad.status_code == 400

    # Valid presigned upload URL
    good = client.post(
        "/api/admin/images/upload-url",
        headers=headers,
        json={"filename": "orion.png", "contentType": "image/png", "fileSize": 20480},
    )
    assert good.status_code == 200
    body = good.get_json()
    assert body["imageKey"].startswith("products/")
    assert "uploadUrl" in body


def test_checkout_authoritative_pricing_idempotency_and_status_transitions(client):
    cust_token = client.post(
        "/api/signup",
        json={"name": "Buyer", "email": "buyer@saati.test", "password": "Password123"},
    ).get_json()["token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}", "Idempotency-Key": "idem-key-001"}

    # Product 1 ("Orion") costs $249 in DynamoDB. Even if client sends forged price, server computes $249 * 2 = $498,
    # applies 10% promo SAATI10 -> $448.20, free shipping (>= $300).
    checkout_res = client.post(
        "/api/checkout",
        headers=cust_headers,
        json={
            "items": [{"productId": "1", "quantity": 2, "price": 0.01}],
            "address": "15 El-Gomhoria St, Mansoura",
            "method": "cod",
            "promo": "SAATI10",
        },
    )
    assert checkout_res.status_code == 201
    order_data = checkout_res.get_json()
    assert order_data["total"] == 448.2
    oid = order_data["orderId"]

    # Retry with same Idempotency-Key must not create duplicate order or double-decrement stock
    retry_res = client.post(
        "/api/checkout",
        headers=cust_headers,
        json={
            "items": [{"productId": "1", "quantity": 2}],
            "address": "15 El-Gomhoria St, Mansoura",
            "method": "cod",
            "promo": "SAATI10",
        },
    )
    assert retry_res.status_code == 200
    assert retry_res.get_json()["orderId"] == oid
    assert retry_res.get_json()["deduplicated"] is True

    # Verify stock decremented by 2 (from 25 to 23)
    prod_after = client.get("/api/products/1").get_json()
    assert prod_after["stockQuantity"] == 23

    # Admin order status validation
    admin_token = client.post(
        "/api/signin",
        json={"email": "admin@saati.test", "password": "AdminPass123!"},
    ).get_json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Invalid transition PENDING -> DELIVERED rejected
    invalid_st = client.patch(
        f"/api/admin/orders/{oid}/status",
        headers=admin_headers,
        json={"status": "DELIVERED"},
    )
    assert invalid_st.status_code == 400

    # Valid transition PENDING -> CONFIRMED succeeds
    valid_st = client.patch(
        f"/api/admin/orders/{oid}/status",
        headers=admin_headers,
        json={"status": "CONFIRMED"},
    )
    assert valid_st.status_code == 200
    assert valid_st.get_json()["status"] == "CONFIRMED"