ARG NGINX_BASE_IMAGE
FROM ${NGINX_BASE_IMAGE}

ARG NGINX_BASE_IMAGE
ARG SOURCE_HEAD
ARG SOURCE_DOCKERFILE_SHA256
ARG SOURCE_DEFAULT_CONF_SHA256
ARG RELEASE_DEFAULT_CONF_SHA256

LABEL org.opencontainers.image.revision="${SOURCE_HEAD}" \
      org.opencontainers.image.base.name="${NGINX_BASE_IMAGE}" \
      life.wuchang.domain_gateway.source_head="${SOURCE_HEAD}" \
      life.wuchang.domain_gateway.source.dockerfile_sha256="${SOURCE_DOCKERFILE_SHA256}" \
      life.wuchang.domain_gateway.source.default_conf_sha256="${SOURCE_DEFAULT_CONF_SHA256}" \
      life.wuchang.domain_gateway.release.default_conf_sha256="${RELEASE_DEFAULT_CONF_SHA256}"

COPY nginx/default.conf /etc/nginx/conf.d/default.conf

RUN set -eu; \
    nginx_uid="$(awk -F: '$1 == "nginx" { print $3 }' /etc/passwd)"; \
    nginx_gid="$(awk -F: '$1 == "nginx" { print $4 }' /etc/passwd)"; \
    group_gid="$(awk -F: '$1 == "nginx" { print $3 }' /etc/group)"; \
    test "${nginx_uid}" = "101"; \
    test "${nginx_gid}" = "101"; \
    test "${group_gid}" = "101"

USER 101:101
