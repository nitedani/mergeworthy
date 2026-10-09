#!/usr/bin/env bash
# Tests for the hooks: stop-lint, pre-bash-guard's check_turn, post-bash-register. Usage: tests/hooks.sh <repo root>
# Runs every case under a temp HOME with a stub `gh` first on PATH; prints "case: <got> (want <want>)".
# Exits 0 only when every case gives what it wants. Stub URLs are example.invalid on purpose, except where
# post-bash-register must see github.com URLs (those go only into the hook's stdin, never to this script's output).
set -u
R=$(readlink -f "$1")
T=$(mktemp -d); export HOME="$T/home"; mkdir -p "$HOME/.claude" "$T/bin" "$T/fx"
cat > "$T/bin/gh" <<'EOF'
#!/usr/bin/env bash
# stub gh: answers `gh api <path>` from $FX/<path with / ? & = replaced by _>; exit 1 when the fixture is missing (a 404)
[ "$1" = api ] || exit 1
f="$FX/$(printf '%s' "$2" | tr '/?&=' '____')"
[ -f "$f" ] && cat "$f" || { echo 'gh: Not Found (HTTP 404)' >&2; exit 1; }
EOF
chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH" FX="$T/fx"
fails=0
check() { # name want got
  echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1))
}

# ---------- stop-lint ----------
sleep 600 & SPID=$!
WD="$T/work/x"; mkdir -p "$WD" "$T/work/x-2/sub" "$WD/sub"
echo "$SPID" > "$WD/gh-watch.pid"
echo "$WD" > "$HOME/.claude/gh-watch-dirs.txt"
tr_file() { # final assistant text
  python3 -c 'import json,sys; print(json.dumps({"type":"user","message":{"content":"tidy up the README"}})); print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":sys.argv[1]}]}}))' "$1" > "$T/tr.jsonl"
}
stop() { # cwd (the other checks; the check-in has its own test)
  python3 -c 'import json,sys; print(json.dumps({"transcript_path":sys.argv[1],"cwd":sys.argv[2]}))' "$T/tr.jsonl" "$1" \
    | MERGEWORTHY_STOP_CHECKIN=off python3 "$R/hooks/stop-lint.py" 2>"$T/err"; echo $?
}
checkin() { # stop_hook_active
  python3 -c 'import json,sys; print(json.dumps({"transcript_path":sys.argv[1],"cwd":sys.argv[2],"stop_hook_active":sys.argv[3]=="1"}))' "$T/tr.jsonl" "$T" "$1" \
    | MERGEWORTHY_STOP_CHECKIN=on python3 "$R/hooks/stop-lint.py" 2>"$T/err"; echo $?
}
tr_file "Loop A is done."
check "the first stop of a turn gets the check-in" 2 "$(checkin 0)"
check "the next stop goes through" 0 "$(checkin 1)"
python3 -c 'import json; print(json.dumps({"type":"user","message":{"content":"Act as the review sub-agent for this task.\n\nCheck the diff."}})); print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":"CLEAN"}]}}))' > "$T/tr.jsonl"
check "a delegated child ends with its result, no check-in" 0 "$(checkin 0)"
tr_file "The watcher runs and the Monitor is armed."
check "no replies-owed.md, cwd=watch dir" 0 "$(stop "$WD")"
echo "o/r 1 comment 42 by someone" > "$WD/replies-owed.md"
check "control: open owed line, cwd=watch dir" 2 "$(stop "$WD")"
check "control: open owed line, cwd=inside watch dir" 2 "$(stop "$WD/sub")"
echo "holding: https://github.com/o/r/issues/1#issuecomment-9 $(date -u -d '+1 hour' +%FT%TZ)" > "$WD/replies-owed.md"
check "a holding line whose ETA is ahead passes" 0 "$(stop "$WD")"
echo "holding: https://github.com/o/r/issues/1#issuecomment-9 $(date -u -d '-1 hour' +%FT%TZ)" > "$WD/replies-owed.md"
check "BLOCK: a holding line past its ETA is owed again" 2 "$(stop "$WD")"
echo "drafting: https://github.com/o/r/issues/1#issuecomment-9 $(date -u -d '+1 hour' +%FT%TZ)" > "$WD/replies-owed.md"
check "a drafting line whose ETA is ahead passes" 0 "$(stop "$WD")"
echo "drafting: https://github.com/o/r/issues/1#issuecomment-9 $(date -u -d '-1 hour' +%FT%TZ)" > "$WD/replies-owed.md"
check "BLOCK: a drafting line past its ETA is owed again" 2 "$(stop "$WD")"
echo "o/r 1 comment 42 by someone" > "$WD/replies-owed.md"
tr_file "README tidied."
check "open owed line, cwd=parent of watch dir" 0 "$(stop "$T/work")"
check "open owed line, cwd=prefix sibling x-2" 0 "$(stop "$T/work/x-2/sub")"
tr_cmd() { # a Bash command the session ran, then the final text
  python3 -c 'import json,sys; print(json.dumps({"type":"user","message":{"content":"go"}})); print(json.dumps({"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","id":"t1","input":{"command":sys.argv[1]}}]}})); print(json.dumps({"type":"assistant","message":{"content":[{"type":"text","text":"Done."}]}}))' "$1" > "$T/tr.jsonl"
}
tr_cmd "ls $WD && grep -n gate-pass notes.md"
check "a session that only mentioned the watch dir doesn't own its owed replies" 0 "$(stop "$T/work")"
tr_cmd "gate-pass $WD/drafts/r.md $WD/drafts/r.review.out"
check "BLOCK: a session that gate-passed a draft there owns them" 2 "$(stop "$T/work")"
tr_cmd "gh api graphql -f query='query(\$n:Int!){repository(owner:\"o\",name:\"r\"){issue(number:\$n){body}}}' -F n=49"
check "a GraphQL query is a read, not a post" 0 "$(stop "$T/work")"
tr_cmd "gh api repos/o/r/issues -X GET -F per_page=100"
check "an explicit GET with fields is a read" 0 "$(stop "$T/work")"
tr_cmd "gh issue comment 5 --repo o/r --body-file $WD/drafts/r.md"
check "BLOCK: a post with no Monitor on the watcher" 2 "$(stop "$T/work")"
kill "$SPID"; wait "$SPID" 2>/dev/null

# ---------- pre-bash-guard check_turn ----------
D="$T/drafts"; mkdir -p "$D"
gate() { printf '%s\n' "$2" > "$D/$1.md"; sha256sum "$D/$1.md" | cut -d' ' -f1 > "$D/$1.md.gate"
         python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1]).read().replace("\r\n","\n").strip().encode()).hexdigest())' "$D/$1.md" >> "$HOME/.claude/gated-posts.txt"; }
gate a1 "Agent comment one."
gate a2 "Agent comment two."
gate new "Agent answer."
now=$(date -u +%Y-%m-%dT%H:%M:%SZ); old=$(date -u -d '-4 hours' +%Y-%m-%dT%H:%M:%SZ); hour=$(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%SZ)
comments() { # body1 body2 created2
  echo 2 > "$FX/repos_o_r_issues_5"
  python3 -c 'import json,sys; print(json.dumps([{"body":sys.argv[1],"created":sys.argv[3],"url":"https://example.invalid/c1"},{"body":sys.argv[2],"created":sys.argv[3],"url":"https://example.invalid/c2"}]))' \
    "$1" "$2" "$3" > "$FX/repos_o_r_issues_5_comments_per_page_100_page_1"
}
guard() { # extra args
  rm -f "$D/new.md.posted"
  python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":" ".join(["gh","issue","comment","5","--repo","o/r","--body-file",sys.argv[2]]+sys.argv[3:])},"cwd":sys.argv[1]}))' "$T" "$D/new.md" "$@" > "$T/in.json"
  python3 "$R/hooks/pre-bash-guard.py" < "$T/in.json" 2>"$T/err"; echo $?
}
A1="Agent comment one."; A2="Agent comment two."
comments "$A1" "/ai please also cover the edge case" "$now"
check "last comment is the user's own (same login, not gated)" 0 "$(guard)"
comments "Maintainer question" "$A2" "$now"
check "only the last comment is the agent's" 0 "$(guard)"
comments "$A1" "$A2" "$now"
date -u -d '+1 minute' +%Y-%m-%dT%H:%M:%SZ > "$FX/repos_o_r_pulls_5_reviews_per_page_100"
check "last two are the agent's but a review came after" 0 "$(guard)"
rm "$FX/repos_o_r_pulls_5_reviews_per_page_100"
check "--help on a comment command" 0 "$(guard --help)"
comments "$A1" "$A2" "$old"
check "last two are the agent's, last is 4 hours old (wait ping)" 0 "$(guard)"
comments "$A1" "$A2" "$hour"
check "BLOCK: last two are the agent's, last is 1 hour old" 2 "$(guard)"
comments "$A1" "$A2" "$now"
check "BLOCK: last two are the agent's gated posts, recent, no review (issue 404)" 2 "$(guard)"
echo nitedani > "$FX/user"
date -u -d '+1 minute' +'maint %Y-%m-%dT%H:%M:%SZ' > "$FX/repos_o_r_pulls_5_commits_per_page_100"
check "a maintainer's push after the last two comments counts as a reply" 0 "$(guard)"
date -u -d '+1 minute' +'nitedani %Y-%m-%dT%H:%M:%SZ' > "$FX/repos_o_r_pulls_5_commits_per_page_100"
check "BLOCK: your own push is not a reply" 2 "$(guard)"
rm -f "$FX/repos_o_r_pulls_5_commits_per_page_100" "$FX/user"
grep -o 'your last two comments.*' "$T/err" | sed 's#https\?://[^ )]*#<url>#'

# ---------- post-bash-register: only a real gh post registers, and only the thread it posted to ----------
sleep 600 & SPID=$!
WD="$T/reg"; mkdir -p "$WD"; echo "$SPID" > "$WD/gh-watch.pid"
echo "$WD" > "$HOME/.claude/gh-watch-dirs.txt"
U5='https://github.com/o/r/issues/5#issuecomment-1'
register() { # command stdout -> the watch dir's threads.txt, space-joined
  rm -f "$WD/threads.txt"
  python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]},"tool_response":{"stdout":sys.argv[2]}}))' "$1" "$2" \
    | python3 "$R/hooks/post-bash-register.py"
  [ -f "$WD/threads.txt" ] && paste -sd' ' "$WD/threads.txt" || echo none
}
printf 'The posted body, with ![shot](https://user-images.example/1.png)' > "$FX/repos_o_r_issues_comments_77"
register "gh issue comment 5 --repo o/r --body-file /x/d.md --attach /x/1.png" 'https://github.com/o/r/issues/5#issuecomment-77' >/dev/null
want=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1]).read().strip().encode()).hexdigest())' "$FX/repos_o_r_issues_comments_77")
check "the body actually posted (after --attach) is registered as the agent's" 1 "$(grep -c "$want" "$HOME/.claude/gated-posts.txt")"
check "printf that mentions a comment command, URL in output" none \
  "$(register "printf '%s' 'gh issue comment 5 --repo o/r' > in.json; python3 hook.py < in.json" "$U5")"
check "grep for a comment command, URL in output" none \
  "$(register "grep -rn 'gh issue comment 5 --repo o/r' ." "x.md: $U5")"
check "real gh issue comment" "o/r 5" \
  "$(register "gh issue comment 5 --repo o/r --body-file x" "$U5")"
check "real gh issue comment, another thread's URL also printed" "o/r 5" \
  "$(register "gh issue comment 5 --repo o/r --body-file x && cat log" "$U5 https://github.com/o/r/issues/6 https://github.com/p/q/pull/5")"
check "real gh pr create, number not named" "o/r 7" \
  "$(register "gh pr create --repo o/r --fill" "https://github.com/o/r/pull/7")"
check "gh api POST comment" "o/r 5" \
  "$(register "gh api repos/o/r/issues/5/comments -F body=@x.md" "{\"html_url\": \"$U5\"}")"
check "gh api read (-X GET with fields)" none \
  "$(register "gh api -X GET repos/o/r/issues -f state=open" "$U5")"
check "gh --help on a comment command" none \
  "$(register "gh issue comment 5 --repo o/r --help" "$U5")"
kill "$SPID"; wait "$SPID" 2>/dev/null

# ---------- finality trigger: the third proposal on a thread needs a thread map ----------
AR="$T/art"; mkdir -p "$AR/drafts/r1" "$AR/maps"
rm -f "$HOME/.claude/proposal-rounds.txt"
prop() { # n: a gated proposal draft, as gate-pass leaves it
  printf 'Proposal %s\n' "$1" > "$AR/drafts/r1/p$1.md"; sha256sum "$AR/drafts/r1/p$1.md" | cut -d' ' -f1 > "$AR/drafts/r1/p$1.md.gate"
  echo "--kind proposal --repo o/r --parent none" > "$AR/drafts/r1/p$1.md.lint"
}
pguard() { # n -> exit code of the pre-bash-guard on posting proposal n to o/r#9
  python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":"gh issue comment 9 --repo o/r --body-file "+sys.argv[1]},"cwd":sys.argv[2]}))' "$AR/drafts/r1/p$1.md" "$T" \
    | python3 "$R/hooks/pre-bash-guard.py" 2>"$T/err"; echo $?
}
pposted() { python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":"gh issue comment 9 --repo o/r --body-file "+sys.argv[1]},"tool_response":{"stdout":"https://example.invalid/x"}}))' "$AR/drafts/r1/p$1.md" \
    | python3 "$R/hooks/post-bash-register.py"; }
for n in 1 2 3; do prop $n; done
check "the 1st proposal passes" 0 "$(pguard 1)"; pposted 1
check "the 2nd proposal passes" 0 "$(pguard 2)"; pposted 2
check "BLOCK: the 3rd proposal without a thread map" 2 "$(pguard 3)"
grep -o 'maps/[^ ]*' "$T/err" | head -1
touch -d '+1 minute' "$AR/maps/o-r-9.md"
check "the 3rd proposal with a fresh map passes" 0 "$(pguard 3)"
touch -d '-1 hour' "$AR/maps/o-r-9.md"
check "BLOCK: a map older than the last proposal" 2 "$(pguard 3)"
# ---------- post-lint: the badge is icons, then a line break ----------
blint() { printf '%s' "$1" > "$T/badge.md"; python3 "$R/bin/post-lint" "$T/badge.md" --parent none 2>&1 | grep -c 'badge'; }
check "icons then a line break pass" 0 "$(blint $'<img src="https://github.com/claude.png" width="20" height="20" alt="Claude"> <img src="https://github.com/openai.png" width="20" height="20" alt="Codex">\nFixed in abc1234.\n')"
check "a **Claude:** label is flagged" 1 "$(blint $'<img src="https://github.com/claude.png" width="20" height="20" alt="Claude"> **Claude:** Fixed in abc1234.\n')"
check "no badge is flagged" 1 "$(blint $'Fixed in abc1234.\n')"
# ---------- post-lint: each list item is its own sentence ----------
B=$'<img src="https://github.com/claude.png" width="20" height="20" alt="Claude">\n'
lint() { python3 "$R/bin/post-lint" "$1" --kind issue --parent none 2>&1 | grep -c 'word sentence'; }
items=$(for i in 1 2 3 4 5 6 7; do echo "  - item number $i with a few short words;"; done)
printf '%s A list of short items follows here:\n%s\n' "$B" "$items" > "$T/list.md"
check "a list of short items: no long sentence" 0 "$(lint "$T/list.md")"
printf '%s A list follows:\n- %s\n' "$B" "$(printf 'word %.0s' $(seq 45))" > "$T/long.md"
check "one list item over 40 words is flagged" 1 "$(lint "$T/long.md")"
printf '%s The spec now warns for W2 and W5.\n' "$B" > "$T/lab.md"
check "an internal label is flagged" 2 "$(python3 "$R/bin/post-lint" "$T/lab.md" --kind issue --parent none 2>&1 | grep -c 'internal label')"
printf '%s The build is uploaded to S3 and served from Cloudflare R2 on my M2 Mac.\n' "$B" > "$T/lab2.md"
check "product names like S3, R2 and M2 are not labels" 0 "$(python3 "$R/bin/post-lint" "$T/lab2.md" --kind issue --parent none 2>&1 | grep -c 'internal label')"
printf '%s Two answers follow.\n\n- **Fetch pipeline:** not needed.\n- **The option:** it stays private, as you asked, under its current name.\n' "$B" > "$T/frag.md"
check "a bold label with a fragment is flagged, a full sentence is not" 1 "$(python3 "$R/bin/post-lint" "$T/frag.md" --kind issue --parent none 2>&1 | grep -c 'bold label with a fragment')"
mkdir -p "$T/cx"; printf '%s Fixed in abc1234.\n' "$B" > "$T/cx/reply.md"; printf 'model: gpt-x\nCLEAN\n' > "$T/cx/review.log"
check "a post Codex reviewed needs the Codex icon" 1 "$(python3 "$R/bin/post-lint" "$T/cx/reply.md" --parent none 2>&1 | grep -c 'badge without Codex')"
printf '<img src="https://github.com/claude.png" width="20" height="20" alt="Claude"><img src="https://github.com/openai.png" width="20" height="20" alt="Codex">\n\nFixed in abc1234.\n' > "$T/cx/reply.md"
check "with the Codex icon it passes" 0 "$(python3 "$R/bin/post-lint" "$T/cx/reply.md" --parent none 2>&1 | grep -c 'badge without Codex')"
printf 'Refactor this PR. Print the lists again with old rating => new rating.\n' > "$T/rp.parent.md"
printf '%s Done, the lists are below.\n\n<details>\n<summary>Lists</summary>\n\nS1 and S2 were rated in the refactor pass. %s\n</details>\n' "$B" "$(printf 'word %.0s' $(seq 400))" > "$T/rp.md"
check "lists a maintainer asked for, in <details>, are not linted or counted" 0 "$(python3 "$R/bin/post-lint" "$T/rp.md" --kind pr --parent "$T/rp.parent.md" 2>&1 | grep -c 'internal label\|words >\|process in the thread')"
check "the same lists nobody asked for are" 4 "$(python3 "$R/bin/post-lint" "$T/rp.md" --kind pr --parent none 2>&1 | grep -c 'internal label\|words >\|process in the thread')"
printf '%s #3557 follows the rule you agreed to, with the proxy inside.\n' "$B" > "$T/cr.md"
check "an agreement credited without a link is flagged" 1 "$(python3 "$R/bin/post-lint" "$T/cr.md" --parent none 2>&1 | grep -c 'credit without a link')"
printf '%s #3557 follows the rule you agreed to ([here](https://github.com/o/r/issues/1#issuecomment-2)).\n' "$B" > "$T/cr2.md"
check "with a link it passes" 0 "$(python3 "$R/bin/post-lint" "$T/cr2.md" --parent none 2>&1 | grep -c 'credit without a link')"
printf '%s Done: eight commits, none changing behavior.\n\nOne change I didn'"'"'t make: the handler stays.\n' "$B" > "$T/lbl.md"
check "a label opening a sentence is flagged" 2 "$(python3 "$R/bin/post-lint" "$T/lbl.md" --parent none 2>&1 | grep -c 'a label opening a sentence')"
printf '%s I landed eight commits at 14:52, and here is the plan I see:\n\n1. Fix it.\n' "$B" > "$T/lbl2.md"
check "a time, or a colon before a list, is not a label" 0 "$(python3 "$R/bin/post-lint" "$T/lbl2.md" --parent none 2>&1 | grep -c 'a label opening a sentence')"
printf '%s Fixes the leak.\n\n<details>\n<summary>Refactor pass, run 2 (head abc1234)</summary>\n\nS1 and S2. %s\n</details>\n' "$B" "$(printf 'word %.0s' $(seq 300))" > "$T/rpb.md"
check "the converge steps' runs collapsed in a PR body are not linted or counted" 0 "$(python3 "$R/bin/post-lint" "$T/rpb.md" --kind pr --parent none 2>&1 | grep -c 'internal label\|words >')"
printf '%s Draft until the release ships.\n\nThe fix.\n' "$B" > "$T/st.md"
check "a PR body that opens with its status is flagged" 1 "$(python3 "$R/bin/post-lint" "$T/st.md" --kind pr --parent none 2>&1 | grep -c 'opens with its status')"
printf '%s Routes after vike(app) skip the auth +middleware. This PR runs it first.\n\nDraft until the release ships.\n' "$B" > "$T/st2.md"
check "status after the opening is fine" 0 "$(python3 "$R/bin/post-lint" "$T/st2.md" --kind pr --parent none 2>&1 | grep -c 'opens with its status')"
printf '%s Two fundamental issues remain.\n' "$B" > "$T/fund.md"
check "a difficulty word without its scope is flagged" 1 "$(python3 "$R/bin/post-lint" "$T/fund.md" --kind issue --parent none 2>&1 | grep -c 'what it.s hard for')"
# the budget grows with the questions in the comment answered
printf 'One? Two? Three?\n' > "$T/q.parent.md"
printf '%s %s\n' "$B" "$(printf 'word %.0s' $(seq 350))" > "$T/q.md"
check "a reply of 350 words is over the ceiling, however many questions" 1 "$(python3 "$R/bin/post-lint" "$T/q.md" --parent "$T/q.parent.md" 2>&1 | grep -c 'for a reply')"
printf 'One?\n' > "$T/q1.parent.md"
check "the same reply to one question is over budget" 1 "$(python3 "$R/bin/post-lint" "$T/q.md" --parent "$T/q1.parent.md" 2>&1 | grep -c 'for a reply')"
printf 'See https://x.io/a?b=1 and https://x.io/c?d=2.\n```\na ? b : c ? d : e\n```\nOK?\n' > "$T/q2.parent.md"
check "question marks in URLs and code don't count" 1 "$(python3 "$R/bin/post-lint" "$T/q.md" --parent "$T/q2.parent.md" 2>&1 | grep -c 'for a reply')"
cp "$T/q.parent.md" "$T/q3.parent.md"; cp "$T/q.md" "$T/q3.md"
check "--parent none ignores a parent file next to the draft" 1 "$(python3 "$R/bin/post-lint" "$T/q3.md" --parent none 2>&1 | grep -c 'for a reply')"
for s in 'Fundamental problems remain in this design.' 'It is impossible to fix this.' 'The fix is impossible.'; do
  printf '%s %s\n' "$B" "$s" > "$T/fund3.md"
  check "flagged: $s" 1 "$(python3 "$R/bin/post-lint" "$T/fund3.md" --kind issue --parent none 2>&1 | grep -c 'what it.s hard for')"
done
for s in 'This fundamentally changes the public API.' 'The guard covers an impossible state.' 'A fundamental issue for the adapter remains.'; do
  printf '%s %s\n' "$B" "$s" > "$T/fund3.md"
  check "passes: $s" 0 "$(python3 "$R/bin/post-lint" "$T/fund3.md" --kind issue --parent none 2>&1 | grep -c 'what it.s hard for')"
done
printf '%s A problem fundamental to one injection point; "fundamental" was the wrong word.\n' "$B" > "$T/fund2.md"
check "a scoped or quoted difficulty word passes" 0 "$(python3 "$R/bin/post-lint" "$T/fund2.md" --kind issue --parent none 2>&1 | grep -c 'what it.s hard for')"
# ---------- post-lint: an issue a newcomer can find (open-issue, evidence) ----------
ilint() { python3 "$R/bin/post-lint" "$1" --kind issue --parent none 2>&1 | grep -c "$2"; }
printf '%s The invoice keeps the winning account, not the typed one.\n' "$B" > "$T/i0.md"
check "a badge alone is no evidence" 1 "$(ilint "$T/i0.md" 'no evidence')"
check "an issue needs How to reproduce" 1 "$(ilint "$T/i0.md" 'no .### How to reproduce')"
printf '%s The list shows the winning account.\n\n### How to reproduce\n\n1. Log in as a manager, open /invoices\n2. See the account column\n\n![list](/abs/list.png)\n' "$B" > "$T/i1.md"
check "one screen in a screenshot passes" 0 "$(python3 "$R/bin/post-lint" "$T/i1.md" --kind issue --parent none 2>&1 | grep -c 'evidence\|How to reproduce\|video')"
printf '%s The saved invoice drops the typed account.\n\n### How to reproduce\n\n1. Log in as a manager\n2. Open a won job\n3. Create an invoice with another account\n4. Save, then see the list\n\n![list](/abs/list.png)\n' "$B" > "$T/i2.md"
check "a multi-step flow in stills needs a video" 1 "$(ilint "$T/i2.md" 'record a video')"
sed 's#/abs/list.png#/abs/flow.mp4#' "$T/i2.md" > "$T/i3.md"
check "the flow as a video passes" 0 "$(ilint "$T/i3.md" 'video\|evidence')"
printf '%s CI runs no tests.\n\n### How to reproduce\n\n1. Run the backend tests\n\n```\n$ pnpm test\nUnknown option --threads\n```\n' "$B" > "$T/i4.md"
check "no screen: the command and output pass" 0 "$(ilint "$T/i4.md" 'evidence')"
{ printf '%s Who picks the payout account?\n\n### How to reproduce\n\n1. Open /invoices\n\n![list](/abs/list.png)\n\n### Options\n\n' "$B"; printf 'word %.0s' $(seq 120); echo; } > "$T/i5.md"
check "a decision issue gets a word budget, not 400 characters" 0 "$(ilint "$T/i5.md" 'for an issue\|decision issue')"
# ---------- pre-bash-guard: no foreground waits ----------
wait_guard() { # command background(true|false)
  python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1],"run_in_background":sys.argv[2]=="true"},"cwd":sys.argv[3]}))' "$1" "$2" "$T" \
    | python3 "$R/hooks/pre-bash-guard.py" 2>/dev/null; echo $?
}
check "BLOCK: a foreground until-sleep loop" 2 "$(wait_guard 'until [ -s out.md ]; do sleep 20; done; cat out.md' false)"
check "the same loop in the background passes" 0 "$(wait_guard 'until [ -s out.md ]; do sleep 20; done; cat out.md' true)"
check "a plain sleep passes" 0 "$(wait_guard 'sleep 2; ls' false)"
# ---------- pre-agent-dedupe: one agent per job ----------
launch() { # task text
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"mcp__t3-code__delegate_task","tool_input":{"task":sys.argv[1],"title":"t"}}))' "$1" \
    | python3 "$R/hooks/pre-agent-dedupe.py" 2>/dev/null; echo $?
}
check "first launch of a ticket passes" 0 "$(launch 'Execute the ticket at /tmp/x/ticket-check.md exactly')"
check "BLOCK: a second launch of the same ticket" 2 "$(launch 'Retry: execute /tmp/x/ticket-check.md')"
check "another ticket passes" 0 "$(launch 'Execute /tmp/x/other.md')"
python3 "$R/bin/agent-job" done /tmp/x/ticket-check.md >/dev/null
check "after agent-job done the ticket launches again" 0 "$(launch 'Execute /tmp/x/ticket-check.md')"
cid() { # clientRequestId
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"mcp__t3-code__delegate_task","tool_input":{"task":"x","clientRequestId":sys.argv[1]}}))' "$1" \
    | python3 "$R/hooks/pre-agent-dedupe.py" 2>/dev/null; echo $?
}
check "a new clientRequestId passes" 0 "$(cid r-1)"
check "a retry of the same clientRequestId within 10 minutes passes" 0 "$(cid r-1)"
python3 -c 'import json,os,time; p=os.path.expanduser("~/.claude/agent-client-request-ids.json"); d=json.load(open(p)); d["r-1"]=time.time()-3600; json.dump(d,open(p,"w"))'
check "BLOCK: a clientRequestId reused later (T3 replays the old result)" 2 "$(cid r-1)"
check "agent-job lists jobs with the id file present" 0 "$(python3 "$R/bin/agent-job" list >/dev/null 2>&1; echo $?)"
# a gate review starts only on a draft that passed post-lint in its current form
mkdir -p "$T/drafts/lf"; printf 'Fixed in abc1234.\n' > "$T/drafts/lf/reply.md"
printf 'Review %s and write the verdict to %s/drafts/lf/r.out; the last message is exactly CLEAN.\n' "$T/drafts/lf/reply.md" "$T" > "$T/drafts/lf/review-ticket.md"
check "BLOCK: a review of a draft with no post-lint record" 2 "$(launch "Execute $T/drafts/lf/review-ticket.md")"
printf 'x' > "$T/drafts/lf/reply.md.lint.sha"
check "BLOCK: a review of a draft with a stale post-lint record" 2 "$(launch "Execute $T/drafts/lf/review-ticket.md")"
python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest(), end="")' "$T/drafts/lf/reply.md" > "$T/drafts/lf/reply.md.lint.sha"
check "a review of a draft with a current post-lint record launches" 0 "$(launch "Execute $T/drafts/lf/review-ticket.md")"
python3 "$R/bin/agent-job" done "$T/drafts/lf/review-ticket.md" >/dev/null
echo 'edited' >> "$T/drafts/lf/reply.md"
check "BLOCK: the same review after the draft was edited" 2 "$(launch "Execute $T/drafts/lf/review-ticket.md")"
python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest(), end="")' "$T/drafts/lf/reply.md" > "$T/drafts/lf/reply.md.lint.sha"
printf 'Evidence.\n' > "$T/drafts/lf/research.md"
printf 'Review %s against the evidence in %s, write the verdict to %s/drafts/lf/r2.out; the last message is exactly CLEAN.\n' "$T/drafts/lf/reply.md" "$T/drafts/lf/research.md" "$T" > "$T/drafts/lf/review2-ticket.md"
check "the evidence file a review names is not a draft" 0 "$(launch "Execute $T/drafts/lf/review2-ticket.md")"
printf 'Live text.\n' > "$T/drafts/lf/reply.current.md"
printf 'Review %s against the live %s, write the verdict to %s/drafts/lf/r3.out; the last message is exactly CLEAN.\n' "$T/drafts/lf/reply.md" "$T/drafts/lf/reply.current.md" "$T" > "$T/drafts/lf/review3-ticket.md"
check "the live copy of an edited post is not a draft" 0 "$(launch "Execute $T/drafts/lf/review3-ticket.md")"
# ---------- pr-steps: a refactor record is a real pass ----------
G="$T/prs"; mkdir -p "$G"; git -C "$G" init -q; git -C "$G" -c user.name=t -c user.email=t@t commit -q --allow-empty -m a
prs() { (cd "$G" && bash "$R/bin/pr-steps" "$@" >/dev/null 2>&1; echo $?); }
printf '# Loop B fix log\nfixed the README\n' > "$T/fixlog.md"
check "BLOCK: a fix log recorded as the refactor pass" 1 "$(prs refactor "$T/fixlog.md")"
printf '| express vike() | 5 ⇒ 8 | abc | named steps |\n✅ express vike()\n' > "$T/pass.md"
check "a pass with ratings and the ✅ list records" 0 "$(prs refactor "$T/pass.md")"
A=$(git -C "$G" rev-parse HEAD); printf 'x\n' > "$G/f"; git -C "$G" add f; git -C "$G" -c user.name=t -c user.email=t@t commit -q -m b
printf 'carries the pass of %s: one docs line\n' "$A" > "$T/carry.md"
check "a small follow-up carries the earlier pass" 0 "$(prs refactor "$T/carry.md")"
# ---------- pr-steps: every converge step leaves its proof; the guard needs all six ----------
G2="$T/prs2"; mkdir -p "$G2"; git -C "$G2" init -q; git -C "$G2" -c user.name=t -c user.email=t@t commit -q --allow-empty -m a
prs2() { (cd "$G2" && bash "$R/bin/pr-steps" "$@" >/dev/null 2>&1; echo $?); }
ready() { python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":"gh pr ready 5"},"cwd":sys.argv[1]}))' "$G2" | python3 "$R/hooks/pre-bash-guard.py" >/dev/null 2>&1; echo $?; }
check "BLOCK: gh pr ready with no step recorded" 2 "$(ready)"
printf 'slice 1: no bug that counts\n' > "$T/v0.md"
check "BLOCK: a Loop A output without DRY" 1 "$(prs2 verify "$T/v0.md")"
printf 'slice 1: no bug that counts\nDRY\n' > "$T/v.md"; check "Loop A ending DRY records" 0 "$(prs2 verify "$T/v.md")"
printf 'nothing worth changing\nCLEAN\n' > "$T/lb.md"; check "Loop B's review ending CLEAN records" 0 "$(prs2 loopb "$T/lb.md")"
printf '| vike() | 5 ⇒ 8 | abc | why |\n✅ vike()\n' > "$T/rf.md"; check "Loop B's ratings record" 0 "$(prs2 refactor "$T/rf.md")"
printf 'NO LOOP B COMMITS\n' > "$T/rv.md"; check "Loop A again, with no Loop B commits, records" 0 "$(prs2 reverify "$T/rv.md")"
printf 'CLEAN\n' > "$T/fr0.md"; check "BLOCK: a fresh read without MERGE AS IS: yes" 1 "$(prs2 fresh "$T/fr0.md")"
printf 'MERGE AS IS: yes\nCLEAN\n' > "$T/fr.md"; check "the fresh reader's merge-as-is and CLEAN record" 0 "$(prs2 fresh "$T/fr.md")"
printf 'pnpm test -> exit 0\npnpm lint -> exit 1\n' > "$T/g1.md"
check "BLOCK: a gates log with a red gate" 1 "$(prs2 gates "$T/g1.md")"
check "BLOCK: gh pr ready with five of six steps" 2 "$(ready)"
printf 'pnpm test -> exit 0\npnpm lint -> exit 0\n' > "$T/g2.md"; check "a green gates log records" 0 "$(prs2 gates "$T/g2.md")"
check "gh pr ready passes once all six steps hold on HEAD" 0 "$(ready)"
# ---------- pre-design-gate: Tier M code waits for prior-art.md and decisions/*.md ----------
D="$T/dg"; mkdir -p "$D" "$D-work"; git -C "$D" init -q
gate() { python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2]),"cwd":sys.argv[3]}))' "$1" "$2" "$D" | python3 "$R/hooks/pre-design-gate.py" 2>/dev/null; echo $?; }
check "no scope.md: an edit passes" 0 "$(gate Edit "{\"file_path\":\"$D/a.ts\"}")"
printf 'Tier: M, because x\n' > "$D-work/scope.md"
check "BLOCK: Tier M edit with no prior art or decision" 2 "$(gate Edit "{\"file_path\":\"$D/a.ts\"}")"
check "BLOCK: Tier M implementation agent with no decision" 2 "$(gate mcp__t3-code__delegate_task '{"role":"implementation"}')"
check "a research agent passes" 0 "$(gate mcp__t3-code__delegate_task '{"role":"research"}')"
check "an artifact-root write passes" 0 "$(gate Write "{\"file_path\":\"$D-work/prior-art.md\"}")"
touch "$D-work/prior-art.md"; mkdir -p "$D-work/decisions"; touch "$D-work/decisions/x.md"
check "Tier M edit passes once prior art and a decision exist" 0 "$(gate Edit "{\"file_path\":\"$D/a.ts\"}")"
# ---------- pre-bash-guard: never kill a running agent ----------
printf '#!/bin/sh\nsleep 600\n' > "$T/claude"; chmod +x "$T/claude"
"$T/claude" --output-format stream-json >/dev/null 2>&1 & APID=$!
sleep 600 >/dev/null 2>&1 & OPID=$!
sleep 0.3
kill_guard() { python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":"kill "+sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$T" | python3 "$R/hooks/pre-bash-guard.py" 2>/dev/null; echo $?; }
check "BLOCK: kill of an agent's claude process" 2 "$(kill_guard $APID)"
check "kill of an ordinary process passes" 0 "$(kill_guard $OPID)"
kill $(ps -o pid= --ppid $APID) $APID $OPID 2>/dev/null
rm -rf "$T"
echo "failures: $fails"; [ "$fails" = 0 ]
