// Resolved configuration without hardcoded secrets.
// When served behind the frontend Nginx container or same-origin reverse proxy,
// empty SAATI_API routes calls to relative `/api/*` endpoints.
window.SAATI_API = window.env?.API_URL || "https://d28bzg8rlab4ye.cloudfront.net";
window.SAATI_IMAGE_BASE = window.env?.IMAGE_BASE || "https://d28bzg8rlab4ye.cloudfront.net";