import logging
import os
import re
import secrets
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

from shared.aws import get_s3_client
from shared.config import Config
from shared.http import configure_logging, err
from shared.security import require_role

configure_logging("images-service")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=Config.ALLOWED_ORIGINS)


def _build_unique_key(filename: str, content_type: str) -> str:
    ext = Config.ALLOWED_IMAGE_TYPES.get(content_type, ".jpg")
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", os.path.splitext(filename)[0])[:40].strip("-") or "watch"
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m")
    unique = secrets.token_hex(6)
    return f"products/{date_prefix}/{base}-{unique}{ext}"


def _delivery_url(image_key: str) -> str:
    if Config.CLOUDFRONT_DOMAIN:
        return f"https://{Config.CLOUDFRONT_DOMAIN.removeprefix('https://')}/{image_key}"
    if Config.S3_BUCKET_NAME:
        try:
            return get_s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": Config.S3_BUCKET_NAME, "Key": image_key},
                ExpiresIn=Config.PRESIGNED_URL_EXPIRES,
            )
        except Exception:
            return ""
    return ""


@app.get("/api/health")
def health():
    return jsonify(status="ok", service="images"), 200


@app.post("/api/admin/images/upload-url")
@require_role("admin")
def create_upload_url():
    d = request.get_json(silent=True) or {}
    filename = str(d.get("filename") or "watch.jpg").strip()
    content_type = str(d.get("contentType") or "").strip().lower()
    file_size = int(d.get("fileSize") or 0)

    if content_type not in Config.ALLOWED_IMAGE_TYPES:
        return err("Unsupported image type. Allowed: JPEG, PNG, WEBP.", 400)
    if file_size <= 0 or file_size > Config.MAX_IMAGE_BYTES:
        return err(f"Image size must be between 1 byte and {Config.MAX_IMAGE_BYTES // (1024 * 1024)} MB.", 400)
    if not Config.S3_BUCKET_NAME:
        return err("S3_BUCKET_NAME is not configured on the server.", 500)

    image_key = _build_unique_key(filename, content_type)
    s3 = get_s3_client()
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": Config.S3_BUCKET_NAME,
            "Key": image_key,
            "ContentType": content_type,
        },
        ExpiresIn=300,
    )

    return jsonify(
        uploadUrl=upload_url,
        imageKey=image_key,
        imageUrl=_delivery_url(image_key),
    ), 200


@app.post("/api/admin/images/upload")
@require_role("admin")
def direct_upload():
    """Direct multipart upload endpoint for environments where browser-to-S3 CORS isn't configured yet."""
    if "file" not in request.files:
        return err("No image file uploaded.", 400)

    f = request.files["file"]
    content_type = (f.mimetype or "").lower()
    if content_type not in Config.ALLOWED_IMAGE_TYPES:
        return err("Unsupported image type. Allowed: JPEG, PNG, WEBP.", 400)

    raw = f.read(Config.MAX_IMAGE_BYTES + 1)
    if not raw or len(raw) > Config.MAX_IMAGE_BYTES:
        return err(f"Image size must be under {Config.MAX_IMAGE_BYTES // (1024 * 1024)} MB.", 400)

    if not Config.S3_BUCKET_NAME:
        return err("S3_BUCKET_NAME is not configured on the server.", 500)

    image_key = _build_unique_key(f.filename or "watch", content_type)
    get_s3_client().put_object(
        Bucket=Config.S3_BUCKET_NAME,
        Key=image_key,
        Body=raw,
        ContentType=content_type,
    )

    return jsonify(
        imageKey=image_key,
        imageUrl=_delivery_url(image_key),
    ), 201


@app.delete("/api/admin/images/<path:image_key>")
@require_role("admin")
def delete_image(image_key: str):
    clean_key = image_key.lstrip("/")
    if not clean_key.startswith("products/"):
        return err("Invalid image key prefix.", 400)
    if not Config.S3_BUCKET_NAME:
        return err("S3_BUCKET_NAME is not configured on the server.", 500)

    get_s3_client().delete_object(Bucket=Config.S3_BUCKET_NAME, Key=clean_key)
    return jsonify(deleted=True, imageKey=clean_key), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8083)))