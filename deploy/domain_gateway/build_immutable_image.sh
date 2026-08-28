#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

sha256_file() {
  sha256sum "$1" | awk '{ print $1 }'
}

sha256_stdin() {
  sha256sum | awk '{ print $1 }'
}

git_status_hash() {
  git -C "$ROOT" status --porcelain=v1 -z --untracked-files=all | sha256_stdin
}

json_escape() {
  sed 's/\\/\\\\/g; s/"/\\"/g'
}

json_string() {
  printf '%s' "$1" | json_escape
}

docker_label() {
  docker image inspect "$IMAGE_ID" --format "{{ index .Config.Labels \"$1\" }}"
}

assert_label() {
  local key="$1"
  local expected="$2"
  local actual
  actual="$(docker_label "$key")"
  [[ "$actual" == "$expected" ]] || die "image label mismatch for ${key}"
}

assert_source_head_stable() {
  local phase="$1"
  local runtime_head
  runtime_head="$(git -C "$ROOT" rev-parse HEAD)"
  [[ "$runtime_head" == "$SOURCE_HEAD" ]] || die "SOURCE_HEAD drifted ${phase}"
}

cleanup() {
  if [[ -n "${RECEIPT_TMP_DIR:-}" && -n "${RECEIPT_ROOT:-}" && -f "${RECEIPT_TMP_DIR}/.domain_gateway_receipt_tmp.marker" ]]; then
    case "$RECEIPT_TMP_DIR" in
      "$RECEIPT_ROOT"/.domain-gateway-receipt.*) rm -rf -- "$RECEIPT_TMP_DIR" ;;
    esac
  fi

  if [[ -n "${TMP_ROOT:-}" && -f "${TMP_ROOT}/.domain_gateway_build_immutable_image.marker" ]]; then
    case "$TMP_ROOT" in
      /tmp/wuchang-domain-gateway-build.*) rm -rf -- "$TMP_ROOT" ;;
    esac
  fi
}
TMP_ROOT=""
RECEIPT_TMP_DIR=""
RECEIPT_ROOT=""
trap cleanup EXIT

require_command awk
require_command date
require_command docker
require_command find
require_command git
require_command mkdir
require_command mktemp
require_command mv
require_command rm
require_command sed
require_command sha256sum
require_command tar

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
ROOT_PHYSICAL="$(cd "$ROOT" && pwd -P)"
RECEIPT_ROOT_REL="runtime/domain_gateway/build_receipts"
RECEIPT_ROOT="${ROOT}/${RECEIPT_ROOT_REL}"

: "${SOURCE_HEAD:?SOURCE_HEAD is required and must be the full runtime HEAD commit}"
: "${NGINX_BASE_IMAGE:?NGINX_BASE_IMAGE is required and must be a local nginx repo digest}"

[[ "$SOURCE_HEAD" =~ ^[0-9a-f]{40}$ ]] || die "SOURCE_HEAD must be a full 40-character lowercase git commit"
assert_source_head_stable "before build"

case "$NGINX_BASE_IMAGE" in
  nginx@sha256:*|docker.io/library/nginx@sha256:*|registry-1.docker.io/library/nginx@sha256:*) ;;
  *) die "NGINX_BASE_IMAGE must be a nginx@sha256 repo digest" ;;
esac
BASE_DIGEST="${NGINX_BASE_IMAGE##*@sha256:}"
[[ "$BASE_DIGEST" =~ ^[0-9a-f]{64}$ ]] || die "NGINX_BASE_IMAGE digest must be sha256 plus 64 lowercase hex characters"

git -C "$ROOT" cat-file -e "${SOURCE_HEAD}:deploy/domain_gateway/Dockerfile" || die "Dockerfile is missing from SOURCE_HEAD"
git -C "$ROOT" cat-file -e "${SOURCE_HEAD}:deploy/domain_gateway/nginx/default.conf" || die "nginx/default.conf is missing from SOURCE_HEAD"
git -C "$ROOT" cat-file -e "${SOURCE_HEAD}:deploy/domain_gateway/build_immutable_image.sh" || die "build_immutable_image.sh is missing from SOURCE_HEAD"
[[ "$(git -C "$ROOT" cat-file -t "${SOURCE_HEAD}:deploy/domain_gateway/build_immutable_image.sh")" == "blob" ]] || die "build_immutable_image.sh is not a SOURCE_HEAD blob"
git -C "$ROOT" diff --quiet -- deploy/domain_gateway/Dockerfile deploy/domain_gateway/nginx/default.conf deploy/domain_gateway/build_immutable_image.sh || die "release inputs have unstaged diff"
git -C "$ROOT" diff --cached --quiet -- deploy/domain_gateway/Dockerfile deploy/domain_gateway/nginx/default.conf deploy/domain_gateway/build_immutable_image.sh || die "release inputs have staged diff"

STATUS_HASH_BEFORE="$(git_status_hash)"
SOURCE_TREE="$(git -C "$ROOT" rev-parse "${SOURCE_HEAD}^{tree}")"
SOURCE_BUILD_SCRIPT_BLOB="$(git -C "$ROOT" rev-parse "${SOURCE_HEAD}:deploy/domain_gateway/build_immutable_image.sh")"
SOURCE_BUILD_SCRIPT_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:deploy/domain_gateway/build_immutable_image.sh" | sha256_stdin)"
SOURCE_DOCKERFILE_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:deploy/domain_gateway/Dockerfile" | sha256_stdin)"
SOURCE_DEFAULT_CONF_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:deploy/domain_gateway/nginx/default.conf" | sha256_stdin)"

BASE_REPO_DIGESTS="$(docker image inspect "$NGINX_BASE_IMAGE" --format '{{ range .RepoDigests }}{{ println . }}{{ end }}')" || die "base image is not present locally"
BASE_REPO_DIGEST="$(printf '%s\n' "$BASE_REPO_DIGESTS" | awk -v digest="sha256:${BASE_DIGEST}" '($0 ~ "(^|/)nginx@" digest "$") { print; exit }')"
[[ -n "$BASE_REPO_DIGEST" ]] || die "base image is not a locally verifiable nginx repo digest"
BASE_IMAGE_ID="$(docker image inspect "$NGINX_BASE_IMAGE" --format '{{ .Id }}')"
[[ "$BASE_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || die "base image ID is not a sha256 image ID"

TMP_ROOT="$(mktemp -d /tmp/wuchang-domain-gateway-build.XXXXXXXXXX)"
touch "${TMP_ROOT}/.domain_gateway_build_immutable_image.marker"
ARCHIVE_ROOT="${TMP_ROOT}/archive"
mkdir -p "$ARCHIVE_ROOT"

git -C "$ROOT" archive --format=tar "$SOURCE_HEAD" \
  deploy/domain_gateway/Dockerfile \
  deploy/domain_gateway/nginx/default.conf \
  | tar -x -C "$ARCHIVE_ROOT"

BUILD_CONTEXT="${ARCHIVE_ROOT}/deploy/domain_gateway"
[[ -d "$BUILD_CONTEXT" ]] || die "archive did not produce deploy/domain_gateway"

EXTRA_ENTRY="$(cd "$BUILD_CONTEXT" && find . -mindepth 1 ! -type f ! -type d -print -quit)"
[[ -z "$EXTRA_ENTRY" ]] || die "archive contains non-regular entry: ${EXTRA_ENTRY}"

ACTUAL_DIRS="$(cd "$BUILD_CONTEXT" && find . -mindepth 1 -type d -printf '%P\n' | LC_ALL=C sort)"
[[ "$ACTUAL_DIRS" == "nginx" ]] || die "archive directory whitelist mismatch"

ACTUAL_FILES="$(cd "$BUILD_CONTEXT" && find . -type f -printf '%P\n' | LC_ALL=C sort)"
EXPECTED_FILES=$'Dockerfile\nnginx/default.conf'
[[ "$ACTUAL_FILES" == "$EXPECTED_FILES" ]] || die "archive file whitelist mismatch"

RELEASE_DOCKERFILE_SHA256="$(sha256_file "${BUILD_CONTEXT}/Dockerfile")"
RELEASE_DEFAULT_CONF_SHA256="$(sha256_file "${BUILD_CONTEXT}/nginx/default.conf")"
[[ "$RELEASE_DOCKERFILE_SHA256" == "$SOURCE_DOCKERFILE_SHA256" ]] || die "release Dockerfile hash mismatch"
[[ "$RELEASE_DEFAULT_CONF_SHA256" == "$SOURCE_DEFAULT_CONF_SHA256" ]] || die "release default.conf hash mismatch"
RELEASE_MANIFEST_SHA256="$(
  cd "$BUILD_CONTEXT"
  {
    printf '%s  %s\n' "$RELEASE_DOCKERFILE_SHA256" "Dockerfile"
    printf '%s  %s\n' "$RELEASE_DEFAULT_CONF_SHA256" "nginx/default.conf"
    printf '%s  %s  %s\n' "$SOURCE_BUILD_SCRIPT_BLOB" "$SOURCE_BUILD_SCRIPT_SHA256" "deploy/domain_gateway/build_immutable_image.sh"
  } | sha256_stdin
)"

IID_FILE="${TMP_ROOT}/image.iid"
docker build \
  --pull=false \
  --network=none \
  --no-cache \
  --iidfile "$IID_FILE" \
  --build-arg "NGINX_BASE_IMAGE=${NGINX_BASE_IMAGE}" \
  --build-arg "SOURCE_HEAD=${SOURCE_HEAD}" \
  --build-arg "SOURCE_DOCKERFILE_SHA256=${SOURCE_DOCKERFILE_SHA256}" \
  --build-arg "SOURCE_DEFAULT_CONF_SHA256=${SOURCE_DEFAULT_CONF_SHA256}" \
  --build-arg "RELEASE_DEFAULT_CONF_SHA256=${RELEASE_DEFAULT_CONF_SHA256}" \
  "$BUILD_CONTEXT"
assert_source_head_stable "after docker build"

IMAGE_ID="$(cat "$IID_FILE")"
[[ "$IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || die "built image ID is not a sha256 image ID"
INSPECTED_IMAGE_ID="$(docker image inspect "$IMAGE_ID" --format '{{ .Id }}')"
[[ "$INSPECTED_IMAGE_ID" == "$IMAGE_ID" ]] || die "built image ID failed inspect verification"

assert_label "org.opencontainers.image.revision" "$SOURCE_HEAD"
assert_label "org.opencontainers.image.base.name" "$NGINX_BASE_IMAGE"
assert_label "life.wuchang.domain_gateway.source_head" "$SOURCE_HEAD"
assert_label "life.wuchang.domain_gateway.source.dockerfile_sha256" "$SOURCE_DOCKERFILE_SHA256"
assert_label "life.wuchang.domain_gateway.source.default_conf_sha256" "$SOURCE_DEFAULT_CONF_SHA256"
assert_label "life.wuchang.domain_gateway.release.default_conf_sha256" "$RELEASE_DEFAULT_CONF_SHA256"

STATUS_HASH_AFTER_BUILD="$(git_status_hash)"
[[ "$STATUS_HASH_AFTER_BUILD" == "$STATUS_HASH_BEFORE" ]] || die "git status hash changed during build"

git -C "$ROOT" check-ignore -q -- "$RECEIPT_ROOT_REL" || die "receipt root must be ignored by git: ${RECEIPT_ROOT_REL}"
mkdir -p -- "$RECEIPT_ROOT"
RECEIPT_ROOT_PHYSICAL="$(cd "$RECEIPT_ROOT" && pwd -P)"
[[ "$RECEIPT_ROOT_PHYSICAL" == "${ROOT_PHYSICAL}/${RECEIPT_ROOT_REL}" ]] || die "receipt root realpath escaped expected root"

if [[ -n "${RUN_ID:-}" ]]; then
  [[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "RUN_ID may only contain letters, numbers, dot, underscore, and hyphen"
else
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${SOURCE_HEAD:0:12}-${STATUS_HASH_BEFORE:0:12}"
fi

RECEIPT_DIR="${RECEIPT_ROOT}/${RUN_ID}"
[[ ! -e "$RECEIPT_DIR" && ! -L "$RECEIPT_DIR" ]] || die "receipt RUN_ID directory already exists: ${RUN_ID}"
RECEIPT_TMP_DIR="$(mktemp -d "${RECEIPT_ROOT}/.domain-gateway-receipt.${RUN_ID}.XXXXXXXXXX")"
touch "${RECEIPT_TMP_DIR}/.domain_gateway_receipt_tmp.marker"
RECEIPT_FILE="${RECEIPT_TMP_DIR}/receipt.json"
STATUS_HASH_AFTER_RECEIPT_EXPECTED="$STATUS_HASH_AFTER_BUILD"

cat > "$RECEIPT_FILE" <<EOF_RECEIPT
{
  "run_id": "$(json_string "$RUN_ID")",
  "source": {
    "head": "$(json_string "$SOURCE_HEAD")",
    "tree": "$(json_string "$SOURCE_TREE")",
    "git_status_hash_before": "$(json_string "$STATUS_HASH_BEFORE")",
    "git_status_hash_after_build": "$(json_string "$STATUS_HASH_AFTER_BUILD")",
    "git_status_hash_after_receipt": "$(json_string "$STATUS_HASH_AFTER_RECEIPT_EXPECTED")"
  },
  "base": {
    "input": "$(json_string "$NGINX_BASE_IMAGE")",
    "verified_repo_digest": "$(json_string "$BASE_REPO_DIGEST")",
    "digest_sha256": "$(json_string "$BASE_DIGEST")",
    "image_id": "$(json_string "$BASE_IMAGE_ID")"
  },
  "files": {
    "source_build_script_blob": "$(json_string "$SOURCE_BUILD_SCRIPT_BLOB")",
    "source_build_script_sha256": "$(json_string "$SOURCE_BUILD_SCRIPT_SHA256")",
    "source_dockerfile_sha256": "$(json_string "$SOURCE_DOCKERFILE_SHA256")",
    "source_default_conf_sha256": "$(json_string "$SOURCE_DEFAULT_CONF_SHA256")"
  },
  "release": {
    "build_script_blob": "$(json_string "$SOURCE_BUILD_SCRIPT_BLOB")",
    "build_script_sha256": "$(json_string "$SOURCE_BUILD_SCRIPT_SHA256")",
    "dockerfile_sha256": "$(json_string "$RELEASE_DOCKERFILE_SHA256")",
    "default_conf_sha256": "$(json_string "$RELEASE_DEFAULT_CONF_SHA256")",
    "manifest_sha256": "$(json_string "$RELEASE_MANIFEST_SHA256")"
  },
  "image": {
    "id": "$(json_string "$IMAGE_ID")",
    "id_sha256": "$(json_string "${IMAGE_ID#sha256:}")"
  }
}
EOF_RECEIPT

RECEIPT_SHA256="$(sha256_file "$RECEIPT_FILE")"
printf '%s  receipt.json\n' "$RECEIPT_SHA256" > "${RECEIPT_FILE}.sha256"
mv -Tn -- "$RECEIPT_TMP_DIR" "$RECEIPT_DIR"
[[ ! -e "$RECEIPT_TMP_DIR" ]] || die "receipt final directory already exists during publish: ${RUN_ID}"
[[ -f "${RECEIPT_DIR}/receipt.json" && -f "${RECEIPT_DIR}/receipt.json.sha256" ]] || die "receipt publish incomplete"
RECEIPT_TMP_DIR=""
RECEIPT_FILE="${RECEIPT_DIR}/receipt.json"

STATUS_HASH_AFTER_RECEIPT="$(git_status_hash)"
[[ "$STATUS_HASH_AFTER_RECEIPT" == "$STATUS_HASH_BEFORE" ]] || die "git status hash changed after receipt write"
assert_source_head_stable "after receipt"

IMAGE_ID_SHA256="${IMAGE_ID#sha256:}"
[[ "$IMAGE_ID_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "built image ID suffix is not 64 lowercase hex"
printf 'IMAGE_ID=%s\n' "$IMAGE_ID_SHA256"
printf 'WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256=%s\n' "$IMAGE_ID_SHA256"
printf 'RECEIPT=%s\n' "$RECEIPT_FILE"
