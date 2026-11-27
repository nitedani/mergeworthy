#!/usr/bin/env bash
# Tests for bin/disk-sweep. Usage: tests/disk-sweep.sh [repo root]
# Builds a temp HOME with a work folder of worktrees and repos, a ~/.t3/worktrees worktree and a stub `docker` first on PATH,
# ages their files, runs the sweep without --delete (a dry run) and then with it, and checks what each rule removed and kept.
# Docker's prunes run only from the watcher daemon of the main watch dir, so they run in a process tree shaped like the daemon's.
# Prints "case: <got> (want <want>)"; exits 0 only when every case gives what it wants.
set -u
R=$(readlink -f "${1:-$(dirname "$0")/..}")
# in /tmp whatever TMPDIR says: disk-sweep refuses --delete for a HOME under the account home
T=$(mktemp -d -p /tmp); export HOME="$T/home" DOCKER_LOG="$T/docker.log" DOCKER_ROOT="$T"; mkdir -p "$HOME/.claude/agent-jobs" "$T/bin"
unset T3CODE_HOME  # T3 Code's data directory, which a run under T3 inherits; the cases use $HOME/.t3
cat > "$T/bin/docker" <<'EOF'
#!/bin/sh
# stub docker: records each call; the prunes report what they reclaimed as Docker prints it, or fail when DOCKER_FAIL is set
echo "$*" >> "$DOCKER_LOG"
case "$1 $2" in
  *" prune") [ -z "${DOCKER_FAIL:-}" ] || { echo 'cannot prune: daemon is shutting down' >&2; exit 1; } ;;
esac
case "$1 $2 $3" in
  "info --format "*) echo "$DOCKER_ROOT"; exit 0 ;;
  "builder prune --help") echo '      --max-used-space bytes   Maximum amount of disk space allowed to keep for cache'; exit 0 ;;
esac
case "$1 $2" in
  "image prune") echo 'Total reclaimed space: 1.5MB' ;;
  "builder prune") printf 'ID\tRECLAIMABLE\tSIZE\nTotal:\t2GB\n' ;;
esac
EOF
for t in pnpm npm pip; do printf '#!/bin/sh\necho "%s $*" >> "%s/tools.log"\n' "$t" "$T" > "$T/bin/$t"; chmod +x "$T/bin/$t"; done  # stub tools: never the machine's
chmod +x "$T/bin/docker"; export PATH="$T/bin:$PATH"; : > "$DOCKER_LOG"
PY=$(python3 -c 'import sys; print(sys.executable)'); python3() { command "$PY" "$@"; }  # no version-manager shim moving its bin ahead of the stubs
fails=0
check() { echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1)); }
G() { git -c user.name=t -c user.email=t@example.invalid "$@"; }
age() { find "$@" -exec touch -h -d '2 days ago' {} +; }
there() { [ -e "$1" ] || [ -L "$1" ] && echo kept || echo removed; }
dsm() { python3 -c 'import importlib.machinery as M, importlib.util as U, os, sys  # bin/disk-sweep as module m, then the code $1, its arguments after it
l = M.SourceFileLoader("ds", sys.argv[1]); m = U.module_from_spec(U.spec_from_loader("ds", l)); l.exec_module(m)
exec(sys.argv[2])' "$R/bin/disk-sweep" "$@"; }

WF="$HOME/x-work"; mkdir -p "$WF"
G init -q --bare "$T/origin.git"; G init -q -b main "$T/main"
printf 'node_modules\n.env\n' > "$T/main/.gitignore"; echo a > "$T/main/README"
G -C "$T/main" add .gitignore README; G -C "$T/main" commit -qm base
G -C "$T/main" remote add origin "$T/origin.git"; G -C "$T/main" push -q origin main; G -C "$T/main" fetch -q origin
wt() { G -C "$T/main" worktree add -q -b "$(basename "$1")" "$1" origin/main 2>/dev/null; }
for n in clean dirty recent proc job writer; do wt "$WF/$n"; done
wt "$HOME/.t3/worktrees/p/t3wt"
echo x > "$WF/dirty/untracked.txt"
mkdir -p "$T/outside/node_modules" "$WF/clean/node_modules" "$WF/proc/node_modules" "$WF/job/node_modules" "$WF/writer/node_modules" "$WF/recent/node_modules" "$WF/drafts/node_modules" "$WF/fresh/node_modules" "$WF/rec"
echo x > "$T/outside/node_modules/x"; ln -s "$T/outside" "$WF/link"; ln -s "$T/outside/node_modules" "$WF/dirty/node_modules"
echo x > "$WF/clean/.env"; echo x > "$WF/clean/node_modules/x"; echo x > "$WF/proc/node_modules/x"; echo x > "$WF/job/node_modules/x"; echo x > "$WF/writer/node_modules/install.log"; echo x > "$WF/recent/node_modules/x"; echo x > "$WF/drafts/node_modules/x"; echo x > "$WF/drafts/notes.md"; echo x > "$WF/fresh/node_modules/x"
G init -q "$WF/tracked"; mkdir -p "$WF/tracked/node_modules"; echo x > "$WF/tracked/node_modules/x"; G -C "$WF/tracked" add node_modules; G -C "$WF/tracked" commit -qm tracked
truncate -s 11M "$WF/rec/old.webm" "$WF/rec/old.zip"
age "$WF" "$HOME/.t3" "$T/outside"
find "$WF/rec" -exec touch -d '8 days ago' {} +
mkdir -p "$HOME/.t3/worktrees/p/t3wt/node_modules"; echo x > "$HOME/.t3/worktrees/p/t3wt/node_modules/x"  # fresh, but git ignores it
touch "$WF/recent/README" "$WF/fresh/new.md"
bash -c "cd '$WF/proc' && exec sleep 600" & SPID=$!
(cd "$T" && exec python3 -c 'import sys, time; f = open(sys.argv[1], "a"); time.sleep(600)' "$WF/writer/node_modules/install.log") & WPID=$!
python3 -c 'import json,sys,time; json.dump({"key": "impl proc", "started": time.time(), "brief": "Work in " + sys.argv[1] + "/src."}, open(sys.argv[2], "w"))' "$WF/job" "$HOME/.claude/agent-jobs/j1.json"
sleep 0.2  # the sleep's cwd is set

python3 "$R/bin/disk-sweep" > "$T/dry.out" 2> "$T/dry.err"; rc=$?
check "without --delete it exits 0" 0 "$rc"
check "without --delete it prints the clean worktree's node_modules and Docker's three prunes, with unknown sizes" "1 3 0" "$(grep -c " $WF/clean/node_modules c-ignored$" "$T/dry.out") $(grep -c '^[^ ]* ? docker:[a-z]* d-docker$' "$T/dry.out") $(wc -c < "$T/dry.err")"
check "without --delete it deletes nothing, writes no log, calls no docker" "kept kept kept no 0" "$(there "$WF/clean/node_modules") $(there "$WF/drafts/node_modules") $(there "$HOME/.t3/worktrees/p/t3wt/node_modules") $([ -e "$HOME/.mergeworthy/disk-sweep.log" ] && echo yes || echo no) $(wc -l < "$DOCKER_LOG")"
check "a second sweep while one runs is refused" "1 1" "$(flock "$HOME/.mergeworthy/disk-sweep.lock" python3 "$R/bin/disk-sweep" 2>"$T/lock.err" >/dev/null; echo $?) $(grep -c 'another sweep is running' "$T/lock.err")"
: > "$DOCKER_LOG"

python3 "$R/bin/disk-sweep" --delete > "$T/run.out" 2>&1; rc=$?
LOG="$HOME/.mergeworthy/disk-sweep.log"
check "a sweep the daemon didn't start exits 0, prints only that Docker is skipped and calls no docker" "0 1 0" "$rc $(wc -l < "$T/run.out") $(wc -l < "$DOCKER_LOG")"
check "a clean, pushed, idle worktree is kept with its ignored .env; its node_modules is removed, logged before and after" "kept kept removed deleting|deleted|" "$(there "$WF/clean") $(there "$WF/clean/.env") $(there "$WF/clean/node_modules") $(grep "^[^ ]* [0-9][0-9]* $WF/clean/node_modules c-ignored " "$LOG" | cut -d' ' -f5 | tr '\n' '|')"
check "a worktree with a file changed in 24 hours is kept, with its node_modules" "kept kept" "$(there "$WF/recent") $(there "$WF/recent/node_modules")"
check "a worktree a process works in keeps its node_modules" kept "$(there "$WF/proc/node_modules")"
check "a worktree an open agent job names a path inside of keeps its node_modules" kept "$(there "$WF/job/node_modules")"
check "a ~/.t3/worktrees worktree is kept, and its ignored node_modules with a file changed in 24 hours" "kept kept" "$(there "$HOME/.t3/worktrees/p/t3wt") $(there "$HOME/.t3/worktrees/p/t3wt/node_modules")"
check "a node_modules a process outside it holds a file open in is kept" kept "$(there "$WF/writer/node_modules")"
check "a tracked node_modules is kept" kept "$(there "$WF/tracked/node_modules")"
check "symlinks to outside the roots are not followed" "kept kept kept" "$(there "$T/outside/node_modules/x") $(there "$WF/link") $(there "$WF/dirty/node_modules")"
check "node_modules outside repos: idle parent removed, recent parent kept" "removed kept" "$(there "$WF/drafts/node_modules") $(there "$WF/fresh/node_modules")"
check "a work folder's .webm and .zip over 10 MB and 8 days old are kept" "kept kept" "$(there "$WF/rec/old.webm") $(there "$WF/rec/old.zip")"

# a HOME whose ~/.t3 is a symlink to a folder outside it, with a process already working in the worktree there
H2="$T/home2"; mkdir -p "$H2" "$T/t3real/worktrees"; ln -s "$T/t3real" "$H2/.t3"
G init -q "$T/t3real/worktrees/p"; echo node_modules > "$T/t3real/worktrees/p/.gitignore"; G -C "$T/t3real/worktrees/p" add .gitignore; G -C "$T/t3real/worktrees/p" commit -qm base
mkdir -p "$T/t3real/worktrees/p/node_modules"; echo x > "$T/t3real/worktrees/p/node_modules/x"; age "$T/t3real"
bash -c "cd '$T/t3real/worktrees/p' && exec sleep 600" & S2=$!; sleep 0.2
HOME="$H2" python3 "$R/bin/disk-sweep" --delete 2>/dev/null; rc=$?
check "a worktree under a symlinked ~/.t3, a process working in it, keeps its node_modules" "0 kept" "$rc $(there "$T/t3real/worktrees/p/node_modules")"
kill "$S2"; wait "$S2" 2>/dev/null
mkdir -p "$T/t3real/worktrees/p/node_modules"; echo x > "$T/t3real/worktrees/p/node_modules/x"; age "$T/t3real"
HOME="$H2" dsm 'm.DRY = False; p = os.path.join(m.HOME, ".t3/worktrees/p/node_modules"); m.delete(p, os.path.dirname(p), os.lstat(p).st_dev, "c-ignored")'
check "a candidate with a symlink on its path is not deleted" kept "$(there "$T/t3real/worktrees/p/node_modules")"

# a process and a job that appear in a candidate's repo after the sweep's start, and a process that starts there while it runs
H4="$T/home4"; Z="$H4/z-work"; mkdir -p "$H4/.claude/agent-jobs" "$H4/.mergeworthy"
for n in late job during; do G init -q "$Z/$n"; echo node_modules > "$Z/$n/.gitignore"; G -C "$Z/$n" add .gitignore; G -C "$Z/$n" commit -qm base; mkdir -p "$Z/$n/node_modules"; echo x > "$Z/$n/node_modules/x"; done; age "$Z"
HOME="$H4" dsm 'import json, subprocess, time
z, started = os.path.join(m.HOME, "z-work"), []
try:
    started.append(subprocess.Popen(["sleep", "600"], cwd=z + "/late"))
    json.dump({"key": "impl late", "started": time.time(), "brief": "Work in " + z + "/job."}, open(m.HOME + "/.claude/agent-jobs/late.json", "w"))
    measure = m.measure
    def measuring(path, dev, *a):
        if path == z + "/during/node_modules":
            started.append(subprocess.Popen(["sleep", "600"], cwd=z + "/during"))
        return measure(path, dev, *a)
    m.measure = measuring; m.DRY = False; m.sweep_files()
finally:
    for q in started:
        q.kill(); q.wait()'
check "a repo a process started in, or a job named, after the sweep's start, or a process started in while it ran, keeps its node_modules" "kept kept kept" "$(there "$Z/late/node_modules") $(there "$Z/job/node_modules") $(there "$Z/during/node_modules")"

# a sweep killed in the middle of a deletion
mkdir -p "$T/killed/node_modules"; echo x > "$T/killed/node_modules/x"; age "$T/killed"
dsm 'm.DRY = False; m.empty = lambda fd, path=None: os.kill(os.getpid(), 9); p = sys.argv[3]; m.delete(p, os.path.dirname(p), os.lstat(p).st_dev, "c-ignored")' "$T/killed/node_modules"
check "a sweep killed while deleting leaves the deletion's intent in the log" "137 1" "$? $(grep -c "^[^ ]* [0-9][0-9]* $T/killed/node_modules c-ignored deleting$" "$LOG")"

# data a rebuild can't restore inside a candidate: a nested checkout with an unpushed commit and an edit, a .git file, an unreadable folder
H3="$T/home3"; Y="$H3/y-work"; mkdir -p "$Y"; G init -q "$Y/outer"; echo build/ > "$Y/outer/.gitignore"; G -C "$Y/outer" add .gitignore; G -C "$Y/outer" commit -qm base
G init -q "$Y/outer/build/checkout"; echo a > "$Y/outer/build/checkout/unique.txt"; G -C "$Y/outer/build/checkout" add unique.txt; G -C "$Y/outer/build/checkout" commit -qm local; echo b >> "$Y/outer/build/checkout/unique.txt"
mkdir -p "$Y/loose/node_modules/pkg" "$Y/locked/node_modules/sub" "$Y/plain/node_modules"; echo 'gitdir: /elsewhere' > "$Y/loose/node_modules/pkg/.git"
echo x > "$Y/locked/node_modules/sub/x"; echo y > "$Y/locked/node_modules/y"; echo x > "$Y/plain/node_modules/x"; age "$Y"; chmod 000 "$Y/locked/node_modules/sub"
HOME="$H3" python3 "$R/bin/disk-sweep" --delete 2>/dev/null; chmod 755 "$Y/locked/node_modules/sub"
check "a build folder holding a nested checkout, a node_modules holding a .git file or a folder it can't read are kept; a plain one goes" "kept kept kept removed" "$(there "$Y/outer/build/checkout/.git") $(there "$Y/loose/node_modules/pkg/.git") $(there "$Y/locked/node_modules/y") $(there "$Y/plain/node_modules")"

# a repo swapped for a symlink, then for a real directory, after the sweep inspected its node_modules and before it deletes it
swap() { mkdir -p "$T/$1/repo/node_modules" "$T/$1/outside/node_modules"; echo x > "$T/$1/repo/node_modules/x"; echo only > "$T/$1/outside/node_modules/only-copy.txt"; age "$T/$1"
  dsm 'rec = m.record
def record(n, what, rule, state):
    if state == "deleting":
        os.rename(sys.argv[3] + "/repo", sys.argv[3] + "/repo-old")
        os.symlink(sys.argv[3] + "/outside", sys.argv[3] + "/repo") if sys.argv[4] == "symlink" else os.rename(sys.argv[3] + "/outside", sys.argv[3] + "/repo")
    rec(n, what, rule, state)
m.record = record; m.DRY = False; p = sys.argv[3] + "/repo/node_modules"; m.delete(p, os.path.dirname(p), os.lstat(p).st_dev, "c-ignored")' "$T/$1" "$1" 2>/dev/null; }
swap symlink
check "a repo swapped for a symlink to elsewhere before the deletion: neither node_modules is deleted" "kept kept" "$(there "$T/symlink/outside/node_modules/only-copy.txt") $(there "$T/symlink/repo-old/node_modules/x")"
swap dir
check "a repo swapped for another real directory before the deletion: neither node_modules is deleted" "kept kept" "$(there "$T/dir/repo/node_modules/only-copy.txt") $(there "$T/dir/repo-old/node_modules/x")"

# a deleting run anywhere under the account's real home, or a Docker prune, only from the installed watcher's daemon on the main watch dir
AH=$(getent passwd "$(id -u)" | cut -d: -f6); AT=$(mktemp -d -p "$AH" .disk-sweep-test.XXXXXX); V="$AT/home/v-work"
mkdir -p "$AT/home/.mergeworthy" "$V"; G init -q "$V/repo"; echo node_modules > "$V/repo/.gitignore"; G -C "$V/repo" add .gitignore; G -C "$V/repo" commit -qm base
mkdir -p "$V/repo/node_modules" "$V/repo2/node_modules"; echo x > "$V/repo/node_modules/x"; echo x > "$V/repo2/node_modules/x"; age "$AT"
HOME="$AT/home" python3 "$R/bin/disk-sweep" --delete 2> "$T/home.err"; rc=$?
HOME="$AT/home" dsm 'm.DRY = False; p = sys.argv[3]; m.delete(p, os.path.dirname(p), os.lstat(p).st_dev, "c-node_modules")' "$V/repo2/node_modules" 2>/dev/null
check "under the account's home a sweep the daemon didn't start refuses --delete, and delete() deletes nothing there" "2 kept kept" "$rc $(there "$V/repo/node_modules") $(there "$V/repo2/node_modules")"
rm -rf "$AT"
: > "$DOCKER_LOG"; dsm 'os.environ["HOME"] = "/elsewhere"; m.DRY = False; sys.exit(m.prune_docker())' 2> "$T/prune.err"; rc=$?
check "prune_docker in a process the daemon didn't start prunes nothing and says so" "0 0 1" "$rc $(grep -c prune "$DOCKER_LOG") $(grep -c 'Docker skipped' "$T/prune.err")"
# the same check from a process tree shaped like the daemon's: a loop shell that wrote gh-watch.pid, its gh-watch.py, the sweep
I="$T/inst"; W="$T/watchdir"; mkdir -p "$I/bin" "$I/hooks" "$I/watcher" "$W"; cp "$R/bin/disk-sweep" "$I/bin/"; cp "$R/hooks/agent_jobs.py" "$R/hooks/memory_file.py" "$R/hooks/own_actions.py" "$R/hooks/records.py" "$R/hooks/shellcmd.py" "$R/hooks/steward.py" "$R/hooks/t3_tasks.py" "$R/hooks/testpaths.py" "$R/hooks/threads_file.py" "$R/hooks/work_folder.py" "$I/hooks/"; ln -s "$I/watcher/gh-watch.py" "$W/gh-watch.py"
LOAD='import importlib.machinery as M, importlib.util as U, sys
l = M.SourceFileLoader("ds", sys.argv[1]); m = U.module_from_spec(U.spec_from_loader("ds", l)); l.exec_module(m)
'
printf 'import subprocess, sys\nsubprocess.run([sys.executable, "-c", sys.argv[1], *sys.argv[2:]])\n' > "$I/watcher/gh-watch.py"
daemon() { bash -c 'cd "$1" && echo $$ > gh-watch.pid && python3 -u gh-watch.py "$3" "$4" "$2" "$1"; true' _ "$W" "$I" "$LOAD$1" "$2"; }
daemon=$(daemon 'print(m.from_daemon(sys.argv[2], sys.argv[3]), m.from_daemon(sys.argv[2], "/elsewhere"), m.from_daemon("/elsewhere", sys.argv[3]))' "$I/bin/disk-sweep")
copy=$(daemon 'print(m.from_daemon(sys.argv[2], sys.argv[3]))' "$R/bin/disk-sweep")
direct=$(cd "$W" && python3 -c "$LOAD"'print(m.from_daemon(sys.argv[2], sys.argv[3]))' "$I/bin/disk-sweep" "$I" "$W")
byhand=$(cd "$W" && python3 -u gh-watch.py "$LOAD"'print(m.from_daemon(sys.argv[2], sys.argv[3]))' "$I/bin/disk-sweep" "$I" "$W"; true)
check "from_daemon: the daemon's tree on the main watch dir yes; another main dir, another install, a sweep from another copy, a probe in the watch dir or its gh-watch.py run by hand no" "True False False|False|False|False" "$daemon|$copy|$direct|$byhand"
# the prunes through the guarded entry, from the daemon's tree with this test's install and watch dir: what the daemon's sweep runs
PRUNE='m.INSTALLED, m.main_watch_dir, m.DRY = sys.argv[2], lambda: sys.argv[3], False; print(m.prune_docker())'
: > "$DOCKER_LOG"; got=$(daemon "$PRUNE" "$I/bin/disk-sweep")
CAP=$(( $(df -B1 --output=size "$T" | tail -1) / 10 ))
check "Docker from the daemon's tree: version, every unused image and the build cache older than 14 days, then the build cache down to a tenth of the filesystem holding Docker's root dir; never containers or volumes" "0 version|image prune -a -f --filter until=336h|builder prune -f --filter until=336h|info --format {{.DockerRootDir}}|builder prune --help|builder prune -f --max-used-space $CAP|" "$got $(tr '\n' '|' < "$DOCKER_LOG")"
check "Docker's reclaimed sizes are logged" "1500000 docker:image|2000000000 docker:builder|2000000000 docker:builder|" "$(grep d-docker "$LOG" | cut -d' ' -f2,3 | tr '\n' '|')"
got=$(DOCKER_FAIL=1 daemon "$PRUNE" "$I/bin/disk-sweep" 2> "$T/prune.err")
check "a prune that fails returns 1, its stderr reported, no log line written" "1 2 3" "$got $(grep -c 'daemon is shutting down' "$T/prune.err") $(grep -c d-docker "$LOG")"

# a dry run selects as a deleting run does: not a node_modules whose repo a process holds a file in, or starts working in while it runs
H5="$T/home5"; D="$H5/d-work"; mkdir -p "$H5/.mergeworthy"
for n in held during; do G init -q "$D/$n"; echo node_modules > "$D/$n/.gitignore"; G -C "$D/$n" add .gitignore; G -C "$D/$n" commit -qm base; mkdir -p "$D/$n/node_modules"; echo x > "$D/$n/node_modules/dep"; done; age "$D"
HOME="$H5" dsm 'import subprocess
d, started = os.path.join(m.HOME, "d-work"), []
try:
    started.append(subprocess.Popen([sys.executable, "-c", "import sys, time; f = open(sys.argv[1]); time.sleep(600)", d + "/held/node_modules/dep"], cwd="/"))
    time = __import__("time"); time.sleep(0.3)
    measure = m.measure
    def measuring(path, dev, *a):
        if path == d + "/during/node_modules":
            started.append(subprocess.Popen(["sleep", "600"], cwd=d + "/during"))
        return measure(path, dev, *a)
    m.measure = measuring; m.sweep_files()
finally:
    for q in started:
        q.kill(); q.wait()' > "$T/dry5.out"
check "a dry run lists no node_modules whose repo a process holds a file in or started working in while it ran" 0 "$(grep -c "$D/" "$T/dry5.out")"

# every sink refuses by itself, whoever calls it: in a dry run (the default on import); under the account's home and for Docker
# unless the main watch dir's daemon started the sweep
mkdir -p "$T/sink/e/x" "$T/sink/r/x"; echo x > "$T/sink/e/x/f"; echo x > "$T/sink/r/x/f"; AS=$(mktemp -d -p "$AH" .disk-sweep-test.XXXXXX); mkdir -p "$AS/r/x"; echo x > "$AS/r/x/f"; : > "$DOCKER_LOG"
got=$(dsm 'def refused(f, *a):
    try:
        f(*a)
    except (PermissionError, AttributeError) as e:
        return type(e).__name__
    return "ran"
fd = os.open(sys.argv[3] + "/e", os.O_RDONLY | os.O_DIRECTORY)
out = [refused(m.empty, fd), refused(m.remove, sys.argv[3] + "/r", os.lstat(sys.argv[3] + "/r")), refused(getattr(m, "run_docker", None) or m.run_prunes, "docker")]
m.DRY = False
out += [refused(m.remove, sys.argv[4] + "/r", os.lstat(sys.argv[4] + "/r")), refused(getattr(m, "run_docker", None) or m.run_prunes, "docker")]
print(*out)' "$T/sink" "$AS" 2>/dev/null)
check "empty, remove and Docker refuse in a dry run; remove under the account's home and Docker refuse outside the daemon" "PermissionError PermissionError PermissionError PermissionError PermissionError kept kept kept 0" "$got $(there "$T/sink/e/x/f") $(there "$T/sink/r/x/f") $(there "$AS/r/x/f") $(wc -l < "$DOCKER_LOG")"
rm -rf "$AS"

# round 7: build output in any repo under home, tool caches, and a weekly report; each needs 14 untouched days
H7="$T/home7"; mkdir -p "$H7/.mergeworthy"; : > "$T/tools.log"
old() { find "$@" -exec touch -h -d '15 days ago' {} +; }
for r in proj/app proj/young .hidden/r a/b/c/d/e/deep; do repo7="$H7/$r"; G init -q "$repo7"; echo dist > "$repo7/.gitignore"; G -C "$repo7" add .gitignore; G -C "$repo7" commit -qm base; mkdir -p "$repo7/dist"; echo x > "$repo7/dist/x"; done
mkdir -p "$H7/.npm/_cacache/x" "$H7/.cache/yarn/stale/x" "$H7/.cache/yarn/fresh" "$H7/.cache/drafts/x" "$H7/.cache/ms-playwright/chromium_headless_shell-1200" "$H7/.cache/yarn/readnow" "$H7/.cargo/registry/cache/idx" "$H7/.cargo/git/checkouts/c/rev/.git" "$H7/old-stuff/sub"
echo x > "$H7/.npm/_cacache/x/f"; echo x > "$H7/.cache/yarn/stale/x/f"; echo x > "$H7/.cache/drafts/x/f"; echo x > "$H7/.cache/yarn/readnow/f"; echo x > "$H7/.cargo/registry/cache/idx/a.crate"; echo x > "$H7/.cargo/git/checkouts/c/rev/.git/HEAD"
truncate -s 3M "$H7/old-stuff/sub/big"; old "$H7"; touch "$H7/.cache/yarn/fresh/f"; touch -a "$H7/.cache/yarn/readnow/f"; age "$H7/proj/young"
HOME="$H7" python3 "$R/bin/disk-sweep" --delete 2>/dev/null
check "a repo anywhere under home loses its 14-day-old build output; 2 days old, hidden or 6 levels down keeps it" "removed kept kept kept" "$(there "$H7/proj/app/dist") $(there "$H7/proj/young/dist") $(there "$H7/.hidden/r/dist") $(there "$H7/a/b/c/d/e/deep/dist")"
mkdir -p "$H7/proj/app/dist"; echo x > "$H7/proj/app/dist/x"; old "$H7/proj/app/dist"
HOME="$H7" python3 "$R/bin/disk-sweep" --delete 2>/dev/null
check "the home-wide walk runs at most once a day" kept "$(there "$H7/proj/app/dist")"
check "caches: pnpm, npm (stale _cacache) and pip by their own commands; stale tool-cache and cargo entries go, a fresh one, an unnamed ~/.cache folder an old Playwright browser and an old entry read today stay" "npm cache clean --force|pip cache purge|pnpm store prune| removed removed removed kept kept kept kept" "$(sort -u "$T/tools.log" | tr '\n' '|') $(there "$H7/.cache/yarn/stale") $(there "$H7/.cargo/registry/cache/idx") $(there "$H7/.cargo/git/checkouts/c") $(there "$H7/.cache/yarn/fresh") $(there "$H7/.cache/drafts") $(there "$H7/.cache/ms-playwright/chromium_headless_shell-1200") $(there "$H7/.cache/yarn/readnow")"
check "a weekly report names the stale folder no rule covers, and deletes nothing" "1 0 kept" "$(cat "$H7/.mergeworthy/disk-report.md" 2>/dev/null | grep -c "$H7/old-stuff") $(cat "$H7/.mergeworthy/disk-report.md" 2>/dev/null | grep -c "$H7/.cache/yarn") $(there "$H7/old-stuff/sub/big")"

# h-cargo: a cargo build folder under home, in a repo or not, goes after 7 unused days; a fresh one, a pytest cache's lone CACHEDIR.TAG
# or one whose project a process works in stays, and a repo's ignored target that h-ignored takes is listed once
HC="$T/homec"; mkdir -p "$HC/.mergeworthy"
for p in loose/target fresh/target busy/target repo/target trk/target force/target repo8/target unig/target mono/member/target custom; do mkdir -p "$HC/$p/debug"; echo x > "$HC/$p/debug/x"; echo 'Signature: 8a477f597d28d172789f06886806bc55' > "$HC/$p/CACHEDIR.TAG"; echo '{}' > "$HC/$p/.rustc_info.json"; done
mkdir -p "$HC/pre/target/debug"; echo '{}' > "$HC/pre/target/.rustc_info.json"; echo x > "$HC/pre/target/debug/x"; mkdir -p "$HC/symm/target/debug"; echo '{}' > "$T/rinfo"; ln -s "$T/rinfo" "$HC/symm/target/.rustc_info.json"; echo x > "$HC/symm/target/debug/x"; mkdir -p "$HC/build/under/target"; echo '{}' > "$HC/build/under/target/.rustc_info.json"; mkdir -p "$HC/py/cache"; echo 'Signature: 8a477f597d28d172789f06886806bc55' > "$HC/py/cache/CACHEDIR.TAG"; echo x > "$HC/py/cache/v"
G init -q "$HC/repo"; echo target/ > "$HC/repo/.gitignore"; G -C "$HC/repo" add .gitignore; G -C "$HC/repo" commit -qm base
for n in trk force repo8 unig mono; do G init -q "$HC/$n"; done; for n in force repo8 mono; do echo target/ > "$HC/$n/.gitignore"; G -C "$HC/$n" add .gitignore; done
G -C "$HC/trk" add target; G -C "$HC/force" add -f target/debug/x; for n in trk force repo8; do G -C "$HC/$n" commit -qm base; echo edit >> "$HC/$n/target/debug/x"; done
find "$HC" -exec touch -h -d '15 days ago' {} +; find "$HC/loose" "$HC/trk" "$HC/force" "$HC/repo8" "$HC/unig" "$HC/mono" "$HC/custom" "$HC/pre" "$HC/symm" "$HC/build" -exec touch -h -d '8 days ago' {} +; find "$HC/fresh" -exec touch -h -d '2 days ago' {} +
LA=$(stat -c %X "$HC/symm/target/.rustc_info.json"); bash -c "cd '$HC/busy' && exec sleep 600" & CB=$!; bash -c "cd '$HC/mono' && exec sleep 600" & CM=$!; sleep 0.2
HOME="$HC" python3 "$R/bin/disk-sweep" > "$T/dryc.out" 2>/dev/null
check "a dry run lists a repo's ignored cargo target once, as h-ignored's" "1 1" "$(grep -c " $HC/repo/target " "$T/dryc.out") $(grep -c " $HC/repo/target h-ignored$" "$T/dryc.out")"
HOME="$HC" python3 "$R/bin/disk-sweep" --delete 2>/dev/null; kill "$CB" "$CM"; wait "$CB" "$CM" 2>/dev/null
check "h-cargo deletes a cargo target outside any repo unused for 7 days, logged; a 2-day-old one, a lone CACHEDIR.TAG and a busy project's stay" "removed 1 kept kept kept removed" "$(there "$HC/loose/target") $(grep -c " $HC/loose/target h-cargo deleted$" "$HC/.mergeworthy/disk-sweep.log") $(there "$HC/fresh/target") $(there "$HC/py/cache") $(there "$HC/busy/target") $(there "$HC/repo/target")"
check "in a repo h-cargo takes only a target git ignores holding no tracked file: a tracked one and an ignored one with a force-added file stay, with their unstaged edits, and an untracked one git doesn't ignore" "kept 1 kept 1 kept removed" "$(there "$HC/trk/target") $(grep -c edit "$HC/trk/target/debug/x") $(there "$HC/force/target") $(grep -c edit "$HC/force/target/debug/x") $(there "$HC/unig/target") $(there "$HC/repo8/target")"
check "a process at a repo's root keeps a member's target; one in another project keeps no cargo folder directly in home" "kept removed" "$(there "$HC/mono/member/target") $(there "$HC/custom")"
check "h-cargo deletes a target cargo built into once it existed, which holds .rustc_info.json without CACHEDIR.TAG" removed "$(there "$HC/pre/target")"
check "a symlinked .rustc_info.json marks no cargo folder, and the sweep doesn't follow it" "kept same" "$(there "$HC/symm/target") $([ "$(stat -c %X "$HC/symm/target/.rustc_info.json")" = "$LA" ] && echo same || echo read)"
check "h-cargo doesn't look inside a folder named like a build folder" kept "$(there "$HC/build/under/target")"

# w-done over a whole sweep: the dry run, then a deleting one, with T3's database as a fixture (deleted, no row, settled, auto-settled,
# archived, live; a row it can't read for err-*)
H9="$T/home9"; mkdir -p "$H9/.t3/userdata"; python3 - "$H9/.t3/userdata/statev2.sqlite" <<'DB'
import json, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute("create table orchestration_v2_projection_threads (thread_id text primary key, archived_at text, deleted_at text, payload_json text not null)")
at, row = "2026-01-01T00:00:00.000Z", lambda tid, archived=None, deleted=None, **p: (tid, archived, deleted, json.dumps({"settledOverride": None, "settledAt": None, **p}))
rows = [row(f"del-{i}", deleted=at) for i in (1, 2, 3, 4, 5, 6, 9)] + [row("set-1", settledOverride="settled", settledAt=at), row("aset-1", settledAt=at), row("arc-1", archived=at)]
rows += [row(f"live-{i}") for i in (1, 2, 3, 4)] + [(f"err-{i}", None, None, "not json") for i in (1, 2)]  # json_extract fails on these: the database can't say
c.executemany("insert into orchestration_v2_projection_threads values (?, ?, ?, ?)", rows); c.commit()
DB
W9="$H9/.mergeworthy/work"; mkdir -p "$W9" "$H9/.claude/agent-jobs" "$H9/.config/systemd/user"; : > "$H9/.config/systemd/user/gh-watch@.service"
G init -q --bare -b main "$T/w-origin.git"; G init -q -b main "$T/w-seed"; printf 'node_modules\n' > "$T/w-seed/.gitignore"; G -C "$T/w-seed" add .gitignore; G -C "$T/w-seed" commit -qm base; G -C "$T/w-seed" push -q "$T/w-origin.git" main
mk() { G clone -q "file://$T/w-origin.git" "$W9/$1/repo"; [ -z "${2:-}" ] || printf '%s\n%s\n' "$2" "${3:-}" > "$W9/$1/t3-thread"; }  # file://: no git object hard-linked across folders aged apart
mk deleted del-1; mk settled set-1; mk autoset aset-1; mk archived arc-1; mk liveold live-1; mk liveyoung live-2; mk live live-3; mk noold; mk noyoung; mk busy del-2; mk fresh del-3; mk lender del-4; mk unknown err-1; mk steward del-9; mk t3dir live-4; mk noanswer err-2; mk watched del-6
mkdir -p "$W9/notfound"; echo nf-1 > "$W9/notfound/t3-gone"
echo x > "$W9/deleted/repo/notes.txt"; G -C "$W9/deleted/repo" commit -q --allow-empty -m 'only here'  # an uncommitted file and a commit on no remote
G -C "$W9/lender/repo" worktree add -q -b side "$T/lent-wt"
G clone -q "$T/w-origin.git" "$T/user9"; mkdir -p "$W9/fix"; echo del-5 > "$W9/fix/t3-thread"; G -C "$T/user9" worktree add -q -b fix-1 "$W9/fix/fix-1" origin/main
for n in live; do mkdir -p "$W9/$n/repo/node_modules" "$W9/$n/drafts/node_modules"; echo x > "$W9/$n/repo/node_modules/x"; echo x > "$W9/$n/drafts/node_modules/x"; done
for n in settled autoset archived liveold liveyoung noold noyoung t3dir noanswer; do date -u -d '20 days ago' +%FT%TZ > "$W9/$n/retired"; done
find "$W9" -exec touch -h -d '9 days ago' {} +; find "$W9/liveyoung" "$W9/noyoung" -exec touch -h -d '7 days ago' {} +
YOUNG=$(date -u -d "@$(( $(stat -c %Y "$W9/noyoung/repo/.gitignore") + 8 * 86400 ))" +%FT%TZ)
mkdir -p "$W9/t3dir/t3-carry" "$W9/t3dir/gh-watch-fix"; echo 999999999 > "$W9/t3dir/gh-watch.pid"
echo x > "$W9/t3dir/t3-carry/fix.py"; echo x > "$W9/t3dir/gh-watch-fix/fix.py"; touch -d '3 days ago' "$W9/t3dir/t3-carry/fix.py" "$W9/t3dir/gh-watch-fix/fix.py"  # checkouts with a watcher file's name, edited 3 days ago
echo 999999999 > "$W9/noold/gh-watch.pid"; : > "$W9/noold/events.log"; : > "$W9/noold/gh-watch-state.json"  # a stopped watcher's files, written now
touch "$W9/fresh/repo/README"; bash -c "cd '$W9/busy' && exec sleep 600" & BUSY=$!
bash -c "cd '$W9/watched' && exec sleep 600" & WATCH=$!; sleep 0.2; echo "$WATCH" > "$W9/watched/gh-watch.pid"; : > "$W9/watched/gh-watch-state.json"  # its watcher, not yet stopped
HOME="$H9" python3 "$R/bin/disk-sweep" > "$T/dry9.out" 2>&1
check "a dry run prints w-done's deletions and the kept folders' rows, and deletes nothing" "1 1 kept no" "$(grep -c "^[^ ]* [0-9][0-9]* $W9/notfound w-done$" "$T/dry9.out") $(grep -c "^- $W9/settled: " "$T/dry9.out") $(there "$W9/notfound") $([ -e "$H9/.mergeworthy/work-kept.md" ] && echo yes || echo no)"
HOME="$H9" python3 "$R/bin/disk-sweep" --delete > "$T/run9.out" 2>&1
KEPT="$H9/.mergeworthy/work-kept.md"; row() { grep -cx -- "- $W9/$1: $2" "$KEPT"; }
check "w-done deletes the folder of a thread T3 deleted, its uncommitted file and local-only commit with it, logged before and after" "removed deleting|deleted|" "$(there "$W9/deleted") $(grep "^[^ ]* [0-9][0-9]* $W9/deleted w-done " "$H9/.mergeworthy/disk-sweep.log" | cut -d' ' -f5 | tr '\n' '|')"
check "the sweep stops no watcher: a deleted thread's folder whose watcher still runs there stays this run, its row naming it busy, the watcher alive" "kept 1 alive" "$(there "$W9/watched") $(row watched 'a process or agent job works in it') $(kill -0 "$WATCH" 2>/dev/null && echo alive || echo gone)"
check "a thread T3's database has no row for (here in t3-gone) is deleted too" removed "$(there "$W9/notfound")"
check "a settled thread (settledOverride, or only a settledAt as T3 auto-settles) or an archived one keeps its folder, its row saying T3 decides" "kept kept kept 1 1 1" "$(there "$W9/settled") $(there "$W9/autoset") $(there "$W9/archived") $(row settled 'its T3 thread is settled or archived; it goes once T3 deletes the thread') $(row autoset 'its T3 thread is settled or archived; it goes once T3 deletes the thread') $(row archived 'its T3 thread is settled or archived; it goes once T3 deletes the thread')"
check "a retired folder untouched for 8 days goes, with a live thread or none, its watcher's fresh files aside; 7 days stays, its row naming the date" "removed removed kept kept 1" "$(there "$W9/liveold") $(there "$W9/noold") $(there "$W9/liveyoung") $(there "$W9/noyoung") $(row noyoung "its watcher retired; deleted no sooner than $YOUNG if left untouched")"
check "a retired folder whose checkouts are named t3-* and gh-watch* stays 8 days after their edit: only the watcher's own top-level files are aside" "kept 1" "$(there "$W9/t3dir") $(grep -c "^- $W9/t3dir: its watcher retired; deleted no sooner than " "$KEPT")"
check "a retired folder whose thread T3's database can't answer about stays this run, its row saying so" "kept 1" "$(there "$W9/noanswer") $(row noanswer 'T3 gave no answer about its thread; kept this run')"
check "a live thread without a retired watcher keeps its folder, with no row; c-ignored and c-node_modules sweep its build folders" "kept 0 removed removed" "$(there "$W9/live/repo") $(grep -c "$W9/live:" "$KEPT") $(there "$W9/live/repo/node_modules") $(there "$W9/live/drafts/node_modules")"
check "a deleted thread's folder stays while a process works in it or a file changed in 24 hours, its row naming the cause" "kept 1 kept 1" "$(there "$W9/busy") $(row busy 'a process or agent job works in it') $(there "$W9/fresh") $(row fresh 'a file changed in the last 24 hours')"
check "a folder whose repo has a worktree outside it stays, its row naming it" "kept 1" "$(there "$W9/lender") $(row lender "$W9/lender/repo: its worktree $(readlink -f "$T")/lent-wt is outside the folder")"
check "an unretired folder T3's database can't answer about and the steward's folder keep theirs, with no row" "kept kept 0" "$(there "$W9/unknown") $(there "$W9/steward") $(grep -c "$W9/unknown:\|$W9/steward:" "$KEPT")"
check "a folder whose check fails stays with that reason, and the next folders are still checked" 2 \
  "$(HOME="$H9" dsm 'm.DRY = True; real = m.thread_state; m.thread_state = lambda f: 1 / 0 if f.endswith("/archived") else real(f); m.sweep_work()' | grep -c "^- $W9/archived: check failed: division by zero$\|^- $W9/settled: its T3")"
check "a deleted folder's worktree of a repo outside: that repo's entry is pruned, so its branch can be checked out there" "removed 1 0" "$(there "$W9/fix") $(G -C "$T/user9" worktree list | wc -l) $(G -C "$T/user9" switch -q fix-1 2>&1 | wc -l)"
check "the deleting run's rows are the dry run's" same "$([ "$(grep '^- ' "$T/dry9.out")" = "$(grep '^- ' "$KEPT")" ] && echo same)"
ln -s "$W9" "$T/w9link"
check "delete() through a symlinked path deletes nothing and says why" "a symlink on its path kept" "$(dsm 'm.DRY = False; p = sys.argv[3]; print(m.delete(p, p, os.lstat(p).st_dev, "w-done", vcs=False))' "$T/w9link/settled") $(there "$W9/settled")"
kill "$BUSY" "$WATCH"; wait "$BUSY" "$WATCH" 2>/dev/null
rm "$H9/.mergeworthy/disk-sweep.work"; HOME="$H9" python3 "$R/bin/disk-sweep" --delete > /dev/null 2>&1
check "once the watcher stopped itself, the next day's sweep deletes the folder" removed "$(there "$W9/watched")"

# c-ignored: Rust's target, a project's .pnpm-store, .venv and .mypy_cache go when git ignores them, and stay when it tracks them
HB="$T/homeb"; B="$HB/b-work"; mkdir -p "$HB/.mergeworthy"
for n in ign trk; do G init -q "$B/$n"; for d in target .pnpm-store .venv .mypy_cache; do mkdir -p "$B/$n/$d"; echo x > "$B/$n/$d/f"; done; done
printf 'target/\n.pnpm-store/\n.venv/\n.mypy_cache/\n' > "$B/ign/.gitignore"; G -C "$B/ign" add .gitignore; G -C "$B/ign" commit -qm base; G -C "$B/trk" add -A; G -C "$B/trk" commit -qm base; age "$B"
HOME="$HB" python3 "$R/bin/disk-sweep" --delete 2>/dev/null
check "c-ignored deletes an ignored target, .pnpm-store, .venv and .mypy_cache, and keeps tracked ones" "removed removed removed removed kept kept kept kept" "$(for n in ign trk; do for d in target .pnpm-store .venv .mypy_cache; do there "$B/$n/$d"; done; done | tr '\n' ' ' | sed 's/ $//')"

# w-merged: the steward's worktrees whose branch is merged, or squash-merged as GitHub shows, go after 8 untouched days with their notes
HS="$T/homes"; S="$HS/.mergeworthy/work/steward"; mkdir -p "$S" "$HS/.claude/agent-jobs"
G init -q --bare -b main "$T/s-origin.git"; git config -f "$HS/.gitconfig" url."$T/s-origin.git".insteadOf https://github.com/o/s.git
HOME="$HS" G clone -q https://github.com/o/s.git "$S/repo" 2>/dev/null; echo a > "$S/repo/f"; G -C "$S/repo" add f; G -C "$S/repo" commit -qm base; HOME="$HS" G -C "$S/repo" push -q origin main
for n in merged squashed open recent busy nopr mdirty; do G -C "$S/repo" worktree add -q -b "$n" "$S/$n" main; G -C "$S/$n" commit -q --allow-empty -m "$n"; mkdir -p "$S/$n-notes"; echo x > "$S/$n-notes/r.md"; done
for n in held helddirty; do G -C "$S/repo" worktree add -q -b "$n" "$S/$n" main; done; echo b > "$S/helddirty/f"; echo b > "$S/mdirty/f"  # never committed; an edited tracked file
G -C "$S/repo" merge -q --no-ff --no-edit merged recent busy mdirty >/dev/null; G -C "$S/repo" commit -q --allow-empty -m later  # a merge commit, as GitHub makes
HOME="$HS" G -C "$S/repo" push -q origin main
HOME="$HS" G -C "$S/open" push -q origin open; HOME="$HS" G -C "$S/repo" fetch -q origin
SQ=$(G -C "$S/squashed" rev-parse HEAD)
printf '#!/bin/sh\n# stub gh: `gh api repos/o/s/commits/<sha>/pulls`: a merged PR headed at the squashed worktree'"'"'s tip, none for any other\ncase "$2" in */%s/pulls) echo '"'"'[{"merged_at":"2026-01-01T00:00:00Z","head":{"sha":"%s"}}]'"'"';; *) echo "[]";; esac\n' "$SQ" "$SQ" > "$T/bin/gh"
chmod +x "$T/bin/gh"; find "$S" -exec touch -h -d '9 days ago' {} +; touch -d '2 days ago' "$S/recent-notes/r.md"
bash -c "cd '$S/busy' && exec sleep 600" & SB=$!; sleep 0.2
HOME="$HS" python3 "$R/bin/disk-sweep" --delete 2>/dev/null; kill "$SB"; wait "$SB" 2>/dev/null
check "w-merged keeps a worktree that never got a commit of its own (on main's line), clean or with an edited tracked file, and a merged one with an uncommitted edit" \
  "kept kept kept 3" "$(there "$S/held") $(there "$S/helddirty") $(there "$S/mdirty") $(G -C "$S/repo" branch --list held helddirty mdirty | wc -l)"
check "w-merged: a merged and a squash-merged worktree go with their notes and branches, logged; unmerged, a PR GitHub doesn't show, notes touched 2 days ago or a process working there keep theirs" \
  "removed removed removed removed 0 4 kept kept kept kept" \
  "$(there "$S/merged") $(there "$S/merged-notes") $(there "$S/squashed") $(there "$S/squashed-notes") $(G -C "$S/repo" branch --list merged squashed | wc -l) $(grep -c ' w-merged deleted$' "$HS/.mergeworthy/disk-sweep.log") $(there "$S/open") $(there "$S/nopr") $(there "$S/recent") $(there "$S/busy")"

# tests/all.sh, on a root whose first suite leaves a child that calls docker after the suite exits
F="$T/allsh"; mkdir -p "$F/node_modules/typescript" "$F/cli/node_modules" "$F/docs" "$F/tests"; cp -r "$R/tests/refuse" "$F/tests/"
echo 'import subprocess; subprocess.Popen(["sh", "-c", "sleep 0.5; docker version"])' > "$F/docs/build-graphs.py"
bash "$R/tests/all.sh" "$F" > /dev/null 2> "$T/allsh.err"
check "tests/all.sh fails a suite whose child calls docker after the suite exited" "1 1" "$? $(grep -c 'called docker' "$T/allsh.err")"
echo 'import subprocess; subprocess.Popen(["sh", "-c", "sleep 0.5; docker version"], start_new_session=True)' > "$F/docs/build-graphs.py"
bash "$R/tests/all.sh" "$F" > /dev/null 2> "$T/allsh.err"
check "tests/all.sh fails a suite whose child in a session of its own calls docker after the suite exited" "1 1" "$? $(grep -c 'called docker' "$T/allsh.err")"

kill "$SPID" "$WPID"; wait "$SPID" "$WPID" 2>/dev/null
rm -rf "$T"
echo "failures: $fails"; [ "$fails" = 0 ]
