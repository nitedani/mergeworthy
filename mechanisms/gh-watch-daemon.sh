#!/bin/bash
# Keeps gh-watch.py running (restarts it if it dies); events go to events.log. PID in gh-watch.pid.
cd "$(dirname "$0")"
echo $$ > gh-watch.pid
trap 'kill $child 2>/dev/null; exit 0' TERM INT HUP  # killing the daemon's PID also stops the watcher
while true; do
  python3 -u gh-watch.py >> events.log 2>&1 & child=$!
  wait $child
  echo "WATCH ERROR gh-watch.py exited ($?) at $(date -u +%FT%TZ), restarting" >> events.log
  sleep 5
done
