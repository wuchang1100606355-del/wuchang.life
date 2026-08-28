#!/usr/bin/env bash
set -Eeuo pipefail

CONTAINER_NAME="wuchang-domain-gateway"
NETWORK_NAME="wuchang-domain-gateway-internal"
COMPOSE_FILE_REL="docker-compose.domain-gateway.yml"
APPLY_FILE_REL="deploy/domain_gateway/apply_immutable_image.sh"
DOCKERFILE_REL="deploy/domain_gateway/Dockerfile"
DEFAULT_CONF_REL="deploy/domain_gateway/nginx/default.conf"
RECEIPT_ROOT_REL="runtime/domain_gateway/deploy_receipts"

ERROR_MESSAGE=""
FINAL_STATUS=""
RECEIPT_TMP_DIR=""
RECEIPT_DIR=""
RECEIPT_PUBLISHED=0
FAILURE_HANDLING=0
EFFECT_STARTED=0
NETWORK_CREATED=0
OLD_CONTAINER_EXISTS=0
OLD_CONTAINER_ID=""
OLD_CONTAINER_IMAGE=""
OLD_CONTAINER_CONFIG_IMAGE=""
OLD_CONTAINER_WAS_RUNNING="false"
OLD_CONTAINER_OWNS_8089=0
OLD_CONTAINER_HEALTH=""
OLD_CONTAINER_CONFIG_SHA256=""
OLD_CONTAINER_HOSTCONFIG_SHA256=""
OLD_CONTAINER_PORT_BINDINGS_JSON=""
OLD_ROLLBACK_NAME=""
OLD_RENAMED=0
NEW_CONTAINER_ID=""
STATUS_HASH_BEFORE=""
STATUS_HASH_BEFORE_EFFECT=""
STATUS_HASH_AFTER_EFFECT=""
STATUS_HASH_AFTER_RECEIPT=""
HEAD_BEFORE=""
HEAD_BEFORE_EFFECT=""
HEAD_AFTER_EFFECT=""
HEAD_AFTER_RECEIPT=""
PRE_LISTENER_8088=""
PRE_LISTENER_8089=""

die() {
  ERROR_MESSAGE="${*:-command failed}"
  return 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

sha256_stdin() {
  sha256sum | awk '{ print $1 }'
}

git_status_hash() {
  git -C "$ROOT" status --porcelain=v1 -z --untracked-files=all | sha256_stdin
}

current_head() {
  git -C "$ROOT" rev-parse HEAD
}

assert_source_head_stable() {
  local phase="$1"
  local head
  head="$(current_head)"
  [[ "$head" == "$SOURCE_HEAD" ]] || die "SOURCE_HEAD drifted ${phase}"
}

assert_git_status_stable() {
  local phase="$1"
  local status_hash
  status_hash="$(git_status_hash)"
  [[ "$status_hash" == "$STATUS_HASH_BEFORE" ]] || die "git status hash drifted ${phase}"
}

assert_status_and_head_stable() {
  local phase="$1"
  assert_source_head_stable "$phase"
  assert_git_status_stable "$phase"
}

container_exists() {
  docker container inspect "$1" >/dev/null 2>&1
}

network_exists() {
  docker network inspect "$1" >/dev/null 2>&1
}

network_internal() {
  docker network inspect "$1" --format '{{ .Internal }}'
}

container_field() {
  docker container inspect "$1" --format "$2"
}

container_owns_host_port() {
  local container_ref="$1"
  local port="$2"
  docker port "$container_ref" | awk -v suffix=":${port}" '
    index($NF, suffix) == length($NF) - length(suffix) + 1 { found=1 }
    END { exit found ? 0 : 1 }
  '
}

image_label() {
  docker image inspect "$TARGET_IMAGE_ID" --format "{{ index .Config.Labels \"$1\" }}"
}

assert_image_label() {
  local key="$1"
  local expected="$2"
  local actual
  actual="$(image_label "$key")"
  [[ "$actual" == "$expected" ]] || die "target image label mismatch for ${key}"
}

listener_lines() {
  local port="$1"
  ss -H -ltn | awk -v suffix=":${port}" 'index($4, suffix) == length($4) - length(suffix) + 1 { print }'
}

listener_exists() {
  local port="$1"
  ss -H -ltn | awk -v suffix=":${port}" '
    index($4, suffix) == length($4) - length(suffix) + 1 { found=1 }
    END { exit found ? 0 : 1 }
  '
}

capture_listeners() {
  local dir="$1"
  ss -H -ltn > "${dir}/ss_listen_tcp.txt"
  listener_lines 8088 > "${dir}/listener_8088.txt"
  listener_lines 8089 > "${dir}/listener_8089.txt"
  {
    if listener_exists 8088; then
      printf 'LISTENER_8088=YES\n'
    else
      printf 'LISTENER_8088=NO\n'
    fi
    if listener_exists 8089; then
      printf 'LISTENER_8089=YES\n'
    else
      printf 'LISTENER_8089=NO\n'
    fi
  } > "${dir}/listeners.env"
}

write_env_line() {
  local key="$1"
  local value="$2"
  printf '%s=%q\n' "$key" "$value"
}

capture_image_allowlist() {
  local image_ref="$1"
  local output_file="$2"
  {
    write_env_line PRESENT YES
    write_env_line IMAGE_ID "$(docker image inspect "$image_ref" --format '{{ .Id }}')"
    write_env_line IMAGE_CONFIG_SHA256 "$(docker image inspect "$image_ref" --format '{{ json .Config }}' | sha256_stdin)"
    write_env_line IMAGE_REPO_DIGESTS_SHA256 "$(docker image inspect "$image_ref" --format '{{ range .RepoDigests }}{{ println . }}{{ end }}' | LC_ALL=C sort | sha256_stdin)"
  } > "$output_file"
}

capture_network_allowlist() {
  local network_ref="$1"
  local output_file="$2"
  {
    write_env_line PRESENT YES
    write_env_line NETWORK_ID "$(docker network inspect "$network_ref" --format '{{ .Id }}')"
    write_env_line DRIVER "$(docker network inspect "$network_ref" --format '{{ .Driver }}')"
    write_env_line INTERNAL "$(docker network inspect "$network_ref" --format '{{ .Internal }}')"
    write_env_line SCOPE "$(docker network inspect "$network_ref" --format '{{ .Scope }}')"
    write_env_line ENDPOINT_COUNT "$(docker network inspect "$network_ref" --format '{{ len .Containers }}')"
  } > "$output_file"
}

capture_container_allowlist() {
  local container_ref="$1"
  local output_file="$2"
  local bind_mounts
  local bind_mount_present=NO
  bind_mounts="$(container_field "$container_ref" '{{ range .Mounts }}{{ if eq .Type "bind" }}bind{{ println }}{{ end }}{{ end }}')"
  [[ -z "$bind_mounts" ]] || bind_mount_present=YES
  {
    write_env_line PRESENT YES
    write_env_line CONTAINER_ID "$(container_field "$container_ref" '{{ .Id }}')"
    write_env_line IMAGE_ID "$(container_field "$container_ref" '{{ .Image }}')"
    write_env_line CONFIG_IMAGE "$(container_field "$container_ref" '{{ .Config.Image }}')"
    write_env_line RUNNING "$(container_field "$container_ref" '{{ .State.Running }}')"
    write_env_line HEALTH "$(container_field "$container_ref" '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}none{{ end }}')"
    write_env_line USER "$(container_field "$container_ref" '{{ .Config.User }}')"
    write_env_line READ_ONLY_ROOTFS "$(container_field "$container_ref" '{{ .HostConfig.ReadonlyRootfs }}')"
    write_env_line PRIVILEGED "$(container_field "$container_ref" '{{ .HostConfig.Privileged }}')"
    write_env_line CAP_DROP "$(container_field "$container_ref" '{{ json .HostConfig.CapDrop }}')"
    write_env_line SECURITY_OPT "$(container_field "$container_ref" '{{ json .HostConfig.SecurityOpt }}')"
    write_env_line PORT_BINDINGS "$(container_field "$container_ref" '{{ json .HostConfig.PortBindings }}')"
    write_env_line NETWORK_NAMES "$(container_field "$container_ref" '{{ range $k, $_ := .NetworkSettings.Networks }}{{ println $k }}{{ end }}' | LC_ALL=C sort | tr '\n' ',')"
    write_env_line RESTART_POLICY "$(container_field "$container_ref" '{{ .HostConfig.RestartPolicy.Name }}')"
    write_env_line BIND_MOUNT_PRESENT "$bind_mount_present"
    write_env_line CONFIG_SHA256 "$(container_field "$container_ref" '{{ json .Config }}' | sha256_stdin)"
    write_env_line HOSTCONFIG_SHA256 "$(container_field "$container_ref" '{{ json .HostConfig }}' | sha256_stdin)"
  } > "$output_file"
}

write_dir_sha() {
  local rel="$1"
  local dir="${RECEIPT_TMP_DIR}/${rel}"
  local files=()
  mkdir -p -- "$dir"
  while IFS= read -r -d '' file; do
    files+=("$file")
  done < <(
    cd "$dir"
    find . -type f ! -name evidence.sha256 -printf '%P\0' | LC_ALL=C sort -z
  )
  if ((${#files[@]})); then
    (
      cd "$dir"
      sha256sum "${files[@]}"
    ) > "${dir}/evidence.sha256"
  else
    : > "${dir}/evidence.sha256"
  fi
}

write_manifest() {
  local files=()
  while IFS= read -r -d '' file; do
    files+=("$file")
  done < <(
    cd "$RECEIPT_TMP_DIR"
    find . -type f ! -name manifest.sha256 -printf '%P\0' | LC_ALL=C sort -z
  )
  (
    cd "$RECEIPT_TMP_DIR"
    sha256sum "${files[@]}"
  ) > "${RECEIPT_TMP_DIR}/manifest.sha256"
}

write_summary() {
  local status="$1"
  {
    write_env_line STATUS "$status"
    write_env_line ERROR_MESSAGE "$ERROR_MESSAGE"
    write_env_line RUN_ID "$RUN_ID"
    write_env_line SOURCE_HEAD "$SOURCE_HEAD"
    write_env_line TARGET_IMAGE_ID "$TARGET_IMAGE_ID"
    write_env_line TARGET_IMAGE_SHA256 "$WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256"
    write_env_line COMPOSE_PROJECT_NAME "$COMPOSE_PROJECT_NAME"
    write_env_line RECEIPT_DIR "$RECEIPT_DIR"
    write_env_line STATUS_HASH_BEFORE "$STATUS_HASH_BEFORE"
    write_env_line STATUS_HASH_BEFORE_EFFECT "$STATUS_HASH_BEFORE_EFFECT"
    write_env_line STATUS_HASH_AFTER_EFFECT "$STATUS_HASH_AFTER_EFFECT"
    write_env_line STATUS_HASH_AFTER_RECEIPT "$STATUS_HASH_AFTER_RECEIPT"
    write_env_line HEAD_BEFORE "$HEAD_BEFORE"
    write_env_line HEAD_BEFORE_EFFECT "$HEAD_BEFORE_EFFECT"
    write_env_line HEAD_AFTER_EFFECT "$HEAD_AFTER_EFFECT"
    write_env_line HEAD_AFTER_RECEIPT "$HEAD_AFTER_RECEIPT"
    write_env_line NETWORK_NAME "$NETWORK_NAME"
    write_env_line NETWORK_CREATED "$NETWORK_CREATED"
    write_env_line OLD_CONTAINER_EXISTS "$OLD_CONTAINER_EXISTS"
    write_env_line OLD_CONTAINER_ID "$OLD_CONTAINER_ID"
    write_env_line OLD_CONTAINER_IMAGE "$OLD_CONTAINER_IMAGE"
    write_env_line OLD_CONTAINER_CONFIG_IMAGE "$OLD_CONTAINER_CONFIG_IMAGE"
    write_env_line OLD_CONTAINER_WAS_RUNNING "$OLD_CONTAINER_WAS_RUNNING"
    write_env_line PRE_LISTENER_8088 "$PRE_LISTENER_8088"
    write_env_line PRE_LISTENER_8089 "$PRE_LISTENER_8089"
    write_env_line OLD_CONTAINER_OWNS_8089 "$OLD_CONTAINER_OWNS_8089"
    write_env_line OLD_ROLLBACK_NAME "$OLD_ROLLBACK_NAME"
    write_env_line OLD_ROLLBACK_CONTAINER_RETAINED "$OLD_RENAMED"
    write_env_line NEW_CONTAINER_ID "$NEW_CONTAINER_ID"
  } > "${RECEIPT_TMP_DIR}/summary.env"
}

publish_receipt() {
  local status="$1"
  [[ -n "$RECEIPT_TMP_DIR" && -d "$RECEIPT_TMP_DIR" ]] || return 0
  [[ "$RECEIPT_PUBLISHED" == "0" ]] || return 0

  mkdir -p -- "${RECEIPT_TMP_DIR}/pre" "${RECEIPT_TMP_DIR}/post" "${RECEIPT_TMP_DIR}/rollback" || return 1
  write_dir_sha pre || return 1
  write_dir_sha post || return 1
  write_dir_sha rollback || return 1
  STATUS_HASH_AFTER_RECEIPT="$(git_status_hash 2>/dev/null || printf 'UNAVAILABLE')"
  HEAD_AFTER_RECEIPT="$(current_head 2>/dev/null || printf 'UNAVAILABLE')"
  if [[ "$status" == "APPLY_DOMAIN_GATEWAY_APPLIED" ]]; then
    [[ "$STATUS_HASH_AFTER_RECEIPT" == "$STATUS_HASH_BEFORE" ]] || return 1
    [[ "$HEAD_AFTER_RECEIPT" == "$SOURCE_HEAD" ]] || return 1
  fi
  write_summary "$status" || return 1
  write_manifest || return 1
  if [[ "$status" == "APPLY_DOMAIN_GATEWAY_APPLIED" ]]; then
    [[ "$(git_status_hash 2>/dev/null || printf 'UNAVAILABLE')" == "$STATUS_HASH_BEFORE" ]] || return 1
    [[ "$(current_head 2>/dev/null || printf 'UNAVAILABLE')" == "$SOURCE_HEAD" ]] || return 1
  fi
  [[ ! -e "$RECEIPT_DIR" && ! -L "$RECEIPT_DIR" ]] || return 1
  mv -Tn -- "$RECEIPT_TMP_DIR" "$RECEIPT_DIR" || return 1
  [[ ! -e "$RECEIPT_TMP_DIR" ]] || return 1
  [[ -f "${RECEIPT_DIR}/summary.env" && -f "${RECEIPT_DIR}/manifest.sha256" ]] || return 1
  RECEIPT_TMP_DIR=""
  RECEIPT_PUBLISHED=1
}

cleanup_tmp_receipt() {
  if [[ "$RECEIPT_PUBLISHED" == "0" && -n "$RECEIPT_TMP_DIR" && -f "${RECEIPT_TMP_DIR}/.domain_gateway_apply_tmp.marker" ]]; then
    case "$RECEIPT_TMP_DIR" in
      "$RECEIPT_ROOT"/.domain-gateway-apply.*) rm -rf -- "$RECEIPT_TMP_DIR" ;;
    esac
  fi
}

rollback_verify_old_container() {
  local ok=0
  if [[ "$OLD_CONTAINER_EXISTS" == "1" ]]; then
    if ! container_exists "$CONTAINER_NAME"; then
      printf 'original container missing after rollback\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
      return 1
    fi
    local current_id
    local current_image
    local current_running
    local current_config_image
    local current_config_sha256
    local current_hostconfig_sha256
    local current_port_bindings_json
    current_id="$(container_field "$CONTAINER_NAME" '{{ .Id }}')" || ok=1
    current_image="$(container_field "$CONTAINER_NAME" '{{ .Image }}')" || ok=1
    current_running="$(container_field "$CONTAINER_NAME" '{{ .State.Running }}')" || ok=1
    current_config_image="$(container_field "$CONTAINER_NAME" '{{ .Config.Image }}')" || ok=1
    current_config_sha256="$(container_field "$CONTAINER_NAME" '{{ json .Config }}' | sha256_stdin)" || ok=1
    current_hostconfig_sha256="$(container_field "$CONTAINER_NAME" '{{ json .HostConfig }}' | sha256_stdin)" || ok=1
    current_port_bindings_json="$(container_field "$CONTAINER_NAME" '{{ json .HostConfig.PortBindings }}')" || ok=1
    [[ "$current_id" == "$OLD_CONTAINER_ID" ]] || ok=1
    [[ "$current_image" == "$OLD_CONTAINER_IMAGE" ]] || ok=1
    [[ "$current_running" == "$OLD_CONTAINER_WAS_RUNNING" ]] || ok=1
    [[ "$current_config_image" == "$OLD_CONTAINER_CONFIG_IMAGE" ]] || ok=1
    [[ "$current_config_sha256" == "$OLD_CONTAINER_CONFIG_SHA256" ]] || ok=1
    [[ "$current_hostconfig_sha256" == "$OLD_CONTAINER_HOSTCONFIG_SHA256" ]] || ok=1
    [[ "$current_port_bindings_json" == "$OLD_CONTAINER_PORT_BINDINGS_JSON" ]] || ok=1
    capture_container_allowlist "$CONTAINER_NAME" "${RECEIPT_TMP_DIR}/rollback/restored_container.env" || ok=1
    {
      write_env_line RESTORED_CONTAINER_ID "$current_id"
      write_env_line RESTORED_CONTAINER_IMAGE "$current_image"
      write_env_line RESTORED_CONTAINER_RUNNING "$current_running"
      write_env_line RESTORED_CONTAINER_CONFIG_IMAGE "$current_config_image"
      write_env_line RESTORED_CONTAINER_CONFIG_SHA256 "$current_config_sha256"
      write_env_line RESTORED_CONTAINER_HOSTCONFIG_SHA256 "$current_hostconfig_sha256"
      write_env_line RESTORED_CONTAINER_PORT_BINDINGS_JSON "$current_port_bindings_json"
    } > "${RECEIPT_TMP_DIR}/rollback/restored_container_state.env"
  else
    if container_exists "$CONTAINER_NAME"; then
      printf 'unexpected original container exists after rollback\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
      ok=1
    fi
    printf 'ORIGINAL_CONTAINER_ABSENT=YES\n' > "${RECEIPT_TMP_DIR}/rollback/no_original_container.env"
  fi
  return "$ok"
}

rollback_network_if_needed() {
  local ok=0
  if [[ "$NETWORK_CREATED" == "1" ]]; then
    if network_exists "$NETWORK_NAME"; then
      local endpoints
      endpoints="$(docker network inspect "$NETWORK_NAME" --format '{{ len .Containers }}')" || ok=1
      write_env_line NETWORK_ENDPOINTS_BEFORE_REMOVE "$endpoints" > "${RECEIPT_TMP_DIR}/rollback/network_remove.env"
      if [[ "$endpoints" == "0" ]]; then
        docker network rm "$NETWORK_NAME" > "${RECEIPT_TMP_DIR}/rollback/network_rm.stdout" 2> "${RECEIPT_TMP_DIR}/rollback/network_rm.stderr" || ok=1
      else
        printf 'created network still has endpoints\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
        ok=1
      fi
    fi
    if network_exists "$NETWORK_NAME"; then
      printf 'created network still exists after rollback\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
      ok=1
    fi
  fi
  return "$ok"
}

rollback() {
  local ok=0
  mkdir -p -- "${RECEIPT_TMP_DIR}/rollback"
  if container_exists "$CONTAINER_NAME"; then
    local live_id
    local live_project=""
    local live_service=""
    local remove_allowed=0
    live_id="$(container_field "$CONTAINER_NAME" '{{ .Id }}')" || ok=1
    if [[ "$OLD_CONTAINER_EXISTS" == "1" && "$live_id" == "$OLD_CONTAINER_ID" && "$OLD_RENAMED" == "0" ]]; then
      :
    else
      if [[ -n "$NEW_CONTAINER_ID" && "$live_id" == "$NEW_CONTAINER_ID" ]]; then
        remove_allowed=1
      elif [[ -z "$NEW_CONTAINER_ID" ]]; then
        live_project="$(container_field "$CONTAINER_NAME" '{{ index .Config.Labels "com.docker.compose.project" }}')" || ok=1
        live_service="$(container_field "$CONTAINER_NAME" '{{ index .Config.Labels "com.docker.compose.service" }}')" || ok=1
        if [[ "$live_project" == "$COMPOSE_PROJECT_NAME" && "$live_service" == "$CONTAINER_NAME" ]]; then
          remove_allowed=1
        fi
      fi
      if [[ "$remove_allowed" == "1" ]]; then
        capture_container_allowlist "$CONTAINER_NAME" "${RECEIPT_TMP_DIR}/rollback/new_container_before_rm.env" || ok=1
        docker rm -f "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/rollback/new_container_rm.stdout" 2> "${RECEIPT_TMP_DIR}/rollback/new_container_rm.stderr" || ok=1
      else
        printf 'refusing to remove container not proven to belong to this apply run\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
        ok=1
      fi
    fi
  fi

  if [[ "$OLD_CONTAINER_EXISTS" == "1" ]]; then
    if ! container_exists "$CONTAINER_NAME"; then
      if container_exists "$OLD_ROLLBACK_NAME"; then
        local rollback_id
        rollback_id="$(container_field "$OLD_ROLLBACK_NAME" '{{ .Id }}')" || ok=1
        if [[ "$rollback_id" == "$OLD_CONTAINER_ID" ]]; then
          if docker rename "$OLD_ROLLBACK_NAME" "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/rollback/old_container_rename_back.stdout" 2> "${RECEIPT_TMP_DIR}/rollback/old_container_rename_back.stderr"; then
            OLD_RENAMED=0
          else
            ok=1
          fi
        else
          printf 'rollback container ID mismatch\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
          ok=1
        fi
      else
        printf 'rollback container not found\n' >> "${RECEIPT_TMP_DIR}/rollback/errors.log"
        ok=1
      fi
    fi

    if container_exists "$CONTAINER_NAME" && [[ "$(container_field "$CONTAINER_NAME" '{{ .Id }}')" == "$OLD_CONTAINER_ID" ]]; then
      local restored_running
      restored_running="$(container_field "$CONTAINER_NAME" '{{ .State.Running }}')" || ok=1
      if [[ "$OLD_CONTAINER_WAS_RUNNING" == "true" && "$restored_running" != "true" ]]; then
        docker start "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/rollback/old_container_start.stdout" 2> "${RECEIPT_TMP_DIR}/rollback/old_container_start.stderr" || ok=1
      fi
      if [[ "$OLD_CONTAINER_WAS_RUNNING" != "true" && "$restored_running" == "true" ]]; then
        docker stop "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/rollback/old_container_stop.stdout" 2> "${RECEIPT_TMP_DIR}/rollback/old_container_stop.stderr" || ok=1
      fi
    fi
  fi

  rollback_verify_old_container || ok=1
  rollback_network_if_needed || ok=1
  capture_listeners "${RECEIPT_TMP_DIR}/rollback" || ok=1
  local rollback_listener_8088="NO"
  local rollback_listener_8089="NO"
  listener_exists 8088 && rollback_listener_8088="YES"
  listener_exists 8089 && rollback_listener_8089="YES"
  {
    write_env_line PRE_LISTENER_8088 "$PRE_LISTENER_8088"
    write_env_line ROLLBACK_LISTENER_8088 "$rollback_listener_8088"
    write_env_line PRE_LISTENER_8089 "$PRE_LISTENER_8089"
    write_env_line ROLLBACK_LISTENER_8089 "$rollback_listener_8089"
  } > "${RECEIPT_TMP_DIR}/rollback/listener_restore.env"
  [[ "$rollback_listener_8088" == "$PRE_LISTENER_8088" ]] || ok=1
  [[ "$rollback_listener_8089" == "$PRE_LISTENER_8089" ]] || ok=1
  return "$ok"
}

on_error() {
  local exit_code="${1:-1}"
  local line_no="${2:-unknown}"
  local command_text="${3:-unknown}"
  if [[ "$FAILURE_HANDLING" == "1" ]]; then
    exit "$exit_code"
  fi
  FAILURE_HANDLING=1
  trap - ERR INT TERM HUP
  set +e
  if [[ -z "$ERROR_MESSAGE" ]]; then
    ERROR_MESSAGE="command failed at line ${line_no}: ${command_text}"
  fi
  if [[ -n "$RECEIPT_TMP_DIR" && -d "$RECEIPT_TMP_DIR" ]]; then
    mkdir -p -- "${RECEIPT_TMP_DIR}/rollback"
    {
      write_env_line EXIT_CODE "$exit_code"
      write_env_line ERROR_MESSAGE "$ERROR_MESSAGE"
      write_env_line FAILED_LINE "$line_no"
      write_env_line FAILED_COMMAND "$command_text"
    } > "${RECEIPT_TMP_DIR}/rollback/failure.env"
  fi

  if [[ "$EFFECT_STARTED" == "1" && -n "$RECEIPT_TMP_DIR" && -d "$RECEIPT_TMP_DIR" ]]; then
    if rollback; then
      FINAL_STATUS="HOLD_ROLLED_BACK"
    else
      FINAL_STATUS="HOLD_ROLLBACK_INCOMPLETE"
    fi
  else
    if [[ -z "$FINAL_STATUS" ]]; then
      FINAL_STATUS="HOLD_BEFORE_EFFECT"
    fi
  fi

  if [[ -n "$RECEIPT_TMP_DIR" && -d "$RECEIPT_TMP_DIR" ]]; then
    if ! publish_receipt "$FINAL_STATUS"; then
      printf '%s\n' "$FINAL_STATUS"
      printf 'RECEIPT_PUBLISH_FAILED=YES\n'
      exit "$exit_code"
    fi
    printf '%s\n' "$FINAL_STATUS"
    printf 'RECEIPT=%s/summary.env\n' "$RECEIPT_DIR"
  else
    printf '%s\n' "$FINAL_STATUS"
  fi
  exit "$exit_code"
}

on_signal() {
  local signal_name="$1"
  ERROR_MESSAGE="received signal ${signal_name}"
  on_error 128 signal "$signal_name"
}

trap cleanup_tmp_receipt EXIT
trap 'on_error $? ${LINENO} "$BASH_COMMAND"' ERR
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM
trap 'on_signal HUP' HUP

require_command awk
require_command date
require_command docker
require_command find
require_command flock
require_command git
require_command mkdir
require_command mktemp
require_command mv
require_command rm
require_command sed
require_command sha256sum
require_command sleep
require_command sort
require_command ss
require_command tr

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
ROOT_PHYSICAL="$(cd "$ROOT" && pwd -P)"
RECEIPT_ROOT="${ROOT}/${RECEIPT_ROOT_REL}"

docker compose version >/dev/null 2>&1 || die "missing required command: docker compose"

[[ "${APPLY_DOMAIN_GATEWAY:-}" == "YES" ]] || die "APPLY_DOMAIN_GATEWAY=YES is required"
[[ -n "${SOURCE_HEAD:-}" ]] || die "SOURCE_HEAD is required"
[[ -n "${WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256:-}" ]] || die "WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256 is required"
[[ "$SOURCE_HEAD" =~ ^[0-9a-f]{40}$ ]] || die "SOURCE_HEAD must be exactly 40 lowercase hexadecimal characters"
[[ "$WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256 must be 64 lowercase hex characters"

HEAD_BEFORE="$(current_head)"
[[ "$SOURCE_HEAD" == "$HEAD_BEFORE" ]] || die "SOURCE_HEAD must equal the executing HEAD"

for rel in "$COMPOSE_FILE_REL" "$APPLY_FILE_REL" "$DOCKERFILE_REL" "$DEFAULT_CONF_REL"; do
  git -C "$ROOT" cat-file -e "${SOURCE_HEAD}:${rel}" || die "${rel} is missing from SOURCE_HEAD"
  [[ -f "${ROOT}/${rel}" ]] || die "${rel} is missing from the working tree"
done

git -C "$ROOT" diff --quiet -- "$COMPOSE_FILE_REL" "$APPLY_FILE_REL" "$DOCKERFILE_REL" "$DEFAULT_CONF_REL" || die "compose/apply/Dockerfile/default.conf have unstaged diff"
git -C "$ROOT" diff --cached --quiet -- "$COMPOSE_FILE_REL" "$APPLY_FILE_REL" "$DOCKERFILE_REL" "$DEFAULT_CONF_REL" || die "compose/apply/Dockerfile/default.conf have staged diff"

STATUS_HASH_BEFORE="$(git_status_hash)"
assert_source_head_stable "after source checks"

SOURCE_COMPOSE_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:${COMPOSE_FILE_REL}" | sha256_stdin)"
SOURCE_APPLY_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:${APPLY_FILE_REL}" | sha256_stdin)"
SOURCE_DOCKERFILE_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:${DOCKERFILE_REL}" | sha256_stdin)"
SOURCE_DEFAULT_CONF_SHA256="$(git -C "$ROOT" show "${SOURCE_HEAD}:${DEFAULT_CONF_REL}" | sha256_stdin)"
TARGET_IMAGE_ID="sha256:${WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256}"

git -C "$ROOT" check-ignore -q -- "$RECEIPT_ROOT_REL" || die "receipt root must be ignored by git: ${RECEIPT_ROOT_REL}"

current_path="$ROOT"
IFS='/' read -r -a receipt_parts <<< "$RECEIPT_ROOT_REL"
for part in "${receipt_parts[@]}"; do
  current_path="${current_path}/${part}"
  [[ ! -L "$current_path" ]] || die "receipt path contains symlink before mkdir: ${current_path}"
  if [[ -e "$current_path" ]]; then
    [[ -d "$current_path" ]] || die "receipt path layer is not a directory: ${current_path}"
  else
    mkdir -- "$current_path"
  fi
  [[ ! -L "$current_path" ]] || die "receipt path contains symlink after mkdir: ${current_path}"
done

RECEIPT_ROOT_PHYSICAL="$(cd "$RECEIPT_ROOT" && pwd -P)"
[[ "$RECEIPT_ROOT_PHYSICAL" == "${ROOT_PHYSICAL}/${RECEIPT_ROOT_REL}" ]] || die "receipt root realpath escaped repo"

exec {LOCK_FD}> "${RECEIPT_ROOT}/.apply.lock"
flock -n "$LOCK_FD" || die "another domain gateway apply is already running"

if [[ -n "${RUN_ID:-}" ]]; then
  [[ "$RUN_ID" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || die "RUN_ID must be 1-64 letters, numbers, dots, underscores, or hyphens"
else
  RUN_ID="$(date -u +%Y%m%dt%H%M%Sz)-${SOURCE_HEAD:0:12}-${STATUS_HASH_BEFORE:0:12}"
fi

RECEIPT_DIR="${RECEIPT_ROOT}/${RUN_ID}"
[[ ! -e "$RECEIPT_DIR" && ! -L "$RECEIPT_DIR" ]] || die "receipt RUN_ID directory already exists: ${RUN_ID}"
RECEIPT_TMP_DIR="$(mktemp -d "${RECEIPT_ROOT}/.domain-gateway-apply.${RUN_ID}.XXXXXXXXXX")"
: > "${RECEIPT_TMP_DIR}/.domain_gateway_apply_tmp.marker"
mkdir -p -- "${RECEIPT_TMP_DIR}/pre" "${RECEIPT_TMP_DIR}/post" "${RECEIPT_TMP_DIR}/rollback"

project_token="$(printf '%s' "$RUN_ID" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-')"
project_token="$(printf '%s' "$project_token" | sed 's/^-*//; s/-*$//')"
if [[ -z "$project_token" || ! "$project_token" =~ ^[a-z0-9] ]]; then
  project_token="run-${SOURCE_HEAD:0:12}"
fi
COMPOSE_PROJECT_NAME="wuchang-domain-gateway-apply-${project_token}"
OLD_ROLLBACK_NAME="${CONTAINER_NAME}-rollback-${RUN_ID}"

capture_image_allowlist "$TARGET_IMAGE_ID" "${RECEIPT_TMP_DIR}/pre/target_image.env"
INSPECTED_TARGET_IMAGE_ID="$(docker image inspect "$TARGET_IMAGE_ID" --format '{{ .Id }}')"
[[ "$INSPECTED_TARGET_IMAGE_ID" == "$TARGET_IMAGE_ID" ]] || die "target image ID does not exactly match ${TARGET_IMAGE_ID}"
assert_image_label "org.opencontainers.image.revision" "$SOURCE_HEAD"
assert_image_label "life.wuchang.domain_gateway.source_head" "$SOURCE_HEAD"
assert_image_label "life.wuchang.domain_gateway.source.dockerfile_sha256" "$SOURCE_DOCKERFILE_SHA256"
assert_image_label "life.wuchang.domain_gateway.source.default_conf_sha256" "$SOURCE_DEFAULT_CONF_SHA256"
assert_image_label "life.wuchang.domain_gateway.release.default_conf_sha256" "$SOURCE_DEFAULT_CONF_SHA256"

{
  write_env_line SOURCE_COMPOSE_SHA256 "$SOURCE_COMPOSE_SHA256"
  write_env_line SOURCE_APPLY_SHA256 "$SOURCE_APPLY_SHA256"
  write_env_line SOURCE_DOCKERFILE_SHA256 "$SOURCE_DOCKERFILE_SHA256"
  write_env_line SOURCE_DEFAULT_CONF_SHA256 "$SOURCE_DEFAULT_CONF_SHA256"
  write_env_line TARGET_IMAGE_ID "$TARGET_IMAGE_ID"
} > "${RECEIPT_TMP_DIR}/pre/source_hashes.env"

if container_exists "$CONTAINER_NAME"; then
  OLD_CONTAINER_EXISTS=1
  OLD_CONTAINER_ID="$(container_field "$CONTAINER_NAME" '{{ .Id }}')"
  OLD_CONTAINER_IMAGE="$(container_field "$CONTAINER_NAME" '{{ .Image }}')"
  OLD_CONTAINER_CONFIG_IMAGE="$(container_field "$CONTAINER_NAME" '{{ .Config.Image }}')"
  OLD_CONTAINER_WAS_RUNNING="$(container_field "$CONTAINER_NAME" '{{ .State.Running }}')"
  OLD_CONTAINER_HEALTH="$(container_field "$CONTAINER_NAME" '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}none{{ end }}')"
  OLD_CONTAINER_CONFIG_SHA256="$(container_field "$CONTAINER_NAME" '{{ json .Config }}' | sha256_stdin)"
  OLD_CONTAINER_HOSTCONFIG_SHA256="$(container_field "$CONTAINER_NAME" '{{ json .HostConfig }}' | sha256_stdin)"
  OLD_CONTAINER_PORT_BINDINGS_JSON="$(container_field "$CONTAINER_NAME" '{{ json .HostConfig.PortBindings }}')"
  capture_container_allowlist "$CONTAINER_NAME" "${RECEIPT_TMP_DIR}/pre/old_container.env"
  capture_image_allowlist "$OLD_CONTAINER_IMAGE" "${RECEIPT_TMP_DIR}/pre/old_image.env"
else
  printf 'PRESENT=NO\n' > "${RECEIPT_TMP_DIR}/pre/old_container.env"
  printf 'PRESENT=NO\n' > "${RECEIPT_TMP_DIR}/pre/old_image.env"
fi

{
  write_env_line OLD_CONTAINER_EXISTS "$OLD_CONTAINER_EXISTS"
  write_env_line OLD_CONTAINER_ID "$OLD_CONTAINER_ID"
  write_env_line OLD_CONTAINER_IMAGE "$OLD_CONTAINER_IMAGE"
  write_env_line OLD_CONTAINER_CONFIG_IMAGE "$OLD_CONTAINER_CONFIG_IMAGE"
  write_env_line OLD_CONTAINER_WAS_RUNNING "$OLD_CONTAINER_WAS_RUNNING"
  write_env_line OLD_CONTAINER_HEALTH "$OLD_CONTAINER_HEALTH"
  write_env_line OLD_CONTAINER_CONFIG_SHA256 "$OLD_CONTAINER_CONFIG_SHA256"
  write_env_line OLD_CONTAINER_HOSTCONFIG_SHA256 "$OLD_CONTAINER_HOSTCONFIG_SHA256"
  write_env_line OLD_CONTAINER_PORT_BINDINGS_JSON "$OLD_CONTAINER_PORT_BINDINGS_JSON"
} > "${RECEIPT_TMP_DIR}/pre/old_container_state.env"

if [[ "$OLD_CONTAINER_EXISTS" == "1" ]] && container_exists "$OLD_ROLLBACK_NAME"; then
  FINAL_STATUS="HOLD_ROLLBACK_NAME_EXISTS"
  die "rollback container name already exists: ${OLD_ROLLBACK_NAME}"
fi

capture_listeners "${RECEIPT_TMP_DIR}/pre"
PRE_LISTENER_8088=NO
PRE_LISTENER_8089=NO
listener_exists 8088 && PRE_LISTENER_8088=YES
listener_exists 8089 && PRE_LISTENER_8089=YES

if network_exists "$NETWORK_NAME"; then
  capture_network_allowlist "$NETWORK_NAME" "${RECEIPT_TMP_DIR}/pre/network.env"
  [[ "$(network_internal "$NETWORK_NAME")" == "true" ]] || die "existing fixed network is not internal: ${NETWORK_NAME}"
else
  printf 'PRESENT=NO\n' > "${RECEIPT_TMP_DIR}/pre/network.env"
fi

COMPOSE_CONFIG_SHA256="$(
  cd "$ROOT"
  WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256="$WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256" docker compose -f "$COMPOSE_FILE_REL" config | sha256_stdin
)"
write_env_line COMPOSE_CONFIG_SHA256 "$COMPOSE_CONFIG_SHA256" > "${RECEIPT_TMP_DIR}/pre/compose_config.env"

if [[ "$PRE_LISTENER_8089" == "YES" ]]; then
  if [[ "$OLD_CONTAINER_EXISTS" == "1" && "$OLD_CONTAINER_WAS_RUNNING" == "true" ]] && container_owns_host_port "$CONTAINER_NAME" 8089; then
    OLD_CONTAINER_OWNS_8089=1
  else
    FINAL_STATUS="HOLD_PRE_EFFECT_FOREIGN_8089_LISTENER"
    die "8089 listener is not owned by the old gateway container"
  fi
fi
{
  write_env_line PRE_LISTENER_8088 "$PRE_LISTENER_8088"
  write_env_line PRE_LISTENER_8089 "$PRE_LISTENER_8089"
  write_env_line OLD_CONTAINER_OWNS_8089 "$OLD_CONTAINER_OWNS_8089"
} > "${RECEIPT_TMP_DIR}/pre/listener_ownership.env"

HEAD_BEFORE_EFFECT="$(current_head)"
STATUS_HASH_BEFORE_EFFECT="$(git_status_hash)"
[[ "$HEAD_BEFORE_EFFECT" == "$SOURCE_HEAD" ]] || die "SOURCE_HEAD drifted before effect"
[[ "$STATUS_HASH_BEFORE_EFFECT" == "$STATUS_HASH_BEFORE" ]] || die "git status hash drifted before effect"

if ! network_exists "$NETWORK_NAME"; then
  EFFECT_STARTED=1
  docker network create --internal "$NETWORK_NAME" > "${RECEIPT_TMP_DIR}/pre/network_create.stdout" 2> "${RECEIPT_TMP_DIR}/pre/network_create.stderr"
  NETWORK_CREATED=1
  capture_network_allowlist "$NETWORK_NAME" "${RECEIPT_TMP_DIR}/pre/network_after_create.env"
  [[ "$(network_internal "$NETWORK_NAME")" == "true" ]] || die "created network is not internal: ${NETWORK_NAME}"
fi

if [[ "$OLD_CONTAINER_EXISTS" == "1" ]]; then
  EFFECT_STARTED=1
  if [[ "$OLD_CONTAINER_WAS_RUNNING" == "true" ]]; then
    docker stop "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/pre/old_container_stop.stdout" 2> "${RECEIPT_TMP_DIR}/pre/old_container_stop.stderr"
  fi
  docker rename "$CONTAINER_NAME" "$OLD_ROLLBACK_NAME" > "${RECEIPT_TMP_DIR}/pre/old_container_rename.stdout" 2> "${RECEIPT_TMP_DIR}/pre/old_container_rename.stderr"
  OLD_RENAMED=1
fi

if [[ "$OLD_CONTAINER_OWNS_8089" == "1" ]] && listener_exists 8089; then
  FINAL_STATUS="HOLD_OLD_GATEWAY_8089_NOT_RELEASED"
  die "old gateway container did not release 8089 after stop and rename"
fi

EFFECT_STARTED=1
(
  cd "$ROOT"
  WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256="$WUCHANG_DOMAIN_GATEWAY_IMAGE_SHA256" \
  COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" \
    docker compose -f "$COMPOSE_FILE_REL" up -d --no-build --pull never --force-recreate --no-deps "$CONTAINER_NAME"
) > "${RECEIPT_TMP_DIR}/post/compose.up.stdout" 2> "${RECEIPT_TMP_DIR}/post/compose.up.stderr"

NEW_CONTAINER_ID="$(container_field "$CONTAINER_NAME" '{{ .Id }}')"
new_image="$(container_field "$CONTAINER_NAME" '{{ .Image }}')"
[[ "$new_image" == "$TARGET_IMAGE_ID" ]] || die "new container image does not match target image ID"
[[ "$(container_field "$CONTAINER_NAME" '{{ .State.Running }}')" == "true" ]] || die "new container is not running"

deadline=$((SECONDS + 60))
health_status=""
while (( SECONDS <= deadline )); do
  health_status="$(container_field "$CONTAINER_NAME" '{{ if .State.Health }}{{ .State.Health.Status }}{{ else }}none{{ end }}')"
  [[ "$health_status" == "healthy" ]] && break
  sleep 2
done
[[ "$health_status" == "healthy" ]] || die "new container health did not become healthy within 60 seconds"

[[ "$(container_field "$CONTAINER_NAME" '{{ .Config.User }}')" == "101:101" ]] || die "new container Config.User mismatch"
[[ "$(container_field "$CONTAINER_NAME" '{{ .HostConfig.ReadonlyRootfs }}')" == "true" ]] || die "new container ReadonlyRootfs mismatch"
[[ "$(container_field "$CONTAINER_NAME" '{{ json .HostConfig.CapDrop }}')" == '["ALL"]' ]] || die "new container CapDrop mismatch"
[[ "$(container_field "$CONTAINER_NAME" '{{ json .HostConfig.SecurityOpt }}')" == '["no-new-privileges:true"]' ]] || die "new container SecurityOpt mismatch"
[[ "$(container_field "$CONTAINER_NAME" '{{ .HostConfig.Privileged }}')" == "false" ]] || die "new container Privileged mismatch"

bind_mounts="$(container_field "$CONTAINER_NAME" '{{ range .Mounts }}{{ if eq .Type "bind" }}bind{{ println }}{{ end }}{{ end }}')"
[[ -z "$bind_mounts" ]] || die "new container has bind mounts"

network_names="$(container_field "$CONTAINER_NAME" '{{ range $k, $_ := .NetworkSettings.Networks }}{{ println $k }}{{ end }}' | LC_ALL=C sort)"
[[ "$network_names" == "$NETWORK_NAME" ]] || die "new container is not attached only to ${NETWORK_NAME}"
[[ "$(network_internal "$NETWORK_NAME")" == "true" ]] || die "new container network is not internal"

expected_ports_json='{"8088/tcp":[{"HostIp":"127.0.0.1","HostPort":"8088"}]}'
[[ "$(container_field "$CONTAINER_NAME" '{{ json .HostConfig.PortBindings }}')" == "$expected_ports_json" ]] || die "new container HostConfig port bindings mismatch"
[[ "$(container_field "$CONTAINER_NAME" '{{ json .NetworkSettings.Ports }}')" == "$expected_ports_json" ]] || die "new container NetworkSettings ports mismatch"

capture_listeners "${RECEIPT_TMP_DIR}/post"
listener_exists 8088 || die "8088 listener missing after apply"
if listener_exists 8089; then
  die "8089 listener exists after apply"
fi

capture_container_allowlist "$CONTAINER_NAME" "${RECEIPT_TMP_DIR}/post/new_container.env"
docker port "$CONTAINER_NAME" > "${RECEIPT_TMP_DIR}/post/new_container.ports.txt"

if [[ "$OLD_RENAMED" == "1" ]]; then
  capture_container_allowlist "$OLD_ROLLBACK_NAME" "${RECEIPT_TMP_DIR}/post/old_rollback_container.env"
  [[ "$(container_field "$OLD_ROLLBACK_NAME" '{{ .State.Running }}')" == "false" ]] || die "old rollback container is not stopped"
  {
    write_env_line OLD_ROLLBACK_CONTAINER_RETAINED YES
    write_env_line OLD_ROLLBACK_NAME "$OLD_ROLLBACK_NAME"
    write_env_line OLD_ROLLBACK_ID "$(container_field "$OLD_ROLLBACK_NAME" '{{ .Id }}')"
  } > "${RECEIPT_TMP_DIR}/post/old_rollback_asset.env"
else
  printf 'OLD_ROLLBACK_CONTAINER_RETAINED=NO\n' > "${RECEIPT_TMP_DIR}/post/old_rollback_asset.env"
fi

HEAD_AFTER_EFFECT="$(current_head)"
STATUS_HASH_AFTER_EFFECT="$(git_status_hash)"
[[ "$HEAD_AFTER_EFFECT" == "$SOURCE_HEAD" ]] || die "SOURCE_HEAD drifted after effect"
[[ "$STATUS_HASH_AFTER_EFFECT" == "$STATUS_HASH_BEFORE" ]] || die "git status hash drifted after effect"

assert_status_and_head_stable "before receipt"
publish_receipt "APPLY_DOMAIN_GATEWAY_APPLIED"

printf 'APPLY_DOMAIN_GATEWAY_APPLIED\n'
printf 'RECEIPT=%s/summary.env\n' "$RECEIPT_DIR"
