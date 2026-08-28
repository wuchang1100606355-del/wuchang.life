ARG NGINX_BASE_IMAGE
FROM ${NGINX_BASE_IMAGE}

COPY public-nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY assets/css/style.css /usr/share/nginx/html/assets/css/style.css
