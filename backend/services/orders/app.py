import logging
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from flask import Flask, g, jsonify, request
from flask_cors import CORS

from shared.aws import get_dynamodb_client, get_dynamodb_resource
from shared.config import Config
from shared.http import configure_logging, err
from shared.pagination import decode_cursor, encode_cursor
from shared.security import require_auth, require_role

configure_logging("orders-service")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=Config.ALLOWED_ORIGINS)

VALID_STATUS_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


def _orders_table():
    return get_dynamodb_resource().Table(Config.ORDERS_TABLE)


def _products_table():
    return get_dynamodb_resource().Table(Config.PRODUCTS_TABLE)


def _serialize_order(item: dict, include_customer: bool = False) -> dict:
    items_out = []
    for line in item.get("items", []):
        items_out.append(
            {
                "productId": str(line.get("productId") or line.get("id")),
                "id": str(line.get("productId") or line.get("id")),
                "name": line.get("name", ""),
                "quantity": int(line.get("quantity") or line.get("q") or 1),
                "q": int(line.get("quantity") or line.get("q") or 1),
                "unitPrice": float(line.get("unitPrice", 0)),
            }
        )

    out = {
        "orderId": item.get("orderId") or item.get("id"),
        "id": item.get("orderId") or item.get("id"),
        "items": items_out,
        "subtotal": float(item.get("subtotal", item.get("total", 0))),
        "discount": float(item.get("discount", 0)),
        "shipping": float(item.get("shipping", 0)),
        "total": float(item.get("total", 0)),
        "method": item.get("method", "cod"),
        "status": item.get("status", "PENDING"),
        "createdAt": item.get("createdAt", ""),
        "updatedAt": item.get("updatedAt", ""),
    }
    if include_customer:
        out["customerEmail"] = item.get("customerEmail") or item.get("email", "")
        out["customerName"] = item.get("customerName", "")
        out["address"] = item.get("address", "")
    return out


@app.get("/api/health")
def health():
    return jsonify(status="ok", service="orders"), 200


@app.post("/api/checkout")
@require_auth
def checkout():
    user = g.current_user
    email = user["sub"]
    customer_name = user.get("name") or email.split("@")[0]
    d = request.get_json(silent=True) or {}

    raw_items = d.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return err("Your cart is empty.", 400)

    address = (d.get("address") or "").strip()
    method = (d.get("method") or "").strip()
    if len(address) < 5 or method not in ("card", "cod"):
        return err("Enter a valid shipping address and payment method.", 400)

    idempotency_key = (
        request.headers.get("Idempotency-Key") or d.get("idempotencyKey") or ""
    ).strip()

    orders_table = _orders_table()
    if idempotency_key:
        existing_idem = orders_table.get_item(
            Key={"orderId": f"IDEM#{email}#{idempotency_key}"}
        ).get("Item")
        if existing_idem:
            return jsonify(
                order_id=existing_idem["targetOrderId"],
                orderId=existing_idem["targetOrderId"],
                total=float(existing_idem["total"]),
                status="PENDING",
                deduplicated=True,
            ), 200

    # Aggregate duplicate product lines if present
    requested_qty: dict[str, int] = {}
    for entry in raw_items:
        pid = str(entry.get("productId") if entry.get("productId") is not None else entry.get("id") or "").strip()
        qty = entry.get("quantity") if entry.get("quantity") is not None else entry.get("q")
        if not pid or not isinstance(qty, int) or isinstance(qty, bool) or not (1 <= qty <= 20):
            return err("Your cart has an invalid item or quantity.", 400)
        requested_qty[pid] = requested_qty.get(pid, 0) + qty

    products_table = _products_table()
    order_lines = []
    subtotal = Decimal("0.00")

    for pid, qty in requested_qty.items():
        prod = products_table.get_item(Key={"productId": pid}).get("Item")
        if not prod:
            return err(f"Product '{pid}' is no longer available.", 400)
        stock = int(prod.get("stockQuantity", 0))
        if stock < qty:
            return err(f"Insufficient stock for {prod.get('name', pid)} (available: {stock}).", 409)

        unit_price = Decimal(str(prod["price"])).quantize(Decimal("0.01"))
        subtotal += unit_price * qty
        order_lines.append(
            {
                "productId": pid,
                "name": prod.get("name", ""),
                "quantity": qty,
                "unitPrice": unit_price,
            }
        )

    promo_applied = (d.get("promo") or "").strip().upper() == Config.PROMO_CODE
    discount = (subtotal * Decimal(str(Config.PROMO_RATE))).quantize(Decimal("0.01")) if promo_applied else Decimal("0.00")
    after_discount = subtotal - discount
    shipping = (
        Decimal("0.00")
        if after_discount >= Decimal(str(Config.FREE_SHIPPING_FROM))
        else Decimal(str(Config.SHIPPING_FEE)).quantize(Decimal("0.01"))
    )
    total = (after_discount + shipping).quantize(Decimal("0.01"))

    order_id = "S-" + secrets.token_hex(4).upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    order_item = {
        "orderId": order_id,
        "entityType": "ORDER",
        "customerEmail": email,
        "customerName": customer_name,
        "items": order_lines,
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "total": total,
        "address": address,
        "method": method,
        "status": "PENDING",
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }

    # Execute conditional stock decrement and order insertion atomically
    try:
        for line in order_lines:
            products_table.update_item(
                Key={"productId": line["productId"]},
                UpdateExpression="SET stockQuantity = stockQuantity - :q, updatedAt = :now",
                ConditionExpression="attribute_exists(productId) AND stockQuantity >= :q",
                ExpressionAttributeValues={":q": line["quantity"], ":now": now_iso},
            )
        orders_table.put_item(
            Item=order_item,
            ConditionExpression="attribute_not_exists(orderId)",
        )
        if idempotency_key:
            orders_table.put_item(
                Item={
                    "orderId": f"IDEM#{email}#{idempotency_key}",
                    "targetOrderId": order_id,
                    "total": total,
                    "createdAt": now_iso,
                }
            )
    except Exception as exc:
        logger.error("Checkout transaction failed: %s", type(exc).__name__)
        return err("Order could not be completed due to stock changes. Please try again.", 409)

    return jsonify(
        order_id=order_id,
        orderId=order_id,
        total=float(total),
        status="PENDING",
    ), 201


@app.get("/api/orders")
@require_auth
def customer_orders():
    email = g.current_user["sub"]
    table = _orders_table()
    resp = table.query(
        IndexName="CustomerOrdersIndex",
        KeyConditionExpression=Key("customerEmail").eq(email),
        ScanIndexForward=False,
        Limit=50,
    )
    orders = [_serialize_order(i, include_customer=False) for i in resp.get("Items", [])]
    return jsonify(orders), 200


@app.get("/api/admin/orders")
@require_role("admin")
def admin_list_orders():
    status_filter = (request.args.get("status") or "").strip().upper()
    search_q = (request.args.get("q") or "").strip().lower()
    date_from = (request.args.get("dateFrom") or "").strip()
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    cursor = decode_cursor(request.args.get("cursor"))

    table = _orders_table()
    query_kwargs = {"Limit": limit, "ScanIndexForward": False}
    if cursor:
        query_kwargs["ExclusiveStartKey"] = cursor

    if status_filter in VALID_STATUS_TRANSITIONS:
        query_kwargs["IndexName"] = "StatusCreatedAtIndex"
        key_cond = Key("status").eq(status_filter)
        if date_from:
            key_cond = key_cond & Key("createdAt").gte(date_from)
        query_kwargs["KeyConditionExpression"] = key_cond
        resp = table.query(**query_kwargs)
    else:
        query_kwargs["IndexName"] = "EntityCreatedAtIndex"
        key_cond = Key("entityType").eq("ORDER")
        if date_from:
            key_cond = key_cond & Key("createdAt").gte(date_from)
        query_kwargs["KeyConditionExpression"] = key_cond
        resp = table.query(**query_kwargs)

    items = [
        _serialize_order(i, include_customer=True)
        for i in resp.get("Items", [])
        if not str(i.get("orderId", "")).startswith("IDEM#")
    ]

    if search_q:
        items = [
            o for o in items
            if search_q in o["orderId"].lower()
            or search_q in o.get("customerEmail", "").lower()
            or search_q in o.get("customerName", "").lower()
        ]

    return jsonify(
        orders=items,
        nextCursor=encode_cursor(resp.get("LastEvaluatedKey")),
    ), 200


@app.get("/api/admin/orders/<order_id>")
@require_role("admin")
def admin_get_order(order_id: str):
    item = _orders_table().get_item(Key={"orderId": order_id}).get("Item")
    if not item or str(item.get("orderId", "")).startswith("IDEM#"):
        return err("Order not found.", 404)
    return jsonify(_serialize_order(item, include_customer=True)), 200


@app.patch("/api/admin/orders/<order_id>/status")
@require_role("admin")
def admin_update_order_status(order_id: str):
    d = request.get_json(silent=True) or {}
    new_status = (d.get("status") or "").strip().upper()
    if new_status not in VALID_STATUS_TRANSITIONS:
        return err(f"Invalid status '{new_status}'.", 400)

    table = _orders_table()
    item = table.get_item(Key={"orderId": order_id}).get("Item")
    if not item:
        return err("Order not found.", 404)

    current_status = item.get("status", "PENDING")
    if new_status != current_status and new_status not in VALID_STATUS_TRANSITIONS.get(current_status, set()):
        return err(
            f"Invalid status transition from '{current_status}' to '{new_status}'.",
            400,
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    resp = table.update_item(
        Key={"orderId": order_id},
        UpdateExpression="SET #s = :new_s, updatedAt = :now",
        ConditionExpression="#s = :curr_s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":new_s": new_status,
            ":curr_s": current_status,
            ":now": now_iso,
        },
        ReturnValues="ALL_NEW",
    )
    return jsonify(_serialize_order(resp["Attributes"], include_customer=True)), 200


@app.get("/api/admin/stats")
@require_role("admin")
def admin_stats():
    orders_table = _orders_table()
    products_table = _products_table()

    orders_resp = orders_table.query(
        IndexName="EntityCreatedAtIndex",
        KeyConditionExpression=Key("entityType").eq("ORDER"),
    )
    products_resp = products_table.query(
        IndexName="EntityCreatedAtIndex",
        KeyConditionExpression=Key("entityType").eq("PRODUCT"),
    )

    orders = orders_resp.get("Items", [])
    products = products_resp.get("Items", [])

    status_counts = {s: 0 for s in VALID_STATUS_TRANSITIONS}
    revenue = Decimal("0.00")
    for o in orders:
        st = o.get("status", "PENDING")
        status_counts[st] = status_counts.get(st, 0) + 1
        if st != "CANCELLED":
            revenue += Decimal(str(o.get("total", 0)))

    return jsonify(
        totalProducts=len(products),
        totalOrders=len(orders),
        totalRevenue=float(revenue),
        statusBreakdown=status_counts,
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8084)))