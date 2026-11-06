#!/bin/sh
# P2a resumable safety coordinator. No model until the P2b/P2c increments.
set -eu
if [ -n "${DATAMATE_PREDICT_CONFIG:-}" ]; then
  exec datamate predict --input "${DATAMATE_INPUT_DIR:-/data}" --output "${DATAMATE_OUTPUT_DIR:-/result}" --config "$DATAMATE_PREDICT_CONFIG"
fi
exec datamate predict --input "${DATAMATE_INPUT_DIR:-/data}" --output "${DATAMATE_OUTPUT_DIR:-/result}"
