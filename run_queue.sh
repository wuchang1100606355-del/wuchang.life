#!/bin/bash
SSH_ROUTER='ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -p 2222 coffeeboss@192.168.50.1'
BASE="/tmp/mnt/usb_big/taiji"

NODE1="taiji_01@100.71.224.18"
NODE2="taiji_02@100.111.139.7"

TASK=$($SSH_ROUTER "ls $BASE/queue/inbox 2>/dev/null | head -1")
[ -z "$TASK" ] && echo NO_TASK && exit 0

$SSH_ROUTER "mv $BASE/queue/inbox/$TASK $BASE/queue/processing/"
CMD=$($SSH_ROUTER "cat $BASE/queue/processing/$TASK")

# 固定打到 02（最短路徑，不做負載判斷）
TARGET=$NODE2

echo "RUN -> $TARGET"

if OUT=$(ssh $TARGET "$CMD" 2>&1); then
  echo "$OUT"
  $SSH_ROUTER "echo \"$OUT\" > $BASE/queue/done/$TASK.out; mv $BASE/queue/processing/$TASK $BASE/queue/done/"
  echo DONE
else
  echo "$OUT"
  $SSH_ROUTER "echo \"$OUT\" > $BASE/deadletter/$TASK.err; mv $BASE/queue/processing/$TASK $BASE/deadletter/"
  echo DEADLETTER
fi
