#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-}"
image_tag="${2:-}"
registry_namespace="${3:-}"
staging_root="${STAGING_ROOT:-/opt/uzbekistan-os}"
compose_file="${staging_root}/docker-compose.staging.yml"
runtime_env="${staging_root}/.env"
release_env="${staging_root}/.release.env"
previous_env="${staging_root}/.release.previous.env"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "required staging file is missing: $1" >&2
    exit 1
  fi
}

write_release() {
  local target="$1"
  local tag="$2"
  local namespace="$3"
  umask 077
  {
    printf 'IMAGE_TAG=%s\n' "$tag"
    printf 'API_IMAGE=%s/uzbekistan-os-api:%s\n' "$namespace" "$tag"
    printf 'WEB_IMAGE=%s/uzbekistan-os-web:%s\n' "$namespace" "$tag"
    printf 'WORKER_IMAGE=%s/uzbekistan-os-worker:%s\n' "$namespace" "$tag"
  } >"$target"
}

compose() {
  local selected_release="$1"
  shift
  docker compose \
    --env-file "$runtime_env" \
    --env-file "$selected_release" \
    -f "$compose_file" \
    "$@"
}

activate_release() {
  local selected_release="$1"
  compose "$selected_release" pull
  compose "$selected_release" up -d postgres redis minio
  compose "$selected_release" run --rm migrate

  local object_store_ready=false
  for _ in {1..20}; do
    if compose "$selected_release" run --rm object-store-init; then
      object_store_ready=true
      break
    fi
    sleep 3
  done
  if [[ "$object_store_ready" != "true" ]]; then
    echo "object storage did not become ready" >&2
    return 1
  fi

  compose "$selected_release" run --rm registry-sync
  compose "$selected_release" up -d api worker scheduler web

  local api_port
  api_port="$(sed -n 's/^STAGING_API_PORT=//p' "$runtime_env" | tail -1)"
  api_port="${api_port:-8000}"
  local api_ready=false
  for _ in {1..30}; do
    if curl --fail --silent --show-error "http://127.0.0.1:${api_port}/ready" >/dev/null; then
      api_ready=true
      break
    fi
    sleep 2
  done
  if [[ "$api_ready" != "true" ]]; then
    echo "staging API readiness check failed" >&2
    return 1
  fi
}

require_file "$compose_file"
require_file "$runtime_env"

case "$command_name" in
deploy)
  if [[ ! "$image_tag" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "image tag contains unsupported characters" >&2
    exit 1
  fi
  if [[ ! "$registry_namespace" =~ ^ghcr\.io/[a-z0-9-]+$ ]]; then
    echo "registry namespace must be a lowercase GHCR owner path" >&2
    exit 1
  fi
  candidate_env="${staging_root}/.release.candidate.env"
  trap 'rm -f "${candidate_env:-}"' EXIT
  write_release "$candidate_env" "$image_tag" "$registry_namespace"
  if [[ -f "$release_env" ]]; then
    cp "$release_env" "$previous_env"
  fi
  activate_release "$candidate_env"
  cp "$candidate_env" "$release_env"
  ;;
rollback)
  require_file "$release_env"
  require_file "$previous_env"
  failed_env="${staging_root}/.release.failed.env"
  cp "$release_env" "$failed_env"
  activate_release "$previous_env"
  cp "$previous_env" "$release_env"
  cp "$failed_env" "$previous_env"
  rm -f "$failed_env"
  ;;
*)
  echo "usage: deploy_staging.sh deploy <image-tag> <ghcr-namespace> | rollback" >&2
  exit 2
  ;;
esac
