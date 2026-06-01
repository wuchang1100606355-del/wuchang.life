#!/bin/bash
SSH='ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -p 2222 coffeeboss@192.168.50.1'
BASE="/tmp/mnt/usb_big/taiji"

TASK=$($SSH "ls $BASE/queue/inbox 2>/dev/null | head -1")
[ -z "$TASK" ] && echo NO_TASK && exit 0

$SSH "mv $BASE/queue/inbox/$TASK $BASE/queue/processing/"
CMD=$($SSH "cat $BASE/queue/processing/$TASK")
bash -c "$CMD"
$SSH "mv $BASE/queue/processing/$TASK $BASE/queue/done/"
echo DONE
