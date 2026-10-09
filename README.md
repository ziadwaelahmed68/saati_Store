# SAATI store

frontend/  -> static files for S3 (index.html, style.css, app.js, config.js)
backend/   -> Python (Flask) API with SQLite

## Run the backend
    cd backend && pip install -r requirements.txt && python app.py      # http://localhost:8080
    # or: docker build -t saati-api . && docker run -p 8080:8080 -v saati:/data -e ALLOWED_ORIGINS=https://your-site.com saati-api

## Deploy the frontend to S3
1. Edit frontend/config.js and set window.SAATI_API to your backend URL (HTTPS).
2. aws s3 sync frontend/ s3://YOUR-BUCKET --delete
3. Enable static website hosting (index document: index.html). For HTTPS, put CloudFront in front of the bucket.
4. Set ALLOWED_ORIGINS on the backend to your site's URL so the browser can call the API.

Note: SQLite is fine for a start. For several servers, move to RDS (PostgreSQL).
