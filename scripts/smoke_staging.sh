#!/usr/bin/env bash
set -euo pipefail

web_url="${1:?staging web URL is required}"
api_url="${2:?staging API URL is required}"
web_url="${web_url%/}"
api_url="${api_url%/}"

curl_args=(--fail --silent --show-error --retry 10 --retry-delay 3 --retry-all-errors)

health_body="$(curl "${curl_args[@]}" "${api_url}/health")"
if [[ "$health_body" != *'"status":"ok"'* ]]; then
  echo "staging API liveness response is invalid" >&2
  exit 1
fi

readiness_body="$(curl "${curl_args[@]}" "${api_url}/ready")"
if [[ "$readiness_body" != *'"status":"ready"'* ]]; then
  echo "staging API readiness response is invalid" >&2
  exit 1
fi

curl "${curl_args[@]}" "$web_url" >/dev/null
echo "staging smoke test passed"
