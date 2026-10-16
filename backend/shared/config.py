import os


class Config:
    AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")
    DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL") or None
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL") or None

    PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "saati_products")
    ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "saati_orders")
    USERS_TABLE = os.environ.get("USERS_TABLE", "saati_users")
    IDEMPOTENCY_TABLE = os.environ.get("IDEMPOTENCY_TABLE", "saati_idempotency")

    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "").rstrip("/")
    PRESIGNED_URL_EXPIRES = int(os.environ.get("PRESIGNED_URL_EXPIRES", "900"))

    # Authentication configuration
    AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "dynamodb").lower()  # "cognito" or "dynamodb"
    COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
    COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
    AUTH_SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "")
    TOKEN_TTL = int(os.environ.get("TOKEN_TTL", str(7 * 24 * 3600)))

    ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()
    ]

    FREE_SHIPPING_FROM = float(os.environ.get("FREE_SHIPPING_FROM", "300.0"))
    SHIPPING_FEE = float(os.environ.get("SHIPPING_FEE", "9.99"))
    PROMO_CODE = os.environ.get("PROMO_CODE", "SAATI10").upper()
    PROMO_RATE = float(os.environ.get("PROMO_RATE", "0.10"))

    MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
    ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}