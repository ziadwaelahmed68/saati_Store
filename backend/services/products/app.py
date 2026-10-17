import logging
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from boto3.dynamodb.conditions import Attr, Key
from flask import Flask, jsonify, request
from flask_cors import CORS

from shared.aws import get_dynamodb_resource, get_s3_client
from shared.config import Config
from shared.http import configure_logging, err
from shared.pagination import decode_cursor, encode_cursor
from shared.security import require_role

configure_logging("products-service")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=Config.ALLOWED_ORIGINS)


def _products_table():
    return get_dynamodb_resource().Table(Config.PRODUCTS_TABLE)


def _resolve_image_url(image_key: str | None, existing_url: str | None = None) -> str:
    if existing_url and existing_url.startswith("https://"):
        return existing_url
    if not image_key:
        return ""
    clean_key = image_key.lstrip("/")
    if Config.CLOUDFRONT_DOMAIN:
        return f"https://{Config.CLOUDFRONT_DOMAIN.removeprefix('https://')}/{clean_key}"
    if Config.S3_BUCKET_NAME:
        try:
            s3 = get_s3_client()
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": Config.S3_BUCKET_NAME, "Key": clean_key},
                ExpiresIn=Config.PRESIGNED_URL_EXPIRES,
            )
        except Exception as exc:
            logger.warning("Could not generate presigned URL: %s", type(exc).__name__)
    return ""


def _serialize_product(item: dict) -> dict:
    image_key = item.get("imageKey") or ""
    category = (item.get("category") or item.get("type") or "smart").lower()
    price = float(item.get("price", 0))
    stock = int(item.get("stockQuantity", item.get("stock", 25)))
    rating = float(item["rating"]) if item.get("rating") is not None else None

    return {
        "productId": str(item.get("productId") or item.get("id")),
        "id": str(item.get("productId") or item.get("id")),
        "name": item.get("name", ""),
        "description": item.get("description", ""),
        "price": price,
        "category": category,
        "type": category,
        "stockQuantity": stock,
        "imageKey": image_key,
        "imageUrl": _resolve_image_url(image_key, item.get("imageUrl")),
        "rating": rating,
        "createdAt": item.get("createdAt", ""),
        "updatedAt": item.get("updatedAt", ""),
    }


def _validate_product_payload(d: dict, partial: bool = False) -> tuple[dict | None, str | None]:
    cleaned = {}

    if not partial or "name" in d:
        name = str(d.get("name") or "").strip()
        if not name or len(name) > 120:
            return None, "Product name is required (1-120 characters)."
        cleaned["name"] = name

    if not partial or "description" in d:
        desc = str(d.get("description") or "").strip()
        if len(desc) > 2000:
            return None, "Description must be under 2000 characters."
        cleaned["description"] = desc

    if not partial or "category" in d or "type" in d:
        cat = str(d.get("category") or d.get("type") or "").strip().lower()
        if cat not in ("smart", "classic"):
            return None, "Category must be either 'smart' or 'classic'."
        cleaned["category"] = cat

    if not partial or "price" in d:
        try:
            price = Decimal(str(d.get("price"))).quantize(Decimal("0.01"))
            if price < Decimal("0.00") or price > Decimal("100000.00"):
                return None, "Price must be between 0 and 100,000."
            cleaned["price"] = price
        except (InvalidOperation, TypeError, ValueError):
            return None, "Valid numeric price is required."

    if not partial or "stockQuantity" in d:
        try:
            stock = int(d.get("stockQuantity", 0))
            if stock < 0 or stock > 100000:
                return None, "Stock quantity must be between 0 and 100,000."
            cleaned["stockQuantity"] = stock
        except (TypeError, ValueError):
            return None, "Stock quantity must be a valid integer."

    if "imageKey" in d:
        cleaned["imageKey"] = str(d.get("imageKey") or "").strip().lstrip("/")

    if "imageUrl" in d:
        cleaned["imageUrl"] = str(d.get("imageUrl") or "").strip()

    if "rating" in d and d.get("rating") not in (None, ""):
        try:
            r = Decimal(str(d.get("rating"))).quantize(Decimal("0.1"))
            if r < Decimal("0.0") or r > Decimal("5.0"):
                return None, "Rating must be between 0.0 and 5.0."
            cleaned["rating"] = r
        except (InvalidOperation, TypeError, ValueError):
            return None, "Rating must be a valid number."

    return cleaned, None


@app.get("/api/health")
def health():
    return jsonify(status="ok", service="products"), 200


@app.get("/api/products")
def list_products():
    category = (request.args.get("category") or request.args.get("type") or "").strip().lower()
    search_q = (request.args.get("q") or "").strip().lower()
    limit = min(max(int(request.args.get("limit", 24)), 1), 100)
    cursor = decode_cursor(request.args.get("cursor"))

    table = _products_table()
    query_kwargs = {"Limit": limit}
    if cursor:
        query_kwargs["ExclusiveStartKey"] = cursor

    if category in ("smart", "classic"):
        # Uses CategoryCreatedAtIndex GSI instead of full table scan
        query_kwargs["IndexName"] = "CategoryCreatedAtIndex"
        query_kwargs["KeyConditionExpression"] = Key("category").eq(category)
        query_kwargs["ScanIndexForward"] = False
        resp = table.query(**query_kwargs)
    else:
        try:
            resp = table.query(
                IndexName="EntityCreatedAtIndex",
                KeyConditionExpression=Key("entityType").eq("PRODUCT"),
                ScanIndexForward=False,
                **query_kwargs,
            )
        except Exception:
            # Fallback clean scan without query-only parameters
            resp = table.scan(**query_kwargs)
    items = [_serialize_product(i) for i in resp.get("Items", [])]
    if search_q:
        items = [
            p for p in items
            if search_q in p["name"].lower() or search_q in p["description"].lower()
        ]

    return jsonify(
        products=items,
        nextCursor=encode_cursor(resp.get("LastEvaluatedKey")),
    ), 200


@app.get("/api/products/<product_id>")
def get_product(product_id: str):
    table = _products_table()
    item = table.get_item(Key={"productId": product_id}).get("Item")
    if not item:
        return err("Product not found.", 404)
    return jsonify(_serialize_product(item)), 200


@app.post("/api/admin/products")
@require_role("admin")
def create_product():
    d = request.get_json(silent=True) or {}
    cleaned, error = _validate_product_payload(d, partial=False)
    if error:
        return err(error, 400)

    now_iso = datetime.now(timezone.utc).isoformat()
    product_id = str(d.get("productId") or f"PRD-{secrets.token_hex(4).upper()}").strip()

    item = {
        "productId": product_id,
        "entityType": "PRODUCT",
        "name": cleaned["name"],
        "description": cleaned.get("description", ""),
        "category": cleaned["category"],
        "price": cleaned["price"],
        "stockQuantity": cleaned["stockQuantity"],
        "imageKey": cleaned.get("imageKey", ""),
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    if "imageUrl" in cleaned and cleaned["imageUrl"]:
        item["imageUrl"] = cleaned["imageUrl"]
    if "rating" in cleaned:
        item["rating"] = cleaned["rating"]

    table = _products_table()
    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(productId)",
        )
    except Exception:
        return err("A product with that ID already exists.", 409)

    return jsonify(_serialize_product(item)), 201


@app.put("/api/admin/products/<product_id>")
@require_role("admin")
def update_product(product_id: str):
    d = request.get_json(silent=True) or {}
    cleaned, error = _validate_product_payload(d, partial=True)
    if error:
        return err(error, 400)
    if not cleaned:
        return err("No valid fields provided for update.", 400)

    table = _products_table()
    existing = table.get_item(Key={"productId": product_id}).get("Item")
    if not existing:
        return err("Product not found.", 404)

    now_iso = datetime.now(timezone.utc).isoformat()
    cleaned["updatedAt"] = now_iso
    cleaned["entityType"] = "PRODUCT"

    expr_parts = []
    expr_names = {}
    expr_vals = {}
    for idx, (k, v) in enumerate(cleaned.items()):
        nk = f"#f{idx}"
        vk = f":v{idx}"
        expr_parts.append(f"{nk} = {vk}")
        expr_names[nk] = k
        expr_vals[vk] = v

    resp = table.update_item(
        Key={"productId": product_id},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
        ConditionExpression="attribute_exists(productId)",
        ReturnValues="ALL_NEW",
    )
    return jsonify(_serialize_product(resp["Attributes"])), 200


@app.delete("/api/admin/products/<product_id>")
@require_role("admin")
def delete_product(product_id: str):
    table = _products_table()
    existing = table.get_item(Key={"productId": product_id}).get("Item")
    if not existing:
        return err("Product not found.", 404)

    table.delete_item(Key={"productId": product_id})

    # Clean up associated S3 image if present
    image_key = existing.get("imageKey")
    if image_key and Config.S3_BUCKET_NAME:
        try:
            get_s3_client().delete_object(Bucket=Config.S3_BUCKET_NAME, Key=image_key)
        except Exception as exc:
            logger.warning("Failed to delete S3 object %s: %s", image_key, type(exc).__name__)

    return jsonify(deleted=True, productId=product_id), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8082)))