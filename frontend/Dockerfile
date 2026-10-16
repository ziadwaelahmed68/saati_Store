FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY index.html style.css app.js config.js /usr/share/nginx/html/
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1