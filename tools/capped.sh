#!/bin/bash
# Run a command and kill it (and everything it started) if their memory together passes CAP_GB.
# Usage: capped.sh CAP_GB cmd...
cap=$1; shift
"$@" &
pid=$!
tree() { local p=$1; echo $p; for c in $(pgrep -P $p); do tree $c; done; }
while kill -0 $pid 2>/dev/null; do
  pids=$(tree $pid | tr '\n' ' ')
  kb=$(ps -o rss= -p ${pids// /,} 2>/dev/null | awk '{s+=$1} END {print s+0}')
  if [ "$kb" -gt $((cap * 1048576)) ]; then
    echo "capped.sh: killed $pid and its children at $((kb / 1024)) MB (cap ${cap} GB)" >&2
    kill $pids 2>/dev/null; wait $pid 2>/dev/null; exit 137
  fi
  sleep 1
done
wait $pid
