#!/bin/bash
set -euo pipefail

if [ "${TAIJI_ALLOW_LEGACY_REMOTE_QUEUE:-false}" != "true" ]; then
  echo "blocked: legacy remote queue runner uses SSH and remote command execution."
  echo "Use manifest/preflight/metric-governed execution instead."
  exit 2
fi

SSH_ROUTER='ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -p 2222 coffeeboss@192.168.50.1'
BASE="/tmp/mnt/usb_big/taiji"
NODE1="taiji_01@100.71.224.18"
NODE2="taiji_02@100.111.139.7"

$SSH_ROUTER "mkdir -p $BASE/queue/inbox $BASE/queue/processing $BASE/queue/done $BASE/deadletter"

while true; do
  TASK=$($SSH_ROUTER "ls $BASE/queue/inbox 2>/dev/null | head -1")
  [ -z "$TASK" ] && sleep 2 && continue

  $SSH_ROUTER "mv $BASE/queue/inbox/$TASK $BASE/queue/processing/"
  CMD=$($SSH_ROUTER "cat $BASE/queue/processing/$TASK")

  LOAD1=$(ssh $NODE1 "uptime | awk -F'load average:' '{print \$2}' | cut -d',' -f1")
  LOAD2=$(ssh $NODE2 "uptime | awk -F'load average:' '{print \$2}' | cut -d',' -f1")

  if (( $(echo "$LOAD1 < $LOAD2" | bc -l) )); then
    TARGET=$NODE1
  else
    TARGET=$NODE2
  fi

  if OUT=$(ssh $TARGET "$CMD" 2>&1); then
    $SSH_ROUTER "echo \"$OUT\" > $BASE/queue/done/$TASK.out; mv $BASE/queue/processing/$TASK $BASE/queue/done/"
  else
    $SSH_ROUTER "echo \"$OUT\" > $BASE/deadletter/$TASK.err; mv $BASE/queue/processing/$TASK $BASE/deadletter/"
  fi

done
