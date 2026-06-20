#!/bin/bash
# W7TP Cloud Service Account Dry-Run Validation Probe
# Enforces zero token leakage and stateless verification.

echo "STATE=TOTAL_FIELD_SERVICE_ACCOUNT_DRYRUN_START"

proj=$(gcloud config get-value project 2>/dev/null)
acct=$(gcloud config get-value account 2>/dev/null)
sa=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null)

if [ -z "$proj" ] || [ "$proj" = "(unset)" ]; then
  echo "STATE=HOLD_NO_GCLOUD_PROJECT"
  exit 1
fi

if [ -z "$sa" ] || [ "$sa" = "(unset)" ]; then
  echo "STATE=HOLD_NO_IMPERSONATE_SERVICE_ACCOUNT_CONFIGURED"
  exit 2
fi

# Execute dry-run (describe project) via impersonation. Stderr is blackholed.
pid=$(gcloud projects describe "$proj" --impersonate-service-account="$sa" --format="value(projectId)" 2>/dev/null || true)

if [ "$pid" != "$proj" ]; then
  echo "STATE=FAIL_SERVICE_ACCOUNT_PROJECT_DESCRIBE_DRYRUN"
  exit 3
fi

# Output absolute safe state
echo "STATE=PASS_TOTAL_FIELD_PREFIX_CLOUD_COMPUTE_REPLY_READONLY token_print=false key_read=false api_enable=false deploy=false restart=false db_write=false cloud_compute_called=false"
