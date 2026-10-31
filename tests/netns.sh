#!/bin/bash
# netns-run: a server on a port inside doesn't hold that port on the host, names resolve inside, and the command's status comes back.
R=$(readlink -f "${1:-$(dirname "$0")/..}"); fails=0
check() { echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1)); }
if ! command -v slirp4netns >/dev/null; then echo "netns-run: slirp4netns missing, skipped"; exit 0; fi
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
py=$(python3 -c "import sys; print(sys.executable)")  # the interpreter itself: a version-manager shim would be the PID killed, leaving the server
inside=$("$R/bin/netns-run" bash -c "$py -m http.server $port --bind 127.0.0.1 >/dev/null 2>&1 & p=\$!; for i in \$(seq 50); do curl -s -o /dev/null http://127.0.0.1:$port/ && break; sleep 0.1; done; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$port/; kill -9 \$p")  # netns-run's shell ignores SIGTERM, and so does what it starts
check "a server inside answers inside" 200 "$inside"
check "the host doesn't see that port" 0 "$(ss -ltn | grep -c ":$port ")"
sleep 0.3; check "the server is gone once the command ends" 0 "$(pgrep -f "^$py -m http.server $port " | wc -l)"
"$R/bin/netns-run" bash -c 'exit 7'; check "the command's exit status comes back" 7 "$?"
check "the namespace has a route out (tap0)" 1 "$("$R/bin/netns-run" ip route | grep -c '^default via 10.0.2.2 dev tap0')"
check "DNS inside goes to slirp4netns's forwarder, not a host stub like 127.0.0.53" "nameserver 10.0.2.3" "$("$R/bin/netns-run" grep -m1 '^nameserver' /etc/resolv.conf)"
check "a name resolves inside" 0 "$("$R/bin/netns-run" getent hosts github.com >/dev/null; echo $?)"
check "the host's search domains stay" "$(grep -E '^search[[:space:]]' /etc/resolv.conf)" "$("$R/bin/netns-run" grep -E '^search[[:space:]]' /etc/resolv.conf)"
check "the caller's fds 3 to 6 reach the command" "a b c d" "$("$R/bin/netns-run" bash -c 'read -r -u 3 a; read -r -u 4 b; read -r -u 5 c; read -r -u 6 d; echo "$a $b $c $d"' 3<<<a 4<<<b 5<<<c 6<<<d)"
check "the command runs as the caller's uid, with the caller's home" "$(id -u) $(getent passwd "$(id -u)" | cut -d: -f6)" "$("$R/bin/netns-run" bash -c 'echo "$(id -u) $(getent passwd "$(id -u)" | cut -d: -f6)"')"
# A start-up that fails or is killed leaves nothing behind, so a pipe from netns-run ends with it. Each case's processes carry $t.
t=$(mktemp -d); mkdir "$t/fail" "$t/hang" "$t/slowmount" "$t/heldfifo" "$t/tmp"
printf '#!/bin/sh\necho "simulated failure" >&2; exit 1\n' > "$t/fail/slirp4netns"
printf '#!/bin/bash\nfor a; do case $a in --exit-fd=*) read -r -u "${a#*=}" _;; esac; done\n' > "$t/hang/slirp4netns"  # never ready; ends when its exit fd closes
printf '#!/bin/bash\necho $$ > "$0.pid"; exec -a "$0" sleep 30\n' > "$t/slowmount/mount"  # holds the set-up after "go"
printf '#!/bin/sh\necho $$ > "$0.pid"; sleep 3; exec /usr/bin/mkfifo "$@"\n' > "$t/heldfifo/mkfifo"  # holds netns-run before any namespace exists
# traced <dir> <command...>: netns-run <command...> with <dir>, of wrappers that log each call, as the only PATH; prints the log sorted, then the status
command_not_found_handle() { echo "unlisted:$1" >> "$TRACE"; return 127; }  # exported into traced runs, through bash wrappers (dash drops it): a name with no wrapper is logged too
traced() { local d=$1; shift; rm -f "$d.log"; (export -f command_not_found_handle; TRACE="$d.log" PATH="$d" exec "$R/bin/netns-run" "$@") >/dev/null 2>&1; local s=$?; LC_ALL=C sort "$d.log" 2>/dev/null | tr '\n' ' '; echo "| $s"; }
mkdir "$t/trace"; for c in mktemp mkfifo id grep setpriv unshare bash ip mount slirp4netns true cat rm; do printf '#!/bin/bash\necho %s >> "$TRACE"; exec %s "$@"\n' "$c" "$(type -P "$c")" > "$t/trace/$c"; done
cp -r "$t/trace" "$t/trace-noslirp"; printf '#!/bin/bash\necho slirp4netns >> "$TRACE"; exec %s "$@"\n' "$t/fail/slirp4netns" > "$t/trace-noslirp/slirp4netns"
cp -r "$t/trace" "$t/trace-nons"; printf '#!/bin/bash\necho unshare >> "$TRACE"; exit 1\n' > "$t/trace-nons/unshare"
chmod +x "$t"/*/*
check "bin/netns-run names no program by absolute path, which no trace would see" "" "$(tail -n +2 "$R/bin/netns-run" | grep -oE '/[A-Za-z0-9_./-]+' | sort -u | while read -r f; do [ -f "$f" ] && [ -x "$f" ] && echo "$f"; done)"
check "the programs netns-run runs before the namespace is tied to it: only mktemp and mkfifo" "mktemp mkfifo setpriv" "$(traced "$t/trace" true >/dev/null; sed '/^setpriv$/q' "$t/trace.log" | tr '\n' ' ' | sed 's/ $//')"
check "every program a run starts, the command's included" "bash ip mkfifo mktemp mount rm setpriv setpriv setpriv slirp4netns true unshare unshare | 0" "$(traced "$t/trace" true)"
check "every program a run starts when slirp4netns fails" "bash mkfifo mktemp rm setpriv slirp4netns unshare | 1" "$(traced "$t/trace-noslirp" true)"
check "every program a run starts when the namespace doesn't start" "mkfifo mktemp rm setpriv unshare | 1" "$(traced "$t/trace-nons" true)"
check "every program a run starts when mktemp fails" "mktemp | 1" "$(TMPDIR=/nonexistent traced "$t/trace" true)"
s=$SECONDS; out=$(PATH="$t/fail:$PATH" "$R/bin/netns-run" echo "$t" 2>&1 | timeout 10 cat; echo "exit ${PIPESTATUS[0]}")
check "a failing slirp4netns: netns-run's error and status come back" "netns-run: slirp4netns didn't come up: simulated failure exit 1" "$(echo $out)"
check "... within seconds" 1 "$((SECONDS - s < 5))"
sleep 0.3; check "... and nothing of that run is left" 0 "$(pgrep -fc -- "$t")"
s=$SECONDS; out=$(PATH="$t/hang:$PATH" timeout 1 "$R/bin/netns-run" echo "$t" 2>&1 | timeout 10 cat; echo "exit ${PIPESTATUS[0]}")
check "netns-run killed before the command starts: the kill's status comes back" "exit 124" "$out"
check "... within seconds" 1 "$((SECONDS - s < 5))"
sleep 0.3; check "... and nothing of that run is left, slirp4netns included" 0 "$(pgrep -fc -- "$t")"
# killed <sig> <file> <command...>: netns-run <command...>, sent <sig> alone once <file> exists; its output passes through
killed() { local sig=$1 f=$2; shift 2; { "$R/bin/netns-run" "$@" & p=$!; for _ in $(seq 100); do [ -s "$f" ] && break; sleep 0.1; done; kill -"$sig" "$p"; } 2>&1 | timeout 10 cat; rm -f "$f"; }
for sig in TERM KILL; do
  s=${EPOCHREALTIME/./}; TMPDIR="$t/tmp" PATH="$t/heldfifo:$PATH" killed "$sig" "$t/heldfifo/mkfifo.pid" echo "$t"
  check "netns-run killed by $sig during mkfifo: its output ends within 2 s, while mkfifo still runs" "1 1" "$(( ${EPOCHREALTIME/./} - s < 2000000 )) $(pgrep -fc -- "$t/heldfifo")"
  sleep 3.5; check "... and mkfifo ends on its own, leaving nothing of the run" 0 "$(pgrep -fc -- "$t")"
  s=$SECONDS; PATH="$t/slowmount:$PATH" killed "$sig" "$t/slowmount/mount.pid" echo "$t"
  sleep 0.3; check "netns-run killed by $sig during the namespace's set-up: within seconds, nothing of it left" "1 0" "$((SECONDS - s < 5)) $(pgrep -fc -- "$t")"
  s=$SECONDS; killed "$sig" "$t/cmd.pid" bash -c 'echo $$ > "$1/cmd.pid"; exec -a "$1" sleep 30' _ "$t"
  sleep 0.3; check "netns-run killed by $sig while the command runs: within seconds, the command ends too" "1 0" "$((SECONDS - s < 5)) $(pgrep -fc -- "$t")"
done
rm -rf "$t"
echo "failures: $fails"; [ "$fails" = 0 ]
