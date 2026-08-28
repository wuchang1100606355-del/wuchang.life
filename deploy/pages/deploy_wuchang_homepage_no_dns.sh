#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
REPO_ROOT="$(cd -- "$REPO_ROOT_GIT" && pwd -P)"
cd "$REPO_ROOT"
SOURCE_HEAD="$(git rev-parse --verify 'HEAD^{commit}')"
if [[ ! "$SOURCE_HEAD" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'STATUS=HOLD\nREASON=SOURCE_HEAD_NOT_UNIQUE_40_HEX\n' >&2
  exit 10
fi
readonly SOURCE_HEAD

COMPOSE_PROJECT_NAME="wuchang-homepage-public"
SERVICE_NAME="wuchang-homepage-public"
CONTAINER_NAME="wuchang-homepage-public"
COMPOSE_NETWORK_KEY="default"
COMPOSE_NETWORK_NAME="wuchang-homepage-public-internal"
COMPOSE_FILE="deploy/pages/docker-compose.wuchang-homepage.yml"
TOOL_CONTAINER_LABEL_KEY="org.wuchang.homepage.deploy_tool"
TOOL_CONTAINER_LABEL_VALUE="deploy_wuchang_homepage_no_dns.v1"
SITE_TREE_PATH="web/wuchang_homepage"
BUILD_SOURCE_PATH="deploy/pages/wuchang_homepage"
CLOUDFLARE_CONFIG_PATH="cloudflare/config.yml"
RECEIPT_ROOT="runtime/wuchang_homepage/deploy"
RUN_ROOT="$RECEIPT_ROOT/runs"
LOCK_PARENT_REL="$RECEIPT_ROOT/locks"
LOCK_DIR_REL="$LOCK_PARENT_REL/deploy.lock"

RELEASE_CONTROL_FILES=(
  "deploy/pages/deploy_wuchang_homepage_no_dns.sh"
  "$COMPOSE_FILE"
  "$BUILD_SOURCE_PATH/Dockerfile"
  "$BUILD_SOURCE_PATH/public-nginx.conf"
  "$CLOUDFLARE_CONFIG_PATH"
  "docker-compose.domain-gateway.yml"
  "deploy/domain_gateway/nginx/default.conf"
  "$SITE_TREE_PATH/index.html"
  "$SITE_TREE_PATH/assets/css/style.css"
)

BUILD_ALLOWLIST_REPO_PATHS=(
  "$BUILD_SOURCE_PATH/Dockerfile"
  "$BUILD_SOURCE_PATH/public-nginx.conf"
  "$SITE_TREE_PATH/index.html"
  "$SITE_TREE_PATH/assets/css/style.css"
)

BUILD_ALLOWLIST_CONTEXT_PATHS=(
  "Dockerfile"
  "public-nginx.conf"
  "index.html"
  "assets/css/style.css"
)

TEMP_PARENT="$(cd -- "${TMPDIR:-/tmp}" && pwd -P)"
WORK_DIR=""
WORK_DIR_REAL=""
WORK_DIR_MARKER=""
CONTEXT_DIR=""
LOCK_DIR_REAL=""
LOCK_OWNER_PATH=""
LOCK_ACQUIRED=false
RUN_ID=""
RUN_DIR_REAL=""
INITIAL_INDEX_FINGERPRINT=""
INITIAL_RELEASE_STATUS_FINGERPRINT=""
FAIL_REASON="UNHANDLED_EXIT"
FAIL_STATUS="HOLD"
CURRENT_STEP="init"
EFFECT_STARTED=false
BUILD_EFFECT_STARTED=false
COMPOSE_EFFECT_STARTED=false
HOMEPAGE_EFFECT_STARTED_AT_EPOCH=""
SUCCESS_WRITTEN=false
ROLLBACK_ATTEMPTED=false
ROLLBACK_CONTAINER_RESULT="NOT_NEEDED"
ROLLBACK_ASSET_NAME="NOT_SET"
ROLLBACK_ASSET_ID=""
ROLLBACK_ASSET_STATE="NOT_EVALUATED"
ROLLBACK_TAG_RESULT="NOT_NEEDED"
ROLLBACK_NETWORK_RESULT="NOT_NEEDED"
ROLLBACK_COMPLETE="NOT_NEEDED"
ROLLBACK_MISMATCH_FIELDS=""
ROLLBACK_POST_SNAPSHOT_PATH=""
DOMAIN_HOLD_NO_ROLLBACK=false
HOMEPAGE_STATUS="NOT_STARTED"
DOMAIN_BINDING="NOT_EVALUATED"
RUNTIME_RECEIPT_VALIDATION="NOT_EVALUATED"
RUNTIME_RECEIPT_REASON="NOT_EVALUATED"
CLOUDFLARED_RUNTIME_RECEIPT_PATH="${WUCHANG_CLOUDFLARED_RUNTIME_RECEIPT_PATH:-/run/wuchang-cloudflared/runtime-config.env}"
CLOUDFLARED_RUNTIME_RECEIPT_SHA256=""
CURRENT_IMAGE_ID_DISCOVERED_FROM_TAG=false
PRE_CONTAINER_EXISTS=false
PRE_CONTAINER_ID=""
PRE_CONTAINER_IMAGE=""
PRE_CONTAINER_RUNNING=""
PRE_CONTAINER_CONFIG_IMAGE=""
PRE_TARGET_TAG_EXISTS=false
PRE_TARGET_TAG_IMAGE_ID=""
PRE_COMPOSE_NETWORK_EXISTS=false
PRE_COMPOSE_NETWORK_ID=""
PRE_COMPOSE_NETWORK_INTERNAL=""
PRE_COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT=""
PRE_COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK=""
PRE_CONTAINER_TOOL_LABEL=""
PRE_STATE_PATH=""
PRE_STATE_SHA_PATH=""
CLOUDFLARE_CONFIG_BLOB_ID=""
CLOUDFLARE_CONFIG_SHA256=""
SECURITY_CONFIG_USER=""
SECURITY_READONLY_ROOTFS=""
SECURITY_CAP_DROP=""
SECURITY_SECURITY_OPT=""
SECURITY_PRIVILEGED=""
SECURITY_BIND_MOUNTS=""
SECURITY_NETWORK_NAME=""
SECURITY_NETWORK_INTERNAL=""
SECURITY_PORT_BINDING=""
IMAGE_TAG=""
IMAGE_ID=""

CONTAINER_SNAPSHOT_FIELDS=(
  CONTAINER_EXISTS
  CONTAINER_ID
  CONTAINER_IMAGE_ID
  CONTAINER_RUNNING
  CONTAINER_CONFIG_IMAGE
  CONTAINER_CONFIG_USER
  CONTAINER_READONLY_ROOTFS
  CONTAINER_CAP_DROP
  CONTAINER_SECURITY_OPT
  CONTAINER_PRIVILEGED
  CONTAINER_PORT_BINDINGS
  CONTAINER_NETWORK_MODE
  CONTAINER_NETWORK_NAME
  CONTAINER_NETWORK_INTERNAL
  CONTAINER_BINDS_EMPTY
  CONTAINER_RESTART_POLICY
  CONTAINER_PIDS_LIMIT
  CONTAINER_MEMORY
  CONTAINER_NANO_CPUS
  CONTAINER_TMPFS
  CONTAINER_LABEL_COMPOSE_PROJECT
  CONTAINER_LABEL_COMPOSE_SERVICE
  CONTAINER_LABEL_COMPOSE_CONFIG_HASH
  CONTAINER_LABEL_COMPOSE_CONTAINER_NUMBER
  CONTAINER_LABEL_COMPOSE_ONEOFF
  CONTAINER_LABEL_COMPOSE_VERSION
  CONTAINER_LABEL_COMPOSE_IMAGE
  CONTAINER_LABEL_TOOL_OWNER
)

ROLLBACK_CONTAINER_COMPARE_FIELDS=(
  CONTAINER_EXISTS
  CONTAINER_ID
  CONTAINER_IMAGE_ID
  CONTAINER_RUNNING
  CONTAINER_CONFIG_IMAGE
  CONTAINER_CONFIG_USER
  CONTAINER_READONLY_ROOTFS
  CONTAINER_CAP_DROP
  CONTAINER_SECURITY_OPT
  CONTAINER_PRIVILEGED
  CONTAINER_PORT_BINDINGS
  CONTAINER_NETWORK_MODE
  CONTAINER_NETWORK_NAME
  CONTAINER_NETWORK_INTERNAL
  CONTAINER_BINDS_EMPTY
  CONTAINER_RESTART_POLICY
  CONTAINER_PIDS_LIMIT
  CONTAINER_MEMORY
  CONTAINER_NANO_CPUS
  CONTAINER_TMPFS
  CONTAINER_LABEL_COMPOSE_PROJECT
  CONTAINER_LABEL_COMPOSE_SERVICE
  CONTAINER_LABEL_COMPOSE_CONFIG_HASH
  CONTAINER_LABEL_COMPOSE_CONTAINER_NUMBER
  CONTAINER_LABEL_COMPOSE_ONEOFF
  CONTAINER_LABEL_COMPOSE_VERSION
  CONTAINER_LABEL_COMPOSE_IMAGE
  CONTAINER_LABEL_TOOL_OWNER
)

TAG_SNAPSHOT_FIELDS=(
  TARGET_TAG_EXISTS
  TARGET_TAG_IMAGE_ID
)

NETWORK_SNAPSHOT_FIELDS=(
  COMPOSE_NETWORK_NAME
  COMPOSE_NETWORK_EXISTS
  COMPOSE_NETWORK_ID
  COMPOSE_NETWORK_INTERNAL
  COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT
  COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK
)

fail() {
  local code="$1"
  local reason="$2"
  FAIL_REASON="$reason"
  printf 'STATUS=%s\nREASON=%s\n' "$FAIL_STATUS" "$reason" >&2
  exit "$code"
}

cleanup_temp() {
  if [[ -n "${WORK_DIR_REAL:-}" && -n "${WORK_DIR_MARKER:-}" && -d "$WORK_DIR_REAL" && -f "$WORK_DIR_MARKER" ]]; then
    case "$WORK_DIR_REAL" in
      "$TEMP_PARENT"/wuchang_homepage_deploy.*)
        rm -rf -- "$WORK_DIR_REAL"
        ;;
      *)
        printf 'STATUS=HOLD\nREASON=TEMP_CLEANUP_PATH_NOT_VERIFIED\nTEMP_PATH=%s\n' "$WORK_DIR_REAL" >&2
        ;;
    esac
  fi
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail 20 "MISSING_LOCAL_COMMAND_$command_name"
}

is_nginx_digest_ref() {
  local ref="$1"
  [[ "$ref" =~ (^|/)nginx@sha256:[0-9a-f]{64}$ ]]
}

require_safe_relative_path() {
  local rel="$1"
  local part
  local -a parts

  [[ -n "$rel" && "$rel" != /* ]] || fail 11 "UNSAFE_REPO_REL_PATH"
  IFS='/' read -r -a parts <<<"$rel"
  for part in "${parts[@]}"; do
    [[ -n "$part" && "$part" != "." && "$part" != ".." ]] || fail 11 "UNSAFE_REPO_REL_PATH"
  done
}

assert_abs_path_in_repo() {
  local abs_path="$1"

  case "$abs_path" in
    "$REPO_ROOT"/*)
      ;;
    *)
      fail 12 "REPO_PATH_ESCAPE"
      ;;
  esac
}

assert_no_symlink_ancestors() {
  local rel="$1"
  local current="$REPO_ROOT"
  local part
  local -a parts

  require_safe_relative_path "$rel"
  IFS='/' read -r -a parts <<<"$rel"
  for part in "${parts[@]}"; do
    current="$current/$part"
    [[ ! -L "$current" ]] || fail 13 "REPO_PATH_SYMLINK_ESCAPE"
  done
}

ensure_repo_dir() {
  local rel="$1"
  local abs_path
  local real_path

  assert_no_symlink_ancestors "$rel"
  abs_path="$REPO_ROOT/$rel"
  mkdir -p -- "$abs_path" || fail 14 "REPO_DIR_CREATE_FAILED"
  real_path="$(cd -- "$abs_path" && pwd -P)" || fail 15 "REPO_DIR_REALPATH_FAILED"
  assert_abs_path_in_repo "$real_path"
  [[ "$real_path" == "$abs_path" ]] || fail 16 "REPO_DIR_CANONICAL_DRIFT"
  printf '%s\n' "$real_path"
}

create_repo_run_dir() {
  local rel="$1"
  local abs_path
  local real_path

  ensure_repo_dir "$RUN_ROOT" >/dev/null
  assert_no_symlink_ancestors "$rel"
  abs_path="$REPO_ROOT/$rel"
  [[ ! -e "$abs_path" && ! -L "$abs_path" ]] || fail 17 "RUN_DIR_EXISTS"
  mkdir -- "$abs_path" || fail 18 "RUN_DIR_CREATE_FAILED"
  real_path="$(cd -- "$abs_path" && pwd -P)" || fail 19 "RUN_DIR_REALPATH_FAILED"
  assert_abs_path_in_repo "$real_path"
  [[ "$real_path" == "$abs_path" ]] || fail 19 "RUN_DIR_CANONICAL_DRIFT"
  printf '%s\n' "$real_path"
}

compute_index_fingerprint() {
  git ls-files --stage -z | sha256sum | awk '{ print $1 }'
}

release_whitelist_status() {
  git status --porcelain=v1 --untracked-files=all -- "${RELEASE_CONTROL_FILES[@]}"
}

compute_release_status_fingerprint() {
  git status --porcelain=v1 -z --untracked-files=all -- "${RELEASE_CONTROL_FILES[@]}" | sha256sum | awk '{ print $1 }'
}

require_source_file() {
  local path="$1"
  git cat-file -e "$SOURCE_HEAD:$path" 2>/dev/null || fail 30 "SOURCE_FILE_MISSING_$path"
}

require_release_whitelist_clean() {
  local status_output

  status_output="$(release_whitelist_status)"
  [[ -z "$status_output" ]] || fail 31 "RELEASE_CONTROL_WORKTREE_NOT_CLEAN"
}

require_release_control_clean() {
  local path

  for path in "${RELEASE_CONTROL_FILES[@]}"; do
    require_source_file "$path"
  done

  require_release_whitelist_clean
}

require_source_state_unchanged() {
  local phase="$1"
  local current_head
  local current_index_fingerprint
  local current_release_status_fingerprint

  current_head="$(git rev-parse --verify 'HEAD^{commit}')"
  [[ "$current_head" == "$SOURCE_HEAD" ]] || fail 32 "SOURCE_HEAD_DRIFT_BEFORE_$phase"

  current_index_fingerprint="$(compute_index_fingerprint)"
  [[ "$current_index_fingerprint" == "$INITIAL_INDEX_FINGERPRINT" ]] || fail 33 "INDEX_FINGERPRINT_DRIFT_BEFORE_$phase"

  require_release_whitelist_clean
  current_release_status_fingerprint="$(compute_release_status_fingerprint)"
  [[ "$current_release_status_fingerprint" == "$INITIAL_RELEASE_STATUS_FINGERPRINT" ]] || fail 34 "RELEASE_STATUS_FINGERPRINT_DRIFT_BEFORE_$phase"
}

require_exact_source_site_tree() {
  local actual_paths
  local expected_paths
  local symlink_paths
  local tree_type

  tree_type="$(git cat-file -t "$SOURCE_HEAD:$SITE_TREE_PATH" 2>/dev/null)" || fail 35 "SOURCE_SITE_TREE_MISSING"
  [[ "$tree_type" == "tree" ]] || fail 35 "SOURCE_SITE_TREE_NOT_TREE"

  expected_paths=$'assets/css/style.css\nindex.html'
  actual_paths="$(git ls-tree -r --name-only "$SOURCE_HEAD:$SITE_TREE_PATH")"
  [[ "$actual_paths" == "$expected_paths" ]] || fail 36 "SOURCE_SITE_TREE_NOT_EXACT_ALLOWLIST"

  symlink_paths="$(git ls-tree -r "$SOURCE_HEAD:$SITE_TREE_PATH" | awk '$1 == "120000" { print $4 }')"
  [[ -z "$symlink_paths" ]] || fail 37 "SOURCE_SITE_TREE_CONTAINS_SYMLINK"
}

create_verified_context() {
  local actual_entries
  local expected_entries

  WORK_DIR="$(mktemp -d "$TEMP_PARENT/wuchang_homepage_deploy.XXXXXXXXXX")"
  WORK_DIR_REAL="$(cd -- "$WORK_DIR" && pwd -P)"
  WORK_DIR_MARKER="$WORK_DIR_REAL/.wuchang_homepage_deploy_tmp"
  CONTEXT_DIR="$WORK_DIR_REAL/context"
  : > "$WORK_DIR_MARKER"
  mkdir -p "$CONTEXT_DIR"

  git archive --format=tar "$SOURCE_HEAD:$BUILD_SOURCE_PATH" Dockerfile public-nginx.conf | tar -x -C "$CONTEXT_DIR"
  git archive --format=tar "$SOURCE_HEAD:$SITE_TREE_PATH" index.html assets/css/style.css | tar -x -C "$CONTEXT_DIR"

  if find "$CONTEXT_DIR" -type l -print -quit | grep -q .; then
    fail 34 "ARCHIVED_CONTEXT_CONTAINS_SYMLINK"
  fi

  expected_entries=$'./Dockerfile\n./assets/css/style.css\n./index.html\n./public-nginx.conf'
  actual_entries="$(cd "$CONTEXT_DIR" && find . -mindepth 1 ! -type d -print | sort)"
  [[ "$actual_entries" == "$expected_entries" ]] || fail 35 "ARCHIVED_CONTEXT_NOT_EXACT_ALLOWLIST"
}

select_fixed_local_nginx_base() {
  local requested="${NGINX_BASE_IMAGE:-}"
  local requested_digest
  local digest_lines
  local selected_digest
  local selected_ref
  local unique_digest_count

  if [[ -n "$requested" ]]; then
    is_nginx_digest_ref "$requested" || fail 40 "NGINX_BASE_IMAGE_NOT_FIXED_NGINX_DIGEST"
    docker image inspect "$requested" >/dev/null 2>&1 || fail 41 "NGINX_BASE_IMAGE_NOT_LOCAL"
    requested_digest="${requested##*@}"
    digest_lines="$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "$requested" | grep -E '(^|/)nginx@sha256:[0-9a-f]{64}$' || true)"
    grep -E "(^|/)nginx@$requested_digest$" <<<"$digest_lines" >/dev/null || fail 42 "NGINX_BASE_IMAGE_REPODIGEST_NOT_VERIFIED"
    printf '%s\n' "$requested"
    return 0
  fi

  docker image inspect nginx:alpine >/dev/null 2>&1 || fail 43 "LOCAL_NGINX_ALPINE_NOT_FOUND"
  digest_lines="$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' nginx:alpine | grep -E '(^|/)nginx@sha256:[0-9a-f]{64}$' || true)"
  [[ -n "$digest_lines" ]] || fail 44 "LOCAL_NGINX_ALPINE_HAS_NO_FIXED_REPODIGEST"

  unique_digest_count="$(awk -F '@' '{ print $2 }' <<<"$digest_lines" | sort -u | wc -l | awk '{ print $1 }')"
  [[ "$unique_digest_count" == "1" ]] || fail 45 "LOCAL_NGINX_ALPINE_REPODIGEST_AMBIGUOUS"

  selected_digest="$(awk -F '@' 'NR == 1 { print $2 }' <<<"$digest_lines")"
  selected_ref="$(grep -E "(^|/)nginx@$selected_digest$" <<<"$digest_lines" | sort | head -n 1)"
  is_nginx_digest_ref "$selected_ref" || fail 46 "LOCAL_NGINX_ALPINE_REPODIGEST_INVALID"
  printf '%s\n' "$selected_ref"
}

source_file_sha256() {
  local path

  path="$1"
  git cat-file -p "$SOURCE_HEAD:$path" | sha256sum | awk '{ print $1 }'
}

release_control_manifest() {
  local path
  local blob_id

  for path in "${RELEASE_CONTROL_FILES[@]}"; do
    blob_id="$(git rev-parse "$SOURCE_HEAD:$path")"
    printf '%s\t%s\n' "$path" "$blob_id"
  done
}

compute_release_sha() {
  release_control_manifest | sha256sum | awk '{ print $1 }'
}

verify_cloudflare_config() {
  local actual_non_empty
  local expected_non_empty

  expected_non_empty=$'tunnel: wuchang-smart-cloud\ncredentials-file: /home/taiji_admin/.cloudflared/wuchang-smart-cloud.json\ningress:\n  - hostname: wuchang.life\n    service: http://127.0.0.1:8089\n  - hostname: www.wuchang.life\n    service: http://127.0.0.1:8089\n  - service: http_status:404'
  actual_non_empty="$(git cat-file -p "$SOURCE_HEAD:$CLOUDFLARE_CONFIG_PATH" | sed '/^[[:space:]]*$/d')"
  [[ "$actual_non_empty" == "$expected_non_empty" ]] || fail 38 "CLOUDFLARE_CONFIG_SOURCE_ROUTES_NOT_EXACT"
}

context_file_hashes() {
  local context_path

  for context_path in "${BUILD_ALLOWLIST_CONTEXT_PATHS[@]}"; do
    printf '%s  %s\n' "$(sha256sum "$CONTEXT_DIR/$context_path" | awk '{ print $1 }')" "$context_path"
  done
}

verify_image_label() {
  local image="$1"
  local label_key="$2"
  local expected="$3"
  local actual

  actual="$(docker image inspect --format "{{ index .Config.Labels \"$label_key\" }}" "$image")"
  [[ "$actual" == "$expected" ]] || fail 50 "IMAGE_LABEL_MISMATCH_$label_key"
}

require_image_tag_not_conflicting() {
  local image="$1"
  local site_tree_sha="$2"
  local release_sha="$3"
  local existing_site_tree_sha
  local existing_release_sha

  if ! docker image inspect "$image" >/dev/null 2>&1; then
    return 0
  fi

  existing_site_tree_sha="$(docker image inspect --format '{{ index .Config.Labels "org.wuchang.homepage.site_tree_sha" }}' "$image")"
  existing_release_sha="$(docker image inspect --format '{{ index .Config.Labels "org.wuchang.homepage.release_sha" }}' "$image")"
  [[ "$existing_site_tree_sha" == "$site_tree_sha" && "$existing_release_sha" == "$release_sha" ]] || fail 51 "IMAGE_TAG_COLLISION"
}

wait_for_healthy() {
  local deadline
  local health

  deadline=$(( $(date +%s) + 60 ))
  while true; do
    health="$(docker container inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    case "$health" in
      healthy)
        printf '%s\n' "$health"
        return 0
        ;;
      unhealthy)
        fail 60 "CONTAINER_UNHEALTHY"
        ;;
    esac

    if (( $(date +%s) >= deadline )); then
      fail 61 "CONTAINER_HEALTH_TIMEOUT"
    fi
    sleep 2
  done
}

verify_port_binding() {
  local binding
  local keys

  keys="$(docker container inspect --format '{{range $key, $_ := .HostConfig.PortBindings}}{{printf "%s\n" $key}}{{end}}' "$CONTAINER_NAME" | sort)"
  [[ "$keys" == "8089/tcp" ]] || fail 62 "CONTAINER_PORT_KEYS_NOT_EXACT"

  binding="$(docker container inspect --format '{{with index .HostConfig.PortBindings "8089/tcp"}}{{if eq (len .) 1}}{{with index . 0}}{{.HostIp}}:{{.HostPort}}{{end}}{{end}}{{end}}' "$CONTAINER_NAME")"
  [[ "$binding" == "127.0.0.1:8089" ]] || fail 63 "CONTAINER_PORT_BINDING_NOT_EXACT"
  SECURITY_PORT_BINDING="$binding"
  printf '%s\n' "$binding"
}

verify_container_image_id() {
  local expected_image_id="$1"
  local actual_image_id

  actual_image_id="$(docker container inspect --format '{{.Image}}' "$CONTAINER_NAME")"
  [[ "$actual_image_id" == "$expected_image_id" ]] || fail 64 "CONTAINER_IMAGE_ID_NOT_EXACT"
}

verify_container_security() {
  local host_binds
  local bind_mounts
  local network_count
  local network_names

  SECURITY_CONFIG_USER="$(docker container inspect --format '{{.Config.User}}' "$CONTAINER_NAME")"
  [[ "$SECURITY_CONFIG_USER" == "101:101" ]] || fail 65 "CONTAINER_USER_NOT_EXACT"

  SECURITY_READONLY_ROOTFS="$(docker container inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$CONTAINER_NAME")"
  [[ "$SECURITY_READONLY_ROOTFS" == "true" ]] || fail 66 "CONTAINER_ROOTFS_NOT_READONLY"

  SECURITY_CAP_DROP="$(docker container inspect --format '{{range .HostConfig.CapDrop}}{{println .}}{{end}}' "$CONTAINER_NAME" | sort)"
  [[ "$SECURITY_CAP_DROP" == "ALL" ]] || fail 67 "CONTAINER_CAP_DROP_NOT_EXACT"

  SECURITY_SECURITY_OPT="$(docker container inspect --format '{{range .HostConfig.SecurityOpt}}{{println .}}{{end}}' "$CONTAINER_NAME" | sort)"
  [[ "$SECURITY_SECURITY_OPT" == "no-new-privileges:true" ]] || fail 68 "CONTAINER_SECURITY_OPT_NOT_EXACT"

  SECURITY_PRIVILEGED="$(docker container inspect --format '{{.HostConfig.Privileged}}' "$CONTAINER_NAME")"
  [[ "$SECURITY_PRIVILEGED" == "false" ]] || fail 69 "CONTAINER_PRIVILEGED"

  host_binds="$(docker container inspect --format '{{range .HostConfig.Binds}}{{println .}}{{end}}' "$CONTAINER_NAME")"
  bind_mounts="$(docker container inspect --format '{{range .Mounts}}{{if eq .Type "bind"}}{{println .Source}}{{end}}{{end}}' "$CONTAINER_NAME")"
  SECURITY_BIND_MOUNTS="${host_binds}${bind_mounts}"
  [[ -z "$host_binds" && -z "$bind_mounts" ]] || fail 70 "CONTAINER_HAS_BIND_MOUNT"

  network_names="$(docker container inspect --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}' "$CONTAINER_NAME" | sort)"
  network_count="$(printf '%s\n' "$network_names" | sed '/^$/d' | wc -l | awk '{ print $1 }')"
  [[ "$network_count" == "1" ]] || fail 71 "CONTAINER_NETWORK_NOT_SINGLE"
  SECURITY_NETWORK_NAME="$network_names"
  [[ "$SECURITY_NETWORK_NAME" == "$COMPOSE_NETWORK_NAME" ]] || fail 72 "CONTAINER_NETWORK_NAME_NOT_DETERMINISTIC"
  SECURITY_NETWORK_INTERNAL="$(docker network inspect --format '{{.Internal}}' "$SECURITY_NETWORK_NAME")"
  [[ "$SECURITY_NETWORK_INTERNAL" == "true" ]] || fail 73 "CONTAINER_NETWORK_NOT_INTERNAL"
}

read_verified_container_started_epoch() {
  local started_at
  local started_epoch
  local now_epoch

  started_at="$(docker container inspect --format '{{.State.StartedAt}}' "$CONTAINER_NAME")" || fail 74 "CONTAINER_STARTED_AT_READ_FAILED"
  [[ -n "$started_at" && "$started_at" != "0001-01-01T00:00:00Z" ]] || fail 74 "CONTAINER_STARTED_AT_EMPTY"
  started_epoch="$(date -u -d "$started_at" +%s)" || fail 74 "CONTAINER_STARTED_AT_EPOCH_CONVERT_FAILED"
  [[ "$started_epoch" =~ ^[1-9][0-9]*$ ]] || fail 74 "CONTAINER_STARTED_AT_EPOCH_NOT_POSITIVE"
  now_epoch="$(date -u +%s)" || fail 74 "NOW_EPOCH_READ_FAILED"
  [[ "$now_epoch" =~ ^[1-9][0-9]*$ ]] || fail 74 "NOW_EPOCH_NOT_POSITIVE"
  (( 10#$started_epoch <= 10#$now_epoch )) || fail 74 "CONTAINER_STARTED_AT_EPOCH_IN_FUTURE"
  printf '%s\n' "$started_epoch"
}

runtime_receipt_fail() {
  RUNTIME_RECEIPT_VALIDATION="FAIL"
  RUNTIME_RECEIPT_REASON="$1"
  return 1
}

is_cloudflared_runtime_receipt_key_allowed() {
  case "$1" in
    STATE | SOURCE_HEAD | CLOUDFLARE_CONFIG_PATH | CLOUDFLARE_CONFIG_BLOB_ID | CLOUDFLARE_CONFIG_SHA256 | CLOUDFLARED_PID | CLOUDFLARED_PROC_START_TICKS | CLOUDFLARED_PROC_EXE_SHA256 | CONFIG_VALIDATION | RUNTIME_RELOAD | APPLIED_AT_EPOCH | DNS_WRITE | MX_TXT_WRITE)
      return 0
      ;;
  esac
  return 1
}

require_safe_root_owned_runtime_file() {
  local path="$1"
  local label="$2"
  local owner_uid
  local mode_hex

  if [[ -z "$path" || "$path" != /* || "$path" == *$'\n'* ]]; then
    runtime_receipt_fail "${label}_PATH_NOT_ABSOLUTE_SAFE"
    return 1
  fi
  if [[ ! -e "$path" ]]; then
    runtime_receipt_fail "${label}_MISSING"
    return 1
  fi
  if [[ -L "$path" ]]; then
    runtime_receipt_fail "${label}_SYMLINK"
    return 1
  fi
  if [[ ! -f "$path" ]]; then
    runtime_receipt_fail "${label}_NOT_REGULAR_FILE"
    return 1
  fi
  if ! owner_uid="$(stat -c '%u' "$path" 2>/dev/null)"; then
    runtime_receipt_fail "${label}_STAT_OWNER_FAILED"
    return 1
  fi
  if [[ "$owner_uid" != "0" ]]; then
    runtime_receipt_fail "${label}_NOT_ROOT_OWNED"
    return 1
  fi
  if ! mode_hex="$(stat -c '%f' "$path" 2>/dev/null)"; then
    runtime_receipt_fail "${label}_STAT_MODE_FAILED"
    return 1
  fi
  if (( (16#$mode_hex & 0x12) != 0 )); then
    runtime_receipt_fail "${label}_GROUP_OR_OTHER_WRITABLE"
    return 1
  fi
}

read_proc_start_ticks() {
  local pid="$1"
  local proc_stat_line
  local proc_stat_after_comm

  proc_stat_line="$(<"/proc/$pid/stat")" || return 1
  proc_stat_after_comm="${proc_stat_line##*) }"
  set -- $proc_stat_after_comm
  printf '%s\n' "${20:-}"
}

verify_cloudflared_runtime_receipt() {
  local receipt_path="$CLOUDFLARED_RUNTIME_RECEIPT_PATH"
  local sidecar_path="${receipt_path}.sha256"
  local receipt_sha
  local receipt_sha_after
  local sidecar_hash
  local sidecar_line_count
  local line
  local key
  local value
  local line_count=0
  local expected_key
  local now_epoch
  local pid
  local proc_comm
  local proc_start_ticks
  local proc_start_ticks_after_hash
  local proc_exe_sha
  local -A receipt=()
  local -A seen=()
  local -a expected_keys=(
    STATE
    SOURCE_HEAD
    CLOUDFLARE_CONFIG_PATH
    CLOUDFLARE_CONFIG_BLOB_ID
    CLOUDFLARE_CONFIG_SHA256
    CLOUDFLARED_PID
    CLOUDFLARED_PROC_START_TICKS
    CLOUDFLARED_PROC_EXE_SHA256
    CONFIG_VALIDATION
    RUNTIME_RELOAD
    APPLIED_AT_EPOCH
    DNS_WRITE
    MX_TXT_WRITE
  )

  RUNTIME_RECEIPT_VALIDATION="FAIL"
  RUNTIME_RECEIPT_REASON="UNKNOWN"
  require_safe_root_owned_runtime_file "$receipt_path" "RUNTIME_RECEIPT" || return 1
  require_safe_root_owned_runtime_file "$sidecar_path" "RUNTIME_RECEIPT_SHA256" || return 1

  if ! receipt_sha="$(sha256sum "$receipt_path" 2>/dev/null | awk '{ print $1 }')"; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_COMPUTE_FAILED"
    return 1
  fi
  if [[ ! "$receipt_sha" =~ ^[0-9a-f]{64}$ ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_INVALID"
    return 1
  fi
  if ! sidecar_line_count="$(awk 'END { print NR }' "$sidecar_path")"; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_READ_FAILED"
    return 1
  fi
  if ! sidecar_hash="$(awk 'NR == 1 { print $1 }' "$sidecar_path")"; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_READ_FAILED"
    return 1
  fi
  if [[ "$sidecar_line_count" != "1" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_LINE_COUNT_NOT_EXACT"
    return 1
  fi
  if [[ "$sidecar_hash" != "$receipt_sha" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SHA256_MISMATCH"
    return 1
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line_count=$((line_count + 1))
    if [[ ! "$line" =~ ^[A-Z0-9_]+=.*$ ]]; then
      runtime_receipt_fail "RUNTIME_RECEIPT_LINE_NOT_KEY_VALUE"
      return 1
    fi
    key="${line%%=*}"
    value="${line#*=}"
    if ! is_cloudflared_runtime_receipt_key_allowed "$key"; then
      runtime_receipt_fail "RUNTIME_RECEIPT_UNKNOWN_KEY"
      return 1
    fi
    if [[ -n "${seen[$key]+x}" ]]; then
      runtime_receipt_fail "RUNTIME_RECEIPT_DUPLICATE_KEY"
      return 1
    fi
    seen[$key]=1
    receipt[$key]="$value"
  done < "$receipt_path"

  for expected_key in "${expected_keys[@]}"; do
    if [[ -z "${seen[$expected_key]+x}" ]]; then
      runtime_receipt_fail "RUNTIME_RECEIPT_MISSING_KEY"
      return 1
    fi
  done
  if [[ "$line_count" != "${#expected_keys[@]}" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_KEY_COUNT_NOT_EXACT"
    return 1
  fi

  if [[ "${receipt[STATE]}" != "PASS_CLOUDFLARED_RUNTIME_CONFIG_APPLIED" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_STATE_NOT_PASS"
    return 1
  fi
  if [[ "${receipt[SOURCE_HEAD]}" != "$SOURCE_HEAD" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_SOURCE_HEAD_MISMATCH"
    return 1
  fi
  if [[ "${receipt[CLOUDFLARE_CONFIG_PATH]}" != "$CLOUDFLARE_CONFIG_PATH" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_CONFIG_PATH_MISMATCH"
    return 1
  fi
  if [[ "${receipt[CLOUDFLARE_CONFIG_BLOB_ID]}" != "$CLOUDFLARE_CONFIG_BLOB_ID" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_CONFIG_BLOB_MISMATCH"
    return 1
  fi
  if [[ "${receipt[CLOUDFLARE_CONFIG_SHA256]}" != "$CLOUDFLARE_CONFIG_SHA256" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_CONFIG_SHA256_MISMATCH"
    return 1
  fi
  if [[ "${receipt[CONFIG_VALIDATION]}" != "PASS" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_CONFIG_VALIDATION_NOT_PASS"
    return 1
  fi
  if [[ "${receipt[RUNTIME_RELOAD]}" != "PASS" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_RELOAD_NOT_PASS"
    return 1
  fi
  if [[ "${receipt[DNS_WRITE]}" != "false" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_DNS_WRITE_NOT_FALSE"
    return 1
  fi
  if [[ "${receipt[MX_TXT_WRITE]}" != "false" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_MX_TXT_WRITE_NOT_FALSE"
    return 1
  fi
  if [[ -z "$HOMEPAGE_EFFECT_STARTED_AT_EPOCH" || ! "$HOMEPAGE_EFFECT_STARTED_AT_EPOCH" =~ ^[1-9][0-9]*$ ]]; then
    runtime_receipt_fail "HOMEPAGE_EFFECT_START_EPOCH_MISSING"
    return 1
  fi
  if [[ ! "${receipt[APPLIED_AT_EPOCH]}" =~ ^[1-9][0-9]*$ ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_APPLIED_AT_INVALID"
    return 1
  fi
  now_epoch="$(date -u +%s)"
  if [[ ! "$now_epoch" =~ ^[1-9][0-9]*$ ]]; then
    runtime_receipt_fail "NOW_EPOCH_INVALID"
    return 1
  fi
  if (( 10#${receipt[APPLIED_AT_EPOCH]} < 10#$HOMEPAGE_EFFECT_STARTED_AT_EPOCH || 10#${receipt[APPLIED_AT_EPOCH]} > 10#$now_epoch )); then
    runtime_receipt_fail "RUNTIME_RECEIPT_APPLIED_AT_OUT_OF_WINDOW"
    return 1
  fi

  pid="${receipt[CLOUDFLARED_PID]}"
  if [[ ! "$pid" =~ ^[1-9][0-9]*$ ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_PID_INVALID"
    return 1
  fi
  if [[ ! -d "/proc/$pid" ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_NOT_LIVE"
    return 1
  fi
  if ! IFS= read -r proc_comm < "/proc/$pid/comm"; then
    runtime_receipt_fail "CLOUDFLARED_PROC_COMM_READ_FAILED"
    return 1
  fi
  if [[ "$proc_comm" != "cloudflared" ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_COMM_MISMATCH"
    return 1
  fi
  if ! proc_start_ticks="$(read_proc_start_ticks "$pid")"; then
    runtime_receipt_fail "CLOUDFLARED_PROC_STAT_READ_FAILED"
    return 1
  fi
  if [[ ! "$proc_start_ticks" =~ ^[0-9]+$ ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_START_TICKS_INVALID"
    return 1
  fi
  if [[ "$proc_start_ticks" != "${receipt[CLOUDFLARED_PROC_START_TICKS]}" ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_START_TICKS_MISMATCH"
    return 1
  fi
  if ! proc_exe_sha="$(sha256sum "/proc/$pid/exe" 2>/dev/null | awk '{ print $1 }')"; then
    runtime_receipt_fail "CLOUDFLARED_PROC_EXE_SHA256_READ_FAILED"
    return 1
  fi
  if [[ "$proc_exe_sha" != "${receipt[CLOUDFLARED_PROC_EXE_SHA256]}" ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_EXE_SHA256_MISMATCH"
    return 1
  fi
  if ! proc_start_ticks_after_hash="$(read_proc_start_ticks "$pid")"; then
    runtime_receipt_fail "CLOUDFLARED_PROC_STAT_REREAD_FAILED"
    return 1
  fi
  if [[ "$proc_start_ticks_after_hash" != "$proc_start_ticks" ]]; then
    runtime_receipt_fail "CLOUDFLARED_PROC_CHANGED_DURING_VALIDATION"
    return 1
  fi
  if ! receipt_sha_after="$(sha256sum "$receipt_path" 2>/dev/null | awk '{ print $1 }')"; then
    runtime_receipt_fail "RUNTIME_RECEIPT_FINAL_SHA256_COMPUTE_FAILED"
    return 1
  fi
  if [[ "$receipt_sha_after" != "$receipt_sha" ]]; then
    runtime_receipt_fail "RUNTIME_RECEIPT_CHANGED_DURING_VALIDATION"
    return 1
  fi

  CLOUDFLARED_RUNTIME_RECEIPT_SHA256="$receipt_sha"
  RUNTIME_RECEIPT_VALIDATION="PASS"
  RUNTIME_RECEIPT_REASON="PASS"
  DOMAIN_BINDING="PASS"
  return 0
}

domain_hold() {
  local reason="$1"

  FAIL_STATUS="HOLD_DOMAIN_INGRESS_NOT_APPLIED"
  FAIL_REASON="$reason"
  HOMEPAGE_STATUS="PASS"
  DOMAIN_BINDING="HOLD"
  RUNTIME_RECEIPT_VALIDATION="FAIL"
  RUNTIME_RECEIPT_REASON="$reason"

  printf 'STATUS=HOLD_DOMAIN_INGRESS_NOT_APPLIED\n'
  printf 'HOMEPAGE=PASS\n'
  printf 'DOMAIN_BINDING=HOLD\n'
  printf 'DNS_WRITE=false\n'
  printf 'MX_TXT_WRITE=false\n'
  printf 'RUNTIME_RECEIPT_REASON=%s\n' "$reason"
  exit 90
}

write_release_control_receipt_entries() {
  local index=0
  local path
  local blob_id

  while IFS=$'\t' read -r path blob_id; do
    index=$((index + 1))
    printf 'RELEASE_CONTROL_%02d_PATH=%s\n' "$index" "$path"
    printf 'RELEASE_CONTROL_%02d_BLOB=%s\n' "$index" "$blob_id"
  done < <(release_control_manifest)
}

join_sorted_lines() {
  sed '/^$/d' | sort | awk 'BEGIN { first=1 } { printf "%s%s", first ? "" : ",", $0; first=0 } END { printf "\n" }'
}

docker_container_label_json() {
  local key="$1"
  local value

  value="$(docker container inspect --format "{{ json (index .Config.Labels \"$key\") }}" "$CONTAINER_NAME")"
  [[ -n "$value" ]] || value="null"
  printf '%s\n' "$value"
}

docker_named_container_label_value() {
  local container_name="$1"
  local key="$2"
  local value

  value="$(docker container inspect --format "{{ index .Config.Labels \"$key\" }}" "$container_name" 2>/dev/null || true)"
  [[ "$value" == "<no value>" ]] && value=""
  printf '%s\n' "$value"
}

docker_network_label_json() {
  local key="$1"
  local value

  value="$(docker network inspect --format "{{ json (index .Labels \"$key\") }}" "$COMPOSE_NETWORK_NAME")"
  [[ -n "$value" ]] || value="null"
  printf '%s\n' "$value"
}

docker_network_label_value() {
  local key="$1"
  local value

  value="$(docker network inspect --format "{{ index .Labels \"$key\" }}" "$COMPOSE_NETWORK_NAME" 2>/dev/null || true)"
  [[ "$value" == "<no value>" ]] && value=""
  printf '%s\n' "$value"
}

snapshot_get_value() {
  local path="$1"
  local key="$2"

  awk -F= -v key="$key" '
    BEGIN { found=0 }
    $1 == key {
      print substr($0, length(key) + 2)
      found=1
      exit
    }
    END {
      if (found == 0) {
        exit 1
      }
    }
  ' "$path"
}

print_empty_container_snapshot() {
  local field

  for field in "${CONTAINER_SNAPSHOT_FIELDS[@]}"; do
    if [[ "$field" == "CONTAINER_EXISTS" ]]; then
      printf '%s=false\n' "$field"
    else
      printf '%s=\n' "$field"
    fi
  done
}

snapshot_state_stream() {
  local cap_drop
  local security_opt
  local port_bindings
  local network_names
  local network_internal
  local network_internal_value
  local network_name
  local binds_count
  local binds_empty
  local tmpfs

  if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    cap_drop="$(docker container inspect --format '{{range .HostConfig.CapDrop}}{{println .}}{{end}}' "$CONTAINER_NAME" | join_sorted_lines)"
    security_opt="$(docker container inspect --format '{{range .HostConfig.SecurityOpt}}{{println .}}{{end}}' "$CONTAINER_NAME" | join_sorted_lines)"
    port_bindings="$(docker container inspect --format '{{range $key, $bindings := .HostConfig.PortBindings}}{{range $binding := $bindings}}{{printf "%s=%s:%s\n" $key $binding.HostIp $binding.HostPort}}{{end}}{{end}}' "$CONTAINER_NAME" | join_sorted_lines)"
    network_names="$(docker container inspect --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}' "$CONTAINER_NAME" | join_sorted_lines)"
    network_internal="$(
      while IFS= read -r network_name; do
        [[ -n "$network_name" ]] || continue
        network_internal_value="$(docker network inspect --format '{{.Internal}}' "$network_name" 2>/dev/null || printf 'NETWORK_INSPECT_FAILED')"
        printf '%s=%s\n' "$network_name" "$network_internal_value"
      done < <(printf '%s\n' "$network_names" | sed 's/,/\n/g') | join_sorted_lines
    )"
    binds_count="$(docker container inspect --format '{{len .HostConfig.Binds}}' "$CONTAINER_NAME")"
    binds_empty=false
    [[ "$binds_count" == "0" ]] && binds_empty=true
    tmpfs="$(docker container inspect --format '{{range $key, $value := .HostConfig.Tmpfs}}{{printf "%s=%s\n" $key $value}}{{end}}' "$CONTAINER_NAME" | join_sorted_lines)"

    printf 'CONTAINER_EXISTS=true\n'
    printf 'CONTAINER_ID=%s\n' "$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_IMAGE_ID=%s\n' "$(docker container inspect --format '{{.Image}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_RUNNING=%s\n' "$(docker container inspect --format '{{.State.Running}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_CONFIG_IMAGE=%s\n' "$(docker container inspect --format '{{.Config.Image}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_CONFIG_USER=%s\n' "$(docker container inspect --format '{{.Config.User}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_READONLY_ROOTFS=%s\n' "$(docker container inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_CAP_DROP=%s\n' "$cap_drop"
    printf 'CONTAINER_SECURITY_OPT=%s\n' "$security_opt"
    printf 'CONTAINER_PRIVILEGED=%s\n' "$(docker container inspect --format '{{.HostConfig.Privileged}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_PORT_BINDINGS=%s\n' "$port_bindings"
    printf 'CONTAINER_NETWORK_MODE=%s\n' "$(docker container inspect --format '{{.HostConfig.NetworkMode}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_NETWORK_NAME=%s\n' "$network_names"
    printf 'CONTAINER_NETWORK_INTERNAL=%s\n' "$network_internal"
    printf 'CONTAINER_BINDS_EMPTY=%s\n' "$binds_empty"
    printf 'CONTAINER_RESTART_POLICY=%s\n' "$(docker container inspect --format '{{.HostConfig.RestartPolicy.Name}}:{{.HostConfig.RestartPolicy.MaximumRetryCount}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_PIDS_LIMIT=%s\n' "$(docker container inspect --format '{{.HostConfig.PidsLimit}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_MEMORY=%s\n' "$(docker container inspect --format '{{.HostConfig.Memory}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_NANO_CPUS=%s\n' "$(docker container inspect --format '{{.HostConfig.NanoCpus}}' "$CONTAINER_NAME")"
    printf 'CONTAINER_TMPFS=%s\n' "$tmpfs"
    printf 'CONTAINER_LABEL_COMPOSE_PROJECT=%s\n' "$(docker_container_label_json 'com.docker.compose.project')"
    printf 'CONTAINER_LABEL_COMPOSE_SERVICE=%s\n' "$(docker_container_label_json 'com.docker.compose.service')"
    printf 'CONTAINER_LABEL_COMPOSE_CONFIG_HASH=%s\n' "$(docker_container_label_json 'com.docker.compose.config-hash')"
    printf 'CONTAINER_LABEL_COMPOSE_CONTAINER_NUMBER=%s\n' "$(docker_container_label_json 'com.docker.compose.container-number')"
    printf 'CONTAINER_LABEL_COMPOSE_ONEOFF=%s\n' "$(docker_container_label_json 'com.docker.compose.oneoff')"
    printf 'CONTAINER_LABEL_COMPOSE_VERSION=%s\n' "$(docker_container_label_json 'com.docker.compose.version')"
    printf 'CONTAINER_LABEL_COMPOSE_IMAGE=%s\n' "$(docker_container_label_json 'com.docker.compose.image')"
    printf 'CONTAINER_LABEL_TOOL_OWNER=%s\n' "$(docker_container_label_json "$TOOL_CONTAINER_LABEL_KEY")"
  else
    print_empty_container_snapshot
  fi

  if [[ -n "${IMAGE_TAG:-}" ]] && docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    printf 'TARGET_TAG_EXISTS=true\n'
    printf 'TARGET_TAG_IMAGE_ID=%s\n' "$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG")"
  else
    printf 'TARGET_TAG_EXISTS=false\n'
    printf 'TARGET_TAG_IMAGE_ID=\n'
  fi

  printf 'COMPOSE_NETWORK_NAME=%s\n' "$COMPOSE_NETWORK_NAME"
  if docker network inspect "$COMPOSE_NETWORK_NAME" >/dev/null 2>&1; then
    printf 'COMPOSE_NETWORK_EXISTS=true\n'
    printf 'COMPOSE_NETWORK_ID=%s\n' "$(docker network inspect --format '{{.Id}}' "$COMPOSE_NETWORK_NAME")"
    printf 'COMPOSE_NETWORK_INTERNAL=%s\n' "$(docker network inspect --format '{{.Internal}}' "$COMPOSE_NETWORK_NAME")"
    printf 'COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT=%s\n' "$(docker_network_label_json 'com.docker.compose.project')"
    printf 'COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK=%s\n' "$(docker_network_label_json 'com.docker.compose.network')"
  else
    printf 'COMPOSE_NETWORK_EXISTS=false\n'
    printf 'COMPOSE_NETWORK_ID=\n'
    printf 'COMPOSE_NETWORK_INTERNAL=\n'
    printf 'COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT=\n'
    printf 'COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK=\n'
  fi
}

write_sanitized_snapshot_file() {
  local snapshot_path="$1"
  local snapshot_sha_path="${snapshot_path}.sha256"
  local snapshot_dir="${snapshot_path%/*}"
  local snapshot_name="${snapshot_path##*/}"
  local snapshot_tmp="$snapshot_dir/.$snapshot_name.$$"
  local snapshot_sha_tmp="$snapshot_dir/.$snapshot_name.sha256.$$"
  local snapshot_sha

  [[ -n "${RUN_DIR_REAL:-}" && -d "$RUN_DIR_REAL" ]] || return 1
  case "$snapshot_path" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$snapshot_tmp" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$snapshot_sha_path" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$snapshot_sha_tmp" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  [[ ! -e "$snapshot_path" && ! -L "$snapshot_path" && ! -e "$snapshot_tmp" && ! -L "$snapshot_tmp" && ! -e "$snapshot_sha_path" && ! -L "$snapshot_sha_path" && ! -e "$snapshot_sha_tmp" && ! -L "$snapshot_sha_tmp" ]] || return 1

  {
    printf 'SNAPSHOT_SCHEMA=wuchang_homepage_sanitized_inspect_v4\n'
    printf 'RUN_ID=%s\n' "$RUN_ID"
    printf 'SOURCE_HEAD=%s\n' "$SOURCE_HEAD"
    printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG"
    snapshot_state_stream
  } > "$snapshot_tmp" || return 1
  mv -- "$snapshot_tmp" "$snapshot_path" || return 1

  snapshot_sha="$(sha256sum "$snapshot_path" | awk '{ print $1 }')" || return 1
  printf '%s  %s\n' "$snapshot_sha" "$snapshot_name" > "$snapshot_sha_tmp" || return 1
  mv -- "$snapshot_sha_tmp" "$snapshot_sha_path" || return 1
}

write_pre_state_entries() {
  local field
  local value
  local pre_state_sha=""

  printf 'PRE_SANITIZED_INSPECT=%s\n' "$PRE_STATE_PATH"
  if [[ -n "$PRE_STATE_SHA_PATH" && -f "$PRE_STATE_SHA_PATH" ]]; then
    pre_state_sha="$(awk 'NR == 1 { print $1 }' "$PRE_STATE_SHA_PATH")"
  fi
  printf 'PRE_SANITIZED_INSPECT_SHA256=%s\n' "$pre_state_sha"

  if [[ -n "$PRE_STATE_PATH" && -f "$PRE_STATE_PATH" ]]; then
    for field in "${CONTAINER_SNAPSHOT_FIELDS[@]}" "${TAG_SNAPSHOT_FIELDS[@]}" "${NETWORK_SNAPSHOT_FIELDS[@]}"; do
      value="$(snapshot_get_value "$PRE_STATE_PATH" "$field" 2>/dev/null || true)"
      printf 'PRE_%s=%s\n' "$field" "$value"
    done
  else
    printf 'PRE_CONTAINER_EXISTS=%s\n' "$PRE_CONTAINER_EXISTS"
    printf 'PRE_CONTAINER_ID=%s\n' "$PRE_CONTAINER_ID"
    printf 'PRE_CONTAINER_IMAGE_ID=%s\n' "$PRE_CONTAINER_IMAGE"
    printf 'PRE_CONTAINER_RUNNING=%s\n' "$PRE_CONTAINER_RUNNING"
    printf 'PRE_CONTAINER_CONFIG_IMAGE=%s\n' "$PRE_CONTAINER_CONFIG_IMAGE"
    printf 'PRE_TARGET_TAG_EXISTS=%s\n' "$PRE_TARGET_TAG_EXISTS"
    printf 'PRE_TARGET_TAG_IMAGE_ID=%s\n' "$PRE_TARGET_TAG_IMAGE_ID"
    printf 'PRE_COMPOSE_NETWORK_EXISTS=%s\n' "$PRE_COMPOSE_NETWORK_EXISTS"
    printf 'PRE_COMPOSE_NETWORK_ID=%s\n' "$PRE_COMPOSE_NETWORK_ID"
    printf 'PRE_COMPOSE_NETWORK_INTERNAL=%s\n' "$PRE_COMPOSE_NETWORK_INTERNAL"
    printf 'PRE_COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT=%s\n' "$PRE_COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT"
    printf 'PRE_COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK=%s\n' "$PRE_COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK"
  fi
}

capture_pre_state() {
  [[ -n "$RUN_DIR_REAL" && -d "$RUN_DIR_REAL" ]] || fail 73 "RUN_DIR_NOT_READY"
  PRE_STATE_PATH="$RUN_DIR_REAL/sanitized_inspect.env"
  PRE_STATE_SHA_PATH="$RUN_DIR_REAL/sanitized_inspect.env.sha256"
  write_sanitized_snapshot_file "$PRE_STATE_PATH" || fail 74 "PRE_STATE_WRITE_FAILED"

  PRE_CONTAINER_EXISTS="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_EXISTS)"
  PRE_CONTAINER_ID="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_ID)"
  PRE_CONTAINER_IMAGE="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_IMAGE_ID)"
  PRE_CONTAINER_RUNNING="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_RUNNING)"
  PRE_CONTAINER_CONFIG_IMAGE="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_CONFIG_IMAGE)"
  PRE_CONTAINER_TOOL_LABEL="$(snapshot_get_value "$PRE_STATE_PATH" CONTAINER_LABEL_TOOL_OWNER)"
  PRE_TARGET_TAG_EXISTS="$(snapshot_get_value "$PRE_STATE_PATH" TARGET_TAG_EXISTS)"
  PRE_TARGET_TAG_IMAGE_ID="$(snapshot_get_value "$PRE_STATE_PATH" TARGET_TAG_IMAGE_ID)"
  PRE_COMPOSE_NETWORK_EXISTS="$(snapshot_get_value "$PRE_STATE_PATH" COMPOSE_NETWORK_EXISTS)"
  PRE_COMPOSE_NETWORK_ID="$(snapshot_get_value "$PRE_STATE_PATH" COMPOSE_NETWORK_ID)"
  PRE_COMPOSE_NETWORK_INTERNAL="$(snapshot_get_value "$PRE_STATE_PATH" COMPOSE_NETWORK_INTERNAL)"
  PRE_COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT="$(snapshot_get_value "$PRE_STATE_PATH" COMPOSE_NETWORK_LABEL_COMPOSE_PROJECT)"
  PRE_COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK="$(snapshot_get_value "$PRE_STATE_PATH" COMPOSE_NETWORK_LABEL_COMPOSE_NETWORK)"
}

preflight_existing_container_for_exact_rollback() {
  local current_id
  local current_tool_label

  [[ -n "$ROLLBACK_ASSET_NAME" && "$ROLLBACK_ASSET_NAME" != "NOT_SET" ]] || fail 82 "ROLLBACK_ASSET_NAME_NOT_SET"
  if docker container inspect "$ROLLBACK_ASSET_NAME" >/dev/null 2>&1; then
    fail 83 "ROLLBACK_ASSET_NAME_ALREADY_EXISTS"
  fi

  if [[ "$PRE_CONTAINER_EXISTS" != true ]]; then
    ROLLBACK_ASSET_NAME="NO_PRE_CONTAINER"
    ROLLBACK_ASSET_ID="NO_PRE_CONTAINER"
    ROLLBACK_ASSET_STATE="NO_PRE_CONTAINER"
    ROLLBACK_CONTAINER_RESULT="NO_PRE_CONTAINER"
    return 0
  fi

  current_id="$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  [[ "$current_id" == "$PRE_CONTAINER_ID" ]] || fail 84 "PRE_CONTAINER_ID_NOT_STILL_EXACT"
  current_tool_label="$(docker_named_container_label_value "$CONTAINER_NAME" "$TOOL_CONTAINER_LABEL_KEY")"
  [[ "$current_tool_label" == "$TOOL_CONTAINER_LABEL_VALUE" && "$PRE_CONTAINER_TOOL_LABEL" == "\"$TOOL_CONTAINER_LABEL_VALUE\"" ]] || fail 85 "PRE_CONTAINER_TOOL_LABEL_NOT_EXACT"
}

verify_current_container_tool_label() {
  local current_tool_label

  current_tool_label="$(docker_named_container_label_value "$CONTAINER_NAME" "$TOOL_CONTAINER_LABEL_KEY")"
  [[ "$current_tool_label" == "$TOOL_CONTAINER_LABEL_VALUE" ]] || fail 86 "CONTAINER_TOOL_LABEL_NOT_EXACT"
}

record_rollback_asset_state() {
  local rollback_running

  if [[ "$ROLLBACK_ASSET_NAME" == "NO_PRE_CONTAINER" ]]; then
    ROLLBACK_ASSET_ID="NO_PRE_CONTAINER"
    ROLLBACK_ASSET_STATE="NO_PRE_CONTAINER"
    return 0
  fi
  if docker container inspect "$ROLLBACK_ASSET_NAME" >/dev/null 2>&1; then
    ROLLBACK_ASSET_ID="$(docker container inspect --format '{{.Id}}' "$ROLLBACK_ASSET_NAME" 2>/dev/null || true)"
    [[ "$ROLLBACK_ASSET_ID" == "$PRE_CONTAINER_ID" ]] || fail 90 "ROLLBACK_ASSET_ID_DRIFT"
    rollback_running="$(docker container inspect --format '{{.State.Running}}' "$ROLLBACK_ASSET_NAME" 2>/dev/null || true)"
    [[ "$rollback_running" == "false" ]] || fail 90 "ROLLBACK_ASSET_NOT_STOPPED_AT_SEAL"
    ROLLBACK_ASSET_STATE="PRESERVED_STOPPED"
  else
    ROLLBACK_ASSET_ID=""
    fail 90 "ROLLBACK_ASSET_NOT_PRESENT_AT_SEAL"
  fi
}

preserve_pre_container_for_rollback() {
  local current_id
  local renamed_id
  local running
  local rc

  if [[ "$PRE_CONTAINER_EXISTS" != true ]]; then
    ROLLBACK_ASSET_NAME="NO_PRE_CONTAINER"
    ROLLBACK_ASSET_ID="NO_PRE_CONTAINER"
    ROLLBACK_ASSET_STATE="NO_PRE_CONTAINER"
    ROLLBACK_CONTAINER_RESULT="NO_PRE_CONTAINER"
    return 0
  fi

  current_id="$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  [[ "$current_id" == "$PRE_CONTAINER_ID" ]] || fail 87 "PRE_CONTAINER_ID_DRIFT_BEFORE_PRESERVE"
  [[ "$(docker_named_container_label_value "$CONTAINER_NAME" "$TOOL_CONTAINER_LABEL_KEY")" == "$TOOL_CONTAINER_LABEL_VALUE" ]] || fail 88 "PRE_CONTAINER_TOOL_LABEL_DRIFT_BEFORE_PRESERVE"
  if docker container inspect "$ROLLBACK_ASSET_NAME" >/dev/null 2>&1; then
    fail 89 "ROLLBACK_ASSET_NAME_EXISTS_BEFORE_PRESERVE"
  fi

  running="$(docker container inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  [[ "$running" == "$PRE_CONTAINER_RUNNING" ]] || fail 89 "PRE_CONTAINER_RUNNING_DRIFT_BEFORE_PRESERVE"
  if [[ "$PRE_CONTAINER_RUNNING" == "true" ]]; then
    docker container stop "$CONTAINER_NAME" >/dev/null
    rc=$?
    [[ "$rc" -eq 0 ]] || fail 89 "PRE_CONTAINER_STOP_FOR_ROLLBACK_FAILED_RC_$rc"
  fi

  docker container rename "$CONTAINER_NAME" "$ROLLBACK_ASSET_NAME" >/dev/null
  rc=$?
  [[ "$rc" -eq 0 ]] || fail 89 "PRE_CONTAINER_RENAME_TO_ROLLBACK_FAILED_RC_$rc"

  renamed_id="$(docker container inspect --format '{{.Id}}' "$ROLLBACK_ASSET_NAME" 2>/dev/null || true)"
  [[ "$renamed_id" == "$PRE_CONTAINER_ID" ]] || fail 89 "ROLLBACK_ASSET_ID_NOT_PRE_CONTAINER"
  [[ "$(docker container inspect --format '{{.State.Running}}' "$ROLLBACK_ASSET_NAME" 2>/dev/null || true)" == "false" ]] || fail 89 "ROLLBACK_ASSET_NOT_STOPPED"
  ROLLBACK_ASSET_ID="$renamed_id"
  ROLLBACK_ASSET_STATE="PRESERVED_STOPPED"
  ROLLBACK_CONTAINER_RESULT="OLD_CONTAINER_PRESERVED_STOPPED"
}

acquire_deploy_lock() {
  local lock_abs

  ensure_repo_dir "$LOCK_PARENT_REL" >/dev/null
  assert_no_symlink_ancestors "$LOCK_DIR_REL"
  lock_abs="$REPO_ROOT/$LOCK_DIR_REL"
  if ! mkdir -- "$lock_abs"; then
    fail 75 "DEPLOY_LOCK_HELD"
  fi

  LOCK_ACQUIRED=true
  LOCK_DIR_REAL="$(cd -- "$lock_abs" && pwd -P)" || fail 76 "LOCK_DIR_REALPATH_FAILED"
  assert_abs_path_in_repo "$LOCK_DIR_REAL"
  [[ "$LOCK_DIR_REAL" == "$lock_abs" ]] || fail 77 "LOCK_DIR_CANONICAL_DRIFT"
  LOCK_OWNER_PATH="$LOCK_DIR_REAL/owner.env"
  assert_abs_path_in_repo "$LOCK_OWNER_PATH"
}

write_lock_owner() {
  [[ "$LOCK_ACQUIRED" == true && -n "$LOCK_OWNER_PATH" ]] || fail 78 "LOCK_NOT_READY"
  [[ ! -e "$LOCK_OWNER_PATH" && ! -L "$LOCK_OWNER_PATH" ]] || fail 79 "LOCK_OWNER_PATH_NOT_CLEAN"
  {
    printf 'SOURCE_HEAD=%s\n' "$SOURCE_HEAD"
    printf 'REPO_ROOT=%s\n' "$REPO_ROOT"
    printf 'PID=%s\n' "$$"
    printf 'INITIAL_INDEX_FINGERPRINT=%s\n' "$INITIAL_INDEX_FINGERPRINT"
    printf 'INITIAL_RELEASE_STATUS_FINGERPRINT=%s\n' "$INITIAL_RELEASE_STATUS_FINGERPRINT"
  } > "$LOCK_OWNER_PATH"
}

release_deploy_lock() {
  if [[ "$LOCK_ACQUIRED" == true && -n "${LOCK_DIR_REAL:-}" ]]; then
    if [[ -n "${LOCK_OWNER_PATH:-}" && "$LOCK_OWNER_PATH" == "$LOCK_DIR_REAL/owner.env" ]]; then
      rm -- "$LOCK_OWNER_PATH" 2>/dev/null
      rmdir -- "$LOCK_DIR_REAL" 2>/dev/null
    else
      printf 'STATUS=HOLD\nREASON=LOCK_OWNER_PATH_NOT_EXACT\n' >&2
    fi
  fi
}

image_tag_matches_current_release() {
  local revision
  local site_tree_label
  local release_label

  [[ -n "${IMAGE_TAG:-}" && -n "${SITE_TREE_SHA:-}" && -n "${RELEASE_SHA:-}" ]] || return 1
  docker image inspect "$IMAGE_TAG" >/dev/null 2>&1 || return 1
  revision="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$IMAGE_TAG" 2>/dev/null || true)"
  site_tree_label="$(docker image inspect --format '{{ index .Config.Labels "org.wuchang.homepage.site_tree_sha" }}' "$IMAGE_TAG" 2>/dev/null || true)"
  release_label="$(docker image inspect --format '{{ index .Config.Labels "org.wuchang.homepage.release_sha" }}' "$IMAGE_TAG" 2>/dev/null || true)"
  [[ "$revision" == "$SOURCE_HEAD" && "$site_tree_label" == "$SITE_TREE_SHA" && "$release_label" == "$RELEASE_SHA" ]]
}

resolve_current_image_id_for_rollback() {
  local discovered_image_id

  if [[ "${IMAGE_ID:-}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    return 0
  fi

  if image_tag_matches_current_release; then
    discovered_image_id="$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG" 2>/dev/null || true)"
    if [[ "$discovered_image_id" =~ ^sha256:[0-9a-f]{64}$ ]]; then
      IMAGE_ID="$discovered_image_id"
      CURRENT_IMAGE_ID_DISCOVERED_FROM_TAG=true
      return 0
    fi
  fi

  return 1
}

remove_current_container_if_new_image() {
  local current_image_id
  local current_service_name
  local current_tool_label
  local rc

  resolve_current_image_id_for_rollback || true
  current_image_id="$(docker container inspect --format '{{.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  current_service_name="$(docker container inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$CONTAINER_NAME" 2>/dev/null || true)"
  current_tool_label="$(docker_named_container_label_value "$CONTAINER_NAME" "$TOOL_CONTAINER_LABEL_KEY")"
  if [[ -n "${IMAGE_ID:-}" && "$current_image_id" == "$IMAGE_ID" && "$current_service_name" == "$SERVICE_NAME" && "$current_tool_label" == "$TOOL_CONTAINER_LABEL_VALUE" ]]; then
    docker container rm -f "$CONTAINER_NAME" >/dev/null 2>&1
    rc=$?
    if [[ "$rc" -eq 0 ]]; then
      ROLLBACK_CONTAINER_RESULT="CURRENT_CONTAINER_REMOVED"
      return 0
    fi
    ROLLBACK_CONTAINER_RESULT="CURRENT_CONTAINER_REMOVE_FAILED_RC_$rc"
    return "$rc"
  fi

  ROLLBACK_CONTAINER_RESULT="CURRENT_CONTAINER_CONFLICT_NOT_REMOVED"
  return 1
}

current_compose_network_is_safe_to_remove() {
  local current_network_internal
  local current_project_label
  local current_network_label

  docker network inspect "$COMPOSE_NETWORK_NAME" >/dev/null 2>&1 || return 1
  current_network_internal="$(docker network inspect --format '{{.Internal}}' "$COMPOSE_NETWORK_NAME" 2>/dev/null || true)"
  current_project_label="$(docker_network_label_value 'com.docker.compose.project')"
  current_network_label="$(docker_network_label_value 'com.docker.compose.network')"

  [[ "$current_project_label" == "$COMPOSE_PROJECT_NAME" && "$current_network_label" == "$COMPOSE_NETWORK_KEY" && "$current_network_internal" == "true" ]]
}

rollback_compose_network_if_new() {
  local rc

  if [[ "$PRE_COMPOSE_NETWORK_EXISTS" == true ]]; then
    ROLLBACK_NETWORK_RESULT="PRE_NETWORK_EXISTED_NOT_MODIFIED"
    return 0
  fi

  if ! docker network inspect "$COMPOSE_NETWORK_NAME" >/dev/null 2>&1; then
    ROLLBACK_NETWORK_RESULT="NO_PRE_NETWORK_AND_NO_CURRENT_NETWORK"
    return 0
  fi

  if current_compose_network_is_safe_to_remove; then
    docker network rm "$COMPOSE_NETWORK_NAME" >/dev/null 2>&1
    rc=$?
    if [[ "$rc" -eq 0 ]]; then
      ROLLBACK_NETWORK_RESULT="CURRENT_NETWORK_REMOVED"
      return 0
    fi
    ROLLBACK_NETWORK_RESULT="CURRENT_NETWORK_REMOVE_FAILED_RC_$rc"
    return "$rc"
  fi

  ROLLBACK_NETWORK_RESULT="CURRENT_NETWORK_CONFLICT_NOT_REMOVED"
  return 1
}

attempt_rollback() {
  local current_container_id=""
  local restored_running
  local rc

  ROLLBACK_ATTEMPTED=true

  if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    current_container_id="$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME" 2>/dev/null)"
  fi

  if [[ "$PRE_CONTAINER_EXISTS" == true ]]; then
    if [[ -n "$current_container_id" && "$current_container_id" == "$PRE_CONTAINER_ID" ]]; then
      ROLLBACK_CONTAINER_RESULT="OLD_CONTAINER_STILL_PRESENT"
      if [[ "$PRE_CONTAINER_RUNNING" == "true" ]]; then
        if [[ "$(docker container inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)" != "true" ]]; then
          docker container start "$CONTAINER_NAME" >/dev/null 2>&1
          rc=$?
          if [[ "$rc" -eq 0 ]]; then
            ROLLBACK_CONTAINER_RESULT="OLD_CONTAINER_STARTED_TO_PRE_STATE"
          else
            ROLLBACK_CONTAINER_RESULT="HOLD_OLD_CONTAINER_START_FAILED_RC_$rc"
          fi
        fi
      else
        docker container stop "$CONTAINER_NAME" >/dev/null 2>&1
        rc=$?
        if [[ "$rc" -eq 0 ]]; then
          ROLLBACK_CONTAINER_RESULT="OLD_CONTAINER_STOPPED_TO_PRE_STATE"
        else
          ROLLBACK_CONTAINER_RESULT="HOLD_OLD_CONTAINER_STOP_FAILED_RC_$rc"
        fi
      fi
      restored_running="$(docker container inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)"
      [[ "$restored_running" == "$PRE_CONTAINER_RUNNING" ]] || ROLLBACK_CONTAINER_RESULT="HOLD_OLD_CONTAINER_STATE_NOT_RESTORED"
      ROLLBACK_ASSET_ID="$PRE_CONTAINER_ID"
      ROLLBACK_ASSET_STATE="ORIGINAL_NAME_$restored_running"
    else
      if [[ -n "$current_container_id" ]]; then
        remove_current_container_if_new_image || true
      fi

      if docker container inspect "$ROLLBACK_ASSET_NAME" >/dev/null 2>&1; then
        if [[ "$(docker container inspect --format '{{.Id}}' "$ROLLBACK_ASSET_NAME" 2>/dev/null || true)" != "$PRE_CONTAINER_ID" ]]; then
          ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_ID_NOT_PRE_CONTAINER"
        elif docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
          ROLLBACK_CONTAINER_RESULT="HOLD_CURRENT_CONTAINER_BLOCKS_RESTORE"
        else
          docker container rename "$ROLLBACK_ASSET_NAME" "$CONTAINER_NAME" >/dev/null 2>&1
          rc=$?
          if [[ "$rc" -eq 0 ]]; then
            if [[ "$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME" 2>/dev/null || true)" == "$PRE_CONTAINER_ID" ]]; then
              if [[ "$PRE_CONTAINER_RUNNING" == "true" ]]; then
                docker container start "$CONTAINER_NAME" >/dev/null 2>&1
                rc=$?
                if [[ "$rc" -eq 0 ]]; then
                  ROLLBACK_CONTAINER_RESULT="ROLLBACK_ASSET_RESTORED_AND_STARTED"
                else
                  ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_START_FAILED_RC_$rc"
                fi
              else
                ROLLBACK_CONTAINER_RESULT="ROLLBACK_ASSET_RESTORED_STOPPED"
              fi
              restored_running="$(docker container inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)"
              [[ "$restored_running" == "$PRE_CONTAINER_RUNNING" ]] || ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_STATE_NOT_RESTORED"
              ROLLBACK_ASSET_ID="$PRE_CONTAINER_ID"
              ROLLBACK_ASSET_STATE="RESTORED_TO_ORIGINAL_NAME_$restored_running"
            else
              ROLLBACK_CONTAINER_RESULT="HOLD_RESTORED_CONTAINER_ID_MISMATCH"
            fi
          else
            ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_RENAME_BACK_FAILED_RC_$rc"
          fi
        fi
      elif [[ "$ROLLBACK_CONTAINER_RESULT" == "CURRENT_CONTAINER_REMOVED" ]]; then
        ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_MISSING_AFTER_NEW_REMOVAL"
      else
        ROLLBACK_CONTAINER_RESULT="HOLD_ROLLBACK_ASSET_MISSING"
      fi
    fi
  elif [[ -n "$current_container_id" ]]; then
    remove_current_container_if_new_image || true
  else
    ROLLBACK_CONTAINER_RESULT="NO_PRE_CONTAINER_AND_NO_CURRENT_CONTAINER"
  fi

  if [[ "$PRE_CONTAINER_EXISTS" == true && "$ROLLBACK_ASSET_STATE" == "PRESERVED_STOPPED" ]]; then
    record_rollback_asset_state
  fi

  if [[ -n "${IMAGE_TAG:-}" ]]; then
    if [[ "$PRE_TARGET_TAG_EXISTS" == true && -n "$PRE_TARGET_TAG_IMAGE_ID" ]]; then
      docker image tag "$PRE_TARGET_TAG_IMAGE_ID" "$IMAGE_TAG" >/dev/null 2>&1
      rc=$?
      if [[ "$rc" -eq 0 ]]; then
        ROLLBACK_TAG_RESULT="OLD_TAG_RESTORED"
      else
        ROLLBACK_TAG_RESULT="OLD_TAG_RESTORE_FAILED_RC_$rc"
      fi
    elif docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
      resolve_current_image_id_for_rollback || true
      if [[ -n "${IMAGE_ID:-}" && "$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG" 2>/dev/null || true)" == "$IMAGE_ID" ]]; then
        docker image rm "$IMAGE_TAG" >/dev/null 2>&1
        rc=$?
        if [[ "$rc" -eq 0 ]]; then
          ROLLBACK_TAG_RESULT="CURRENT_TAG_REMOVED"
        else
          ROLLBACK_TAG_RESULT="CURRENT_TAG_REMOVE_FAILED_RC_$rc"
        fi
      else
        ROLLBACK_TAG_RESULT="CURRENT_TAG_CONFLICT_NOT_REMOVED"
      fi
    else
      ROLLBACK_TAG_RESULT="NO_PRE_TAG_AND_NO_CURRENT_TAG"
    fi
  fi

  rollback_compose_network_if_new || true
}

verify_rollback_state() {
  local post_snapshot_path
  local field
  local pre_value
  local post_value
  local -a mismatches=()

  ROLLBACK_COMPLETE=false
  [[ -n "${RUN_DIR_REAL:-}" && -d "$RUN_DIR_REAL" ]] || {
    ROLLBACK_MISMATCH_FIELDS="ROLLBACK_RUN_DIR_MISSING"
    FAIL_STATUS="HOLD_ROLLBACK_INCOMPLETE"
    return 1
  }
  [[ -n "$PRE_STATE_PATH" && -f "$PRE_STATE_PATH" ]] || {
    ROLLBACK_MISMATCH_FIELDS="PRE_SANITIZED_INSPECT_MISSING"
    FAIL_STATUS="HOLD_ROLLBACK_INCOMPLETE"
    return 1
  }

  post_snapshot_path="$RUN_DIR_REAL/rollback_sanitized_inspect.env"
  if ! write_sanitized_snapshot_file "$post_snapshot_path"; then
    ROLLBACK_POST_SNAPSHOT_PATH="$post_snapshot_path"
    ROLLBACK_MISMATCH_FIELDS="ROLLBACK_SANITIZED_INSPECT_WRITE_FAILED"
    FAIL_STATUS="HOLD_ROLLBACK_INCOMPLETE"
    return 1
  fi
  ROLLBACK_POST_SNAPSHOT_PATH="$post_snapshot_path"

  for field in SNAPSHOT_SCHEMA RUN_ID SOURCE_HEAD IMAGE_TAG "${ROLLBACK_CONTAINER_COMPARE_FIELDS[@]}" "${TAG_SNAPSHOT_FIELDS[@]}" "${NETWORK_SNAPSHOT_FIELDS[@]}"; do
    pre_value="$(snapshot_get_value "$PRE_STATE_PATH" "$field" 2>/dev/null || true)"
    post_value="$(snapshot_get_value "$post_snapshot_path" "$field" 2>/dev/null || true)"
    if [[ "$pre_value" != "$post_value" ]]; then
      mismatches+=("$field")
    fi
  done

  if ((${#mismatches[@]} == 0)); then
    ROLLBACK_COMPLETE=true
    ROLLBACK_MISMATCH_FIELDS=""
    return 0
  fi

  local IFS=,
  ROLLBACK_MISMATCH_FIELDS="${mismatches[*]}"
  FAIL_STATUS="HOLD_ROLLBACK_INCOMPLETE"
  return 1
}

write_failure_receipt() {
  local exit_code="$1"
  local failure_path
  local failure_tmp
  local failure_sha_path
  local failure_sha_tmp
  local failure_sha

  [[ -n "${RUN_DIR_REAL:-}" && -d "$RUN_DIR_REAL" ]] || return 1
  failure_path="$RUN_DIR_REAL/failure.env"
  failure_tmp="$RUN_DIR_REAL/.failure.env.$$"
  failure_sha_path="$RUN_DIR_REAL/failure.env.sha256"
  failure_sha_tmp="$RUN_DIR_REAL/.failure.env.sha256.$$"
  case "$failure_path" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$failure_tmp" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$failure_sha_path" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  case "$failure_sha_tmp" in
    "$REPO_ROOT"/*)
      ;;
    *)
      return 1
      ;;
  esac
  [[ ! -L "$failure_path" && ! -L "$failure_sha_path" && ! -e "$failure_tmp" && ! -L "$failure_tmp" && ! -e "$failure_sha_tmp" && ! -L "$failure_sha_tmp" ]] || return 1

  {
    printf 'STATUS=%s\n' "$FAIL_STATUS"
    printf 'FAILURE_SEALED=true\n'
    printf 'EXIT_CODE=%s\n' "$exit_code"
    printf 'FAIL_REASON=%s\n' "$FAIL_REASON"
    printf 'RUN_ID=%s\n' "$RUN_ID"
    printf 'SOURCE_HEAD=%s\n' "$SOURCE_HEAD"
    printf 'INITIAL_INDEX_FINGERPRINT=%s\n' "$INITIAL_INDEX_FINGERPRINT"
    printf 'INITIAL_RELEASE_STATUS_FINGERPRINT=%s\n' "$INITIAL_RELEASE_STATUS_FINGERPRINT"
    printf 'RELEASE_SHA=%s\n' "${RELEASE_SHA:-}"
    printf 'CLOUDFLARE_CONFIG_PATH=%s\n' "$CLOUDFLARE_CONFIG_PATH"
    printf 'CLOUDFLARE_CONFIG_BLOB_ID=%s\n' "$CLOUDFLARE_CONFIG_BLOB_ID"
    printf 'CLOUDFLARE_CONFIG_SHA256=%s\n' "$CLOUDFLARE_CONFIG_SHA256"
    printf 'IMAGE_TAG=%s\n' "${IMAGE_TAG:-}"
    printf 'IMAGE_ID=%s\n' "${IMAGE_ID:-}"
    printf 'CURRENT_IMAGE_ID_DISCOVERED_FROM_TAG=%s\n' "$CURRENT_IMAGE_ID_DISCOVERED_FROM_TAG"
    printf 'HOMEPAGE=%s\n' "$HOMEPAGE_STATUS"
    printf 'DOMAIN_BINDING=%s\n' "$DOMAIN_BINDING"
    printf 'DNS_WRITE=false\n'
    printf 'MX_TXT_WRITE=false\n'
    printf 'HOMEPAGE_EFFECT_STARTED_AT_EPOCH=%s\n' "$HOMEPAGE_EFFECT_STARTED_AT_EPOCH"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_VALIDATION=%s\n' "$RUNTIME_RECEIPT_VALIDATION"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_REASON=%s\n' "$RUNTIME_RECEIPT_REASON"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_PATH=%s\n' "$CLOUDFLARED_RUNTIME_RECEIPT_PATH"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_SHA256=%s\n' "$CLOUDFLARED_RUNTIME_RECEIPT_SHA256"
    printf 'EFFECT_STARTED=%s\n' "$EFFECT_STARTED"
    printf 'BUILD_EFFECT_STARTED=%s\n' "$BUILD_EFFECT_STARTED"
    printf 'COMPOSE_EFFECT_STARTED=%s\n' "$COMPOSE_EFFECT_STARTED"
    printf 'ROLLBACK_ATTEMPTED=%s\n' "$ROLLBACK_ATTEMPTED"
    printf 'ROLLBACK_COMPLETE=%s\n' "$ROLLBACK_COMPLETE"
    printf 'ROLLBACK_MISMATCH_FIELDS=%s\n' "$ROLLBACK_MISMATCH_FIELDS"
    printf 'ROLLBACK_POST_SANITIZED_INSPECT=%s\n' "$ROLLBACK_POST_SNAPSHOT_PATH"
    printf 'ROLLBACK_CONTAINER_RESULT=%s\n' "$ROLLBACK_CONTAINER_RESULT"
    printf 'ROLLBACK_ASSET_NAME=%s\n' "$ROLLBACK_ASSET_NAME"
    printf 'ROLLBACK_ASSET_ID=%s\n' "$ROLLBACK_ASSET_ID"
    printf 'ROLLBACK_ASSET_STATE=%s\n' "$ROLLBACK_ASSET_STATE"
    printf 'ROLLBACK_TAG_RESULT=%s\n' "$ROLLBACK_TAG_RESULT"
    printf 'ROLLBACK_NETWORK_RESULT=%s\n' "$ROLLBACK_NETWORK_RESULT"
    write_pre_state_entries
  } > "$failure_tmp" || return 1
  mv -f -- "$failure_tmp" "$failure_path" || return 1
  failure_sha="$(sha256sum "$failure_path" | awk '{ print $1 }')" || return 1
  [[ "$failure_sha" =~ ^[0-9a-f]{64}$ ]] || return 1
  printf '%s  failure.env\n' "$failure_sha" > "$failure_sha_tmp" || return 1
  mv -f -- "$failure_sha_tmp" "$failure_sha_path" || return 1
}

on_err() {
  local code="$?"

  if [[ "$code" != "0" && "$FAIL_REASON" == "UNHANDLED_EXIT" ]]; then
    FAIL_REASON="UNHANDLED_ERROR_STEP_$CURRENT_STEP"
  fi
  return "$code"
}

on_exit() {
  local exit_code="$?"

  set +e
  if [[ "$exit_code" -ne 0 ]]; then
    if [[ "$FAIL_REASON" == "UNHANDLED_EXIT" ]]; then
      FAIL_REASON="EXIT_${exit_code}_STEP_$CURRENT_STEP"
    fi
    if [[ "$EFFECT_STARTED" == true && "$DOMAIN_HOLD_NO_ROLLBACK" != true ]]; then
      attempt_rollback
      if ! verify_rollback_state; then
        printf 'STATUS=HOLD_ROLLBACK_INCOMPLETE\n' >&2
        printf 'ROLLBACK_MISMATCH_FIELDS=%s\n' "$ROLLBACK_MISMATCH_FIELDS" >&2
        printf 'ROLLBACK_CONTAINER_RESULT=%s\n' "$ROLLBACK_CONTAINER_RESULT" >&2
        printf 'ROLLBACK_TAG_RESULT=%s\n' "$ROLLBACK_TAG_RESULT" >&2
        printf 'ROLLBACK_NETWORK_RESULT=%s\n' "$ROLLBACK_NETWORK_RESULT" >&2
      fi
    elif [[ "$DOMAIN_HOLD_NO_ROLLBACK" == true ]]; then
      ROLLBACK_COMPLETE="NOT_ATTEMPTED_DOMAIN_HOLD"
    fi
    if ! write_failure_receipt "$exit_code"; then
      printf 'STATUS=HOLD_FAILURE_SEAL_WRITE_FAILED\n' >&2
      printf 'FAIL_REASON=%s\n' "$FAIL_REASON" >&2
    fi
  fi
  cleanup_temp
  release_deploy_lock
  exit "$exit_code"
}

write_receipt() {
  local run_id="$1"
  local git_head="$2"
  local site_tree_sha="$3"
  local release_sha="$4"
  local base_image="$5"
  local base_image_id="$6"
  local image="$7"
  local image_id="$8"
  local container_id="$9"
  local port_binding="${10}"
  local health="${11}"
  local receipt_path
  local receipt_tmp
  local receipt_sha_path
  local receipt_sha_tmp
  local receipt_sha

  [[ -n "$RUN_DIR_REAL" && -d "$RUN_DIR_REAL" ]] || fail 80 "RUN_DIR_NOT_READY_FOR_RECEIPT"
  receipt_path="$RUN_DIR_REAL/receipt.env"
  receipt_tmp="$RUN_DIR_REAL/.receipt.env.$$"
  receipt_sha_path="$RUN_DIR_REAL/receipt.env.sha256"
  receipt_sha_tmp="$RUN_DIR_REAL/.receipt.env.sha256.$$"
  assert_abs_path_in_repo "$receipt_path"
  assert_abs_path_in_repo "$receipt_tmp"
  assert_abs_path_in_repo "$receipt_sha_path"
  assert_abs_path_in_repo "$receipt_sha_tmp"
  [[ ! -e "$receipt_path" && ! -L "$receipt_path" && ! -e "$receipt_sha_path" && ! -L "$receipt_sha_path" && ! -e "$receipt_tmp" && ! -L "$receipt_tmp" && ! -e "$receipt_sha_tmp" && ! -L "$receipt_sha_tmp" ]] || fail 81 "RECEIPT_PATH_NOT_CLEAN"

  {
    printf 'RUN_ID=%s\n' "$run_id"
    printf 'DNS_WRITE=false\n'
    printf 'MX_TXT_WRITE=false\n'
    printf 'HOMEPAGE=PASS\n'
    printf 'DOMAIN_BINDING=PASS\n'
    printf 'SOURCE_HEAD=%s\n' "$git_head"
    printf 'GIT_HEAD=%s\n' "$git_head"
    printf 'INITIAL_INDEX_FINGERPRINT=%s\n' "$INITIAL_INDEX_FINGERPRINT"
    printf 'INITIAL_RELEASE_STATUS_FINGERPRINT=%s\n' "$INITIAL_RELEASE_STATUS_FINGERPRINT"
    printf 'SITE_TREE_SHA=%s\n' "$site_tree_sha"
    printf 'RELEASE_SHA=%s\n' "$release_sha"
    printf 'CLOUDFLARE_CONFIG_PATH=%s\n' "$CLOUDFLARE_CONFIG_PATH"
    printf 'CLOUDFLARE_CONFIG_BLOB_ID=%s\n' "$CLOUDFLARE_CONFIG_BLOB_ID"
    printf 'CLOUDFLARE_CONFIG_SHA256=%s\n' "$CLOUDFLARE_CONFIG_SHA256"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_VALIDATION=%s\n' "$RUNTIME_RECEIPT_VALIDATION"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_PATH=%s\n' "$CLOUDFLARED_RUNTIME_RECEIPT_PATH"
    printf 'CLOUDFLARED_RUNTIME_RECEIPT_SHA256=%s\n' "$CLOUDFLARED_RUNTIME_RECEIPT_SHA256"
    printf 'NGINX_BASE_IMAGE=%s\n' "$base_image"
    printf 'NGINX_BASE_IMAGE_ID=%s\n' "$base_image_id"
    printf 'WUCHANG_HOMEPAGE_IMAGE_TAG=%s\n' "$image"
    printf 'IMAGE_ID=%s\n' "$image_id"
    printf 'CONTAINER_NAME=%s\n' "$CONTAINER_NAME"
    printf 'CONTAINER_ID=%s\n' "$container_id"
    printf 'CONTAINER_TOOL_LABEL_KEY=%s\n' "$TOOL_CONTAINER_LABEL_KEY"
    printf 'CONTAINER_TOOL_LABEL_VALUE=%s\n' "$TOOL_CONTAINER_LABEL_VALUE"
    printf 'ROLLBACK_ASSET_NAME=%s\n' "$ROLLBACK_ASSET_NAME"
    printf 'ROLLBACK_ASSET_ID=%s\n' "$ROLLBACK_ASSET_ID"
    printf 'ROLLBACK_ASSET_STATE=%s\n' "$ROLLBACK_ASSET_STATE"
    printf 'PORT_BINDING=%s\n' "$port_binding"
    printf 'HEALTH=%s\n' "$health"
    printf 'HOMEPAGE_EFFECT_STARTED_AT_EPOCH=%s\n' "$HOMEPAGE_EFFECT_STARTED_AT_EPOCH"
    printf 'COMPOSE_FILE=%s\n' "$COMPOSE_FILE"
    printf 'SECURITY_CONFIG_USER=%s\n' "$SECURITY_CONFIG_USER"
    printf 'SECURITY_READONLY_ROOTFS=%s\n' "$SECURITY_READONLY_ROOTFS"
    printf 'SECURITY_CAP_DROP=%s\n' "$SECURITY_CAP_DROP"
    printf 'SECURITY_SECURITY_OPT=%s\n' "$SECURITY_SECURITY_OPT"
    printf 'SECURITY_PRIVILEGED=%s\n' "$SECURITY_PRIVILEGED"
    printf 'SECURITY_BIND_MOUNTS=%s\n' "$SECURITY_BIND_MOUNTS"
    printf 'SECURITY_NETWORK_NAME=%s\n' "$SECURITY_NETWORK_NAME"
    printf 'SECURITY_NETWORK_INTERNAL=%s\n' "$SECURITY_NETWORK_INTERNAL"
    printf 'SECURITY_PORT_BINDING=%s\n' "$SECURITY_PORT_BINDING"
    write_pre_state_entries
    write_release_control_receipt_entries
    context_file_hashes | while read -r hash path; do
      printf 'FILE_SHA256_%s=%s\n' "$(printf '%s' "$path" | sed 's#[^A-Za-z0-9]#_#g')" "$hash"
    done
  } > "$receipt_tmp"
  mv -- "$receipt_tmp" "$receipt_path"

  receipt_sha="$(sha256sum "$receipt_path" | awk '{ print $1 }')"
  printf '%s  receipt.env\n' "$receipt_sha" > "$receipt_sha_tmp"
  mv -- "$receipt_sha_tmp" "$receipt_sha_path"
  printf '%s\n' "$receipt_path"
}

trap on_err ERR
trap on_exit EXIT

require_command git
require_command docker
require_command tar
require_command find
require_command sort
require_command sha256sum
require_command awk
require_command sed
require_command date
require_command mktemp
require_command grep
require_command head
require_command wc
require_command mkdir
require_command mv
require_command rm
require_command rmdir
require_command sleep
require_command stat
docker compose version >/dev/null 2>&1 || fail 21 "MISSING_LOCAL_DOCKER_COMPOSE"

CURRENT_STEP="acquire_deploy_lock"
acquire_deploy_lock
INITIAL_INDEX_FINGERPRINT="$(compute_index_fingerprint)"
INITIAL_RELEASE_STATUS_FINGERPRINT="$(compute_release_status_fingerprint)"
write_lock_owner

CURRENT_STEP="verify_source_release_control"
require_source_state_unchanged "INITIAL"
require_release_control_clean
verify_cloudflare_config
require_exact_source_site_tree
create_verified_context

GIT_HEAD="$SOURCE_HEAD"
SITE_TREE_SHA="$(git rev-parse "$SOURCE_HEAD:$SITE_TREE_PATH")"
RELEASE_SHA="$(compute_release_sha)"
CLOUDFLARE_CONFIG_BLOB_ID="$(git rev-parse "$SOURCE_HEAD:$CLOUDFLARE_CONFIG_PATH")"
CLOUDFLARE_CONFIG_SHA256="$(source_file_sha256 "$CLOUDFLARE_CONFIG_PATH")"
IMAGE_TAG="wuchang-homepage:${SITE_TREE_SHA}-${RELEASE_SHA:0:12}"
BASE_IMAGE="$(select_fixed_local_nginx_base)"
BASE_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$BASE_IMAGE")"
require_image_tag_not_conflicting "$IMAGE_TAG" "$SITE_TREE_SHA" "$RELEASE_SHA"
RUN_ID="$(date -u +%Y%m%dT%H%M%S%NZ)-${SOURCE_HEAD:0:12}-${RELEASE_SHA:0:12}"
ROLLBACK_ASSET_NAME="${CONTAINER_NAME}.rollback.${RUN_ID}"
RUN_DIR_REAL="$(create_repo_run_dir "$RUN_ROOT/$RUN_ID")"
capture_pre_state
preflight_existing_container_for_exact_rollback

CURRENT_STEP="docker_build"
require_source_state_unchanged "DOCKER_BUILD"
EFFECT_STARTED=true
BUILD_EFFECT_STARTED=true
docker build \
  --pull=false \
  --network=none \
  --build-arg "NGINX_BASE_IMAGE=$BASE_IMAGE" \
  --label "org.opencontainers.image.revision=$GIT_HEAD" \
  --label "org.wuchang.homepage.site_tree_sha=$SITE_TREE_SHA" \
  --label "org.wuchang.homepage.release_sha=$RELEASE_SHA" \
  --label "org.wuchang.homepage.base_image=$BASE_IMAGE" \
  --label "org.wuchang.homepage.base_image_id=$BASE_IMAGE_ID" \
  --tag "$IMAGE_TAG" \
  "$CONTEXT_DIR"

IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE_TAG")"
[[ "$IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || fail 52 "IMAGE_ID_NOT_SHA256_ID"
verify_image_label "$IMAGE_TAG" "org.opencontainers.image.revision" "$GIT_HEAD"
verify_image_label "$IMAGE_TAG" "org.wuchang.homepage.site_tree_sha" "$SITE_TREE_SHA"
verify_image_label "$IMAGE_TAG" "org.wuchang.homepage.release_sha" "$RELEASE_SHA"
verify_image_label "$IMAGE_TAG" "org.wuchang.homepage.base_image" "$BASE_IMAGE"
verify_image_label "$IMAGE_TAG" "org.wuchang.homepage.base_image_id" "$BASE_IMAGE_ID"

export WUCHANG_HOMEPAGE_IMAGE_ID="$IMAGE_ID"
docker compose --project-name "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" config --quiet
CURRENT_STEP="compose_run"
require_source_state_unchanged "COMPOSE_RUN"
COMPOSE_EFFECT_STARTED=true
preserve_pre_container_for_rollback
docker compose --project-name "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" run -d --no-deps --service-ports --name "$CONTAINER_NAME" --no-build --pull never "$SERVICE_NAME"

verify_container_image_id "$IMAGE_ID"
verify_current_container_tool_label
HOMEPAGE_EFFECT_STARTED_AT_EPOCH="$(read_verified_container_started_epoch)"
HEALTH="$(wait_for_healthy)"
PORT_BINDING="$(verify_port_binding)"
verify_container_security
CONTAINER_ID="$(docker container inspect --format '{{.Id}}' "$CONTAINER_NAME")"
record_rollback_asset_state
HOMEPAGE_STATUS="PASS"

CURRENT_STEP="verify_domain_ingress_runtime_receipt"
if ! verify_cloudflared_runtime_receipt; then
  domain_hold "$RUNTIME_RECEIPT_REASON"
fi

RECEIPT_PATH="$(write_receipt "$RUN_ID" "$GIT_HEAD" "$SITE_TREE_SHA" "$RELEASE_SHA" "$BASE_IMAGE" "$BASE_IMAGE_ID" "$IMAGE_TAG" "$IMAGE_ID" "$CONTAINER_ID" "$PORT_BINDING" "$HEALTH")"
RECEIPT_SHA="$(sha256sum "$RECEIPT_PATH" | awk '{ print $1 }')"
SUCCESS_WRITTEN=true

printf 'STATUS=OK\n'
printf 'HOMEPAGE=PASS\n'
printf 'DOMAIN_BINDING=PASS\n'
printf 'RUN_ID=%s\n' "$RUN_ID"
printf 'SOURCE_HEAD=%s\n' "$SOURCE_HEAD"
printf 'SITE_TREE_SHA=%s\n' "$SITE_TREE_SHA"
printf 'RELEASE_SHA=%s\n' "$RELEASE_SHA"
printf 'CLOUDFLARE_CONFIG_SHA256=%s\n' "$CLOUDFLARE_CONFIG_SHA256"
printf 'WUCHANG_HOMEPAGE_IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf 'IMAGE_ID=%s\n' "$IMAGE_ID"
printf 'CONTAINER_ID=%s\n' "$CONTAINER_ID"
printf 'CONTAINER_TOOL_LABEL_KEY=%s\n' "$TOOL_CONTAINER_LABEL_KEY"
printf 'CONTAINER_TOOL_LABEL_VALUE=%s\n' "$TOOL_CONTAINER_LABEL_VALUE"
printf 'ROLLBACK_ASSET_NAME=%s\n' "$ROLLBACK_ASSET_NAME"
printf 'ROLLBACK_ASSET_ID=%s\n' "$ROLLBACK_ASSET_ID"
printf 'ROLLBACK_ASSET_STATE=%s\n' "$ROLLBACK_ASSET_STATE"
printf 'PORT_BINDING=%s\n' "$PORT_BINDING"
printf 'HEALTH=%s\n' "$HEALTH"
printf 'DNS_WRITE=false\n'
printf 'MX_TXT_WRITE=false\n'
printf 'CLOUDFLARED_RUNTIME_RECEIPT_SHA256=%s\n' "$CLOUDFLARED_RUNTIME_RECEIPT_SHA256"
printf 'RECEIPT=%s\n' "$RECEIPT_PATH"
printf 'RECEIPT_SHA256=%s\n' "$RECEIPT_SHA"
