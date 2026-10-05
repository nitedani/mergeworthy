#!/usr/bin/env bash
# Local model server (llama-server, Anthropic + OpenAI compatible API; web UI off). Model and context: profile.sh.
#   serve.sh start    start in the background (no-op if already running the same profile)
#   serve.sh stop     stop it and free the GPU memory
#   serve.sh status
#   serve.sh in-use   exit 0 while any local Claude session runs (wrapper, /bg worker, or a Claude on claude-config)
#   serve.sh reap     started by `start`: stops the server 30 s after the last local session is gone, however it ended
# On demand: claude-local starts it. Loaded means working: after LLM_IDLE seconds (60) without a request the server
# sleeps (the model leaves the GPU, the process stays) and the next request wakes it in ~4 s; measured: 14.8 GB loaded,
# ~0.2 GB asleep. Requests need the key in .api-key.
# Settings: LLM_PROFILE (profile.sh), LLM_PORT (8080), LLM_CTX (the profile's), LLM_IDLE (60).
set -euo pipefail
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
source "$DIR/profile.sh"
SIG="$LLM_PROFILE $LLM_CTX $(echo "${LLM_ARGS[*]}" | md5sum | cut -c1-8)"  # restart when any of these change
PORT="${LLM_PORT:-8080}"
CTX="$LLM_CTX"
IDLE="${LLM_IDLE:-60}"
KEYFILE="$DIR/.api-key"
LOG="$DIR/server.log"
URL="http://127.0.0.1:$PORT"

# --max-time: on some networking setups, connecting to a port nobody listens on hangs instead of being refused
up() { curl -sf --max-time 1 "$URL/health" >/dev/null 2>&1; }
# Another program (a game) is using the GPU: busy over LLM_GPU_BUSY_UTIL % (30) or, before the model loads, over
# LLM_GPU_BUSY_MB (3000, above the desktop's own idle use; re-measure for yours). Then the model doesn't load, and a loaded one unloads.
gpu() { nvidia-smi --query-gpu="$1" --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
gpu_taken() {
  local util; util=$(gpu utilization.gpu); [ -n "$util" ] || return 1
  [ "$util" -ge "${LLM_GPU_BUSY_UTIL:-30}" ] && return 0
  ! up && [ "$(gpu memory.used)" -ge "${LLM_GPU_BUSY_MB:-3000}" ]
}
processing() { curl -sf --max-time 2 -H "Authorization: Bearer $(cat "$KEYFILE")" "$URL/slots" 2>/dev/null | grep -q '"is_processing":true'; }
# The server is the llama-server listening on the port, found by port (no PID file to go stale); the settings it was
# started with ride in its environment (LLM_SIG).
server_pid() { local p; p=$(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2); [ -n "$p" ] && grep -qa llama-server "/proc/$p/cmdline" 2>/dev/null && echo "$p"; }
server_sig() { local p; p=$(server_pid) && tr '\0' '\n' <"/proc/$p/environ" 2>/dev/null | sed -n 's/^LLM_SIG=//p'; }
# The reaper stops the server when no local session is left, even after a killed wrapper; one at a time (flock), and it
# outlives a restart, so a reloading server keeps its watcher.
reaper() { (setsid nohup "$0" reap >/dev/null 2>&1 &); }

case "${1:-start}" in
  start)
    # `touch .disabled` keeps the model off (e.g. while the GPU is needed elsewhere); remove the file to allow it again
    [ -e "$DIR/.disabled" ] && { echo "local model disabled ($DIR/.disabled exists)" >&2; exit 1; }
    if ! up && gpu_taken; then echo "another program is using the GPU ($(gpu utilization.gpu)%, $(gpu memory.used) MiB): not loading the local model" >&2; exit 1; fi
    if [ -n "$(server_pid)" ]; then
      [ "$(server_sig)" = "$SIG" ] && { reaper; echo "already running at $URL ($LLM_PROFILE)"; exit 0; }
      # New settings never interrupt work: while another session uses the server, keep it; they apply at the next start
      if "$0" in-use; then reaper; echo "running with other settings while in use; the new ones apply after it stops" >&2; exit 0; fi
      echo "running with other settings ($(server_sig)); restarting as $SIG"
      "$0" stop; sleep 2
    fi
    [ -s "$KEYFILE" ] || (umask 077; head -c 24 /dev/urandom | base64 | tr -d '/+=' >"$KEYFILE")
    # Sampling: Qwen3.8's thinking-mode values (both profiles' GGUFs carry temp 1.0). --jinja: chat templates, needed for tool calls; the template is the
    # model's own, changed to accept the system message Claude Code sends mid-conversation.
    LLM_SIG="$SIG" nohup "$DIR/build/bin/llama-server" \
      -m "$DIR/weights/$LLM_MODEL" --alias local \
      --host 127.0.0.1 --port "$PORT" \
      -ngl 99 -fa on -c "$CTX" -np 1 "${LLM_ARGS[@]}" --jinja \
      --chat-template-file "$DIR/chat-template.jinja" \
      --api-key-file "$KEYFILE" --sleep-idle-seconds "$IDLE" --no-webui \
      --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.05 \
      >"$LOG" 2>&1 &
    SPID=$!
    echo -n "loading model"
    for _ in $(seq 180); do
      up && { reaper; echo; echo "running at $URL ($LLM_PROFILE, ${CTX} context; log: $LOG)"; exit 0; }
      kill -0 "$SPID" 2>/dev/null || { echo; echo "server exited; last lines of $LOG:"; tail -20 "$LOG"; exit 1; }
      echo -n .; sleep 1
    done
    echo; echo "not ready after 3 minutes; see $LOG"; exit 1 ;;
  stop)
    p=$(server_pid); [ -n "$p" ] && kill "$p" && echo stopped || echo "not running" ;;
  status)
    up && echo "running at $URL" || echo "not running" ;;
  in-use)
    exec python3 - "$DIR" <<'PY'
import json, os, re, sys
d = sys.argv[1]; cfg = os.path.join(d, 'claude-config')
def cmdline(pid):
    try: return open(f'/proc/{pid}/cmdline', 'rb').read()
    except OSError: return b''
sess = os.path.join(d, '.sessions')
for f in os.listdir(sess) if os.path.isdir(sess) else ():  # claude-local wrappers
    c = cmdline(f)  # an eval run, in the harness's bin/sandbox
    if b'claude-local' in c or re.search(rb'/sandbox\0', c): sys.exit(0)
try: workers = json.load(open(os.path.join(cfg, 'daemon/roster.json'))).get('workers', {})  # /bg sessions
except Exception: workers = {}
if any(cmdline(w.get('pid', 0)) for w in workers.values()): sys.exit(0)
want = b'CLAUDE_CONFIG_DIR=' + cfg.encode()  # a Claude whose wrapper is gone (t3 can end the wrapper and keep Claude)
for pid in filter(str.isdigit, os.listdir('/proc')):
    try:
        if '/claude/versions/' in os.readlink(f'/proc/{pid}/exe') and want in open(f'/proc/{pid}/environ', 'rb').read().split(b'\0'):
            sys.exit(0)
    except OSError: pass
sys.exit(1)
PY
    ;;
  reap)
    exec 9>"$DIR/.reaper.lock"; flock -n 9 || exit 0; idle=0; gone=0; busy=0
    while :; do
      if [ -z "$(server_pid)" ]; then gone=$((gone + 1)); [ "$gone" -ge 12 ] && break; sleep 15; continue; fi
      gone=0
      if "$0" in-use; then idle=0; else idle=$((idle + 1)); fi
      [ "$idle" -ge 2 ] && { "$0" stop >/dev/null; break; }
      # the GPU is busy while the model isn't working: another program needs it
      # Another program on the GPU: busy while our server is up and idle, on two readings in a row (30 s). One reading isn't
      # enough: right after a request the GPU still shows our own work, and that stopped a session between two requests.
      # gpu_taken first: /slots counts as a request, and polling it every 15 s kept the server from ever sleeping
      if gpu_taken && up && ! processing; then busy=$((busy + 1)); else busy=0; fi
      [ "$busy" -ge 2 ] && { echo "$(date +%T) unloaded: another program is using the GPU" >>"$LOG"; "$0" stop >/dev/null; break; }
      sleep 15
    done ;;
  *) sed -n 2,6p "$0"; exit 2 ;;
esac
