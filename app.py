import os
import sys

from flask_limiter import Limiter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# ضبط افتراضي للبيئة المحلية في حال عدم تمرير متغيرات بيئة
os.environ.setdefault("INITIAL_ADMIN_EMAIL", "admin@saati.com")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "Admin123!")

from flask import Flask, jsonify
from flask_cors import CORS
from shared.config import Config

from services.auth.app import signup, signin, me, signout
from services.products.app import (
    list_products,
    get_product,
    create_product,
    update_product,
    delete_product,
)
from services.images.app import create_upload_url, direct_upload, delete_image
from services.orders.app import (
    checkout,
    customer_orders,
    admin_list_orders,
    admin_get_order,
    admin_update_order_status,
    admin_stats,
)
from scripts.migrate_dynamodb import (
    ensure_tables,
    seed_initial_products,
    seed_admin_from_env,
)

app = Flask(__name__)
CORS(app, origins=Config.ALLOWED_ORIGINS)

try:
    ensure_tables()
    seed_initial_products()
    seed_admin_from_env()
    print("✅ DynamoDB tables, watches catalog, and admin account are ready!")
except Exception as exc:
    print(f"⚠️ Database auto-init warning: {exc}")


@app.get("/api/health")
@Limiter.exempt
def health():
    return jsonify(status="ok", service="auth"), 200

app.add_url_rule("/api/signup", "signup", signup, methods=["POST"])
app.add_url_rule("/api/signin", "signin", signin, methods=["POST"])
app.add_url_rule("/api/me", "me", me, methods=["GET"])
app.add_url_rule("/api/signout", "signout", signout, methods=["POST"])

app.add_url_rule("/api/products", "list_products", list_products, methods=["GET"])
app.add_url_rule("/api/products/<product_id>", "get_product", get_product, methods=["GET"])
app.add_url_rule("/api/admin/products", "create_product", create_product, methods=["POST"])
app.add_url_rule("/api/admin/products/<product_id>", "update_product", update_product, methods=["PUT"])
app.add_url_rule("/api/admin/products/<product_id>", "delete_product", delete_product, methods=["DELETE"])

app.add_url_rule("/api/admin/images/upload-url", "create_upload_url", create_upload_url, methods=["POST"])
app.add_url_rule("/api/admin/images/upload", "direct_upload", direct_upload, methods=["POST"])
app.add_url_rule("/api/admin/images/<path:image_key>", "delete_image", delete_image, methods=["DELETE"])

app.add_url_rule("/api/checkout", "checkout", checkout, methods=["POST"])
app.add_url_rule("/api/orders", "customer_orders", customer_orders, methods=["GET"])
app.add_url_rule("/api/admin/orders", "admin_list_orders", admin_list_orders, methods=["GET"])
app.add_url_rule("/api/admin/orders/<order_id>", "admin_get_order", admin_get_order, methods=["GET"])
app.add_url_rule(
    "/api/admin/orders/<order_id>/status",
    "admin_update_order_status",
    admin_update_order_status,
    methods=["PATCH"],
)
app.add_url_rule("/api/admin/stats", "admin_stats", admin_stats, methods=["GET"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))