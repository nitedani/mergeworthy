#!/usr/bin/env bash
# Tests for bin/project-learn (the daily project-file learning run). Usage: tests/project-learn.sh [repo root]
# Temp HOME with project files and studies; a stub gh answering GET paths and GraphQL queries from recorded vikejs/vike responses
# (trimmed), a stub t3.
set -u
R=$(readlink -f "${1:-$(dirname "$0")/..}")
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; export HOME="$T/home"; P="$HOME/.mergeworthy/projects"; L="$HOME/.mergeworthy/work/project-learn"
mkdir -p "$P/vikejs" "$P/o" "$HOME/.mergeworthy/work/a" "$T/bin"
fails=0
check() { echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1)); }

# the project file cites our PR whole and our comment 333 for older lessons: new reactions on them are still unsorted
printf '%s\n' '# vikejs/vike' '## Who decides' 'brillout merges. Study: vike.study.md' '## What worked' \
  '- a reply: https://github.com/vikejs/vike/pull/3636#issuecomment-111' '- an earlier lesson on https://github.com/vikejs/vike/pull/3636 (2026-10-20)' \
  '- 👍 on https://github.com/vikejs/vike/pull/3636#issuecomment-333 (2026-10-20)' > "$P/vikejs/vike.md"
printf 'Studied: 2026-10-29\n# vike study\n- a quote\n' > "$P/vikejs/vike.study.md"
echo '9999999 TASTE https://x' > "$HOME/.mergeworthy/work/a/followups-sorted.txt"
BADGED='<img src=\"https://github.com/claude.png\" alt=\"Claude\"> *Claude wrote this*'
UPD='"updated_at": "2026-10-30T18:00:00Z"'
cat > "$T/gh.json" <<EOF
{
"search:vikejs/vike": {"items": [
  {"number": 3636, "pull_request": {}, "user": {"login": "nitedani-agent"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3636", "html_url": "https://github.com/vikejs/vike/pull/3636", "body": "$BADGED", "reactions": {"total_count": 1}},
  {"number": 1707, "user": {"login": "brillout"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/1707", "html_url": "https://github.com/vikejs/vike/issues/1707", "body": "a design question of theirs", "reactions": {"total_count": 0}},
  {"number": 3594, "pull_request": {}, "user": {"login": "nitedani"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3594", "html_url": "https://github.com/vikejs/vike/pull/3594", "body": "$BADGED", "reactions": {"total_count": 0}},
  {"number": 3651, "pull_request": {}, "user": {"login": "redbar0n"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3651", "html_url": "https://github.com/vikejs/vike/pull/3651", "body": "their PR we reviewed", "reactions": {"total_count": 0}},
  {"number": 3652, "pull_request": {}, "user": {"login": "redbar0n"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3652", "html_url": "https://github.com/vikejs/vike/pull/3652", "body": "their PR we reviewed in a review body", "reactions": {"total_count": 0}},
  {"number": 3700, "user": {"login": "eve"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3700", "html_url": "https://github.com/vikejs/vike/issues/3700", "body": "someone else's issue", "reactions": {"total_count": 0}},
  {"number": 3650, "pull_request": {}, "user": {"login": "redbar0n"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3650", "html_url": "https://github.com/vikejs/vike/pull/3650", "body": "someone else's PR", "reactions": {"total_count": 0}},
  {"number": 3659, "pull_request": {}, "user": {"login": "dgesteves"}, $UPD, "url": "https://api.github.com/repos/vikejs/vike/issues/3659", "html_url": "https://github.com/vikejs/vike/pull/3659", "body": "$BADGED", "reactions": {"total_count": 0}},
  {"number": 3600, "pull_request": {}, "user": {"login": "redbar0n"}, "updated_at": "2026-10-20T00:00:00Z", "url": "https://api.github.com/repos/vikejs/vike/issues/3600", "html_url": "https://github.com/vikejs/vike/pull/3600", "body": "an older PR of theirs", "reactions": {"total_count": 0}}]},
"repos/vikejs/vike/issues/1707/comments": [
  {"html_url": "https://github.com/vikejs/vike/issues/1707#issuecomment-1707001", "url": "u", "user": {"login": "nitedani-agent"}, "created_at": "2026-10-30T09:30:00Z", "author_association": "CONTRIBUTOR", "body": "$BADGED", "reactions": {"total_count": 0}},
  {"html_url": "https://github.com/vikejs/vike/issues/1707#issuecomment-1707002", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T10:30:00Z", "author_association": "MEMBER", "body": "Nothing's blocking you, correct? So let's postpone this", "reactions": {"total_count": 0}}],
"repos/vikejs/vike/issues/3594/comments": [],
"repos/vikejs/vike/pulls/3594/reviews": [],
"repos/vikejs/vike/pulls/3594/comments": [],
"repos/vikejs/vike/pulls/3594": {"base": {"sha": "ba5e"}, "head": {"sha": "4ead"}},
"repos/vikejs/vike/issues/3651/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3651#issuecomment-3651001", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T11:30:00Z", "author_association": "MEMBER", "body": "Good catch, I'll change it", "reactions": {"total_count": 0}}],
"repos/vikejs/vike/pulls/3651/reviews": [],
"repos/vikejs/vike/pulls/3651/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3651#discussion_r53", "url": "https://api.github.com/repos/vikejs/vike/pulls/comments/53", "user": {"login": "nitedani-agent"}, "created_at": "2026-10-30T11:00:00Z", "author_association": "CONTRIBUTOR", "path": "b.ts", "body": "$BADGED", "reactions": {"total_count": 1}}],
"repos/vikejs/vike/pulls/comments/53/reactions": [{"user": {"login": "brillout"}, "content": "+1", "created_at": "2026-10-30T11:20:00Z"}],
"repos/vikejs/vike/issues/3652/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3652#issuecomment-3652001", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T12:10:00Z", "author_association": "MEMBER", "body": "Agreed, splitting it", "reactions": {"total_count": 0}}],
"repos/vikejs/vike/pulls/3652/reviews": [
  {"html_url": "https://github.com/vikejs/vike/pull/3652#pullrequestreview-77", "node_id": "PRR_77", "user": {"login": "nitedani-agent"}, "submitted_at": "2026-10-30T12:00:00Z", "author_association": "CONTRIBUTOR", "state": "COMMENTED", "body": "$BADGED"}],
"graphql:PRR_77": {"data": {"node": {"reactions": {"nodes": []}}}},
"repos/vikejs/vike/pulls/3652/comments": [],
"repos/vikejs/vike/issues/3650/comments": [],
"repos/vikejs/vike/issues/3600/comments": [],
"repos/vikejs/vike/pulls/3600/reviews": [],
"repos/vikejs/vike/pulls/3600/comments": [],
"repos/vikejs/vike/issues/3700/comments": [
  {"html_url": "https://github.com/vikejs/vike/issues/3700#issuecomment-3700001", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T10:30:00Z", "author_association": "MEMBER", "body": "the claude.png in the docs is broken", "reactions": {"total_count": 0}}],
"search:vikejs/vike:merged": {"items": [{"number": 3648, "pull_request": {}, "user": {"login": "nitedani-agent"}, "body": "$BADGED"},
  {"number": 3660, "pull_request": {}, "user": {"login": "dgesteves"}, "body": "$BADGED"}]},
"repos/vikejs/vike/pulls/3660": {"merged_at": "2026-10-29T09:00:00Z", "merge_commit_sha": "7777777777777777777777777777777777777777"},
"repos/vikejs/vike/pulls/3660/files": [{"filename": "packages/vike/c.ts"}],
"repos/vikejs/vike/commits/7777777777777777777777777777777777777777": {"files": [{"filename": "packages/vike/a.ts"}]},
"repos/vikejs/vike/issues/3636/reactions": [{"user": {"login": "brillout"}, "content": "heart", "created_at": "2026-10-30T09:00:00Z"}],
"repos/vikejs/vike/issues/3636/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3636#issuecomment-6529075994", "url": "https://api.github.com/repos/vikejs/vike/issues/comments/6529075994", "user": {"login": "brillout"}, "created_at": "2026-10-30T17:28:25Z", "author_association": "MEMBER", "body": "> https://github.com/vikejs/vike/pull/3636/changes/5b822aea8cdbfc4d3ce30c0d1cac3ec7fb27c77a\r\n\r\nI love these kind of refactors, curious: why didn't find it earlier when I asked https://github.com/vikejs/vike/pull/3636#issuecomment-6500292129 ?", "reactions": {"total_count": 1}},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#issuecomment-6491486934", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-28T08:12:31Z", "author_association": "MEMBER", "body": "merge main", "reactions": {"total_count": 0}},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#issuecomment-111", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T10:00:00Z", "author_association": "MEMBER", "body": "already in the project file", "reactions": {"total_count": 0}},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#issuecomment-222", "url": "u", "user": {"login": "eve"}, "created_at": "2026-10-30T10:00:00Z", "author_association": "CONTRIBUTOR", "body": "a bystander", "reactions": {"total_count": 0}},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#issuecomment-333", "url": "https://api.github.com/repos/vikejs/vike/issues/comments/333", "user": {"login": "nitedani-agent"}, "created_at": "2026-10-30T11:00:00Z", "author_association": "CONTRIBUTOR", "body": "$BADGED", "reactions": {"total_count": 1}}],
"repos/vikejs/vike/issues/comments/333/reactions": [{"user": {"login": "brillout"}, "content": "+1", "created_at": "2026-10-30T12:00:00Z"}, {"user": {"login": "eve"}, "content": "+1", "created_at": "2026-10-30T12:00:00Z"}],
"repos/vikejs/vike/pulls/3636/reviews": [
  {"html_url": "https://github.com/vikejs/vike/pull/3636#pullrequestreview-1", "user": {"login": "brillout"}, "submitted_at": "2026-10-30T13:00:00Z", "author_association": "MEMBER", "state": "APPROVED", "body": ""},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#pullrequestreview-2", "user": {"login": "brillout"}, "submitted_at": "2026-10-30T13:00:00Z", "author_association": "MEMBER", "state": "COMMENTED", "body": ""},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#pullrequestreview-3", "node_id": "PRR_3", "user": {"login": "nitedani-agent"}, "submitted_at": "2026-10-30T13:30:00Z", "author_association": "CONTRIBUTOR", "state": "COMMENTED", "body": "$BADGED"}],
"graphql:PRR_3": {"data": {"node": {"reactions": {"nodes": [{"content": "HOORAY", "createdAt": "2026-10-30T14:30:00Z", "user": {"login": "brillout"}}]}}}},
"repos/vikejs/vike/pulls/3636/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3636#discussion_r4414894877", "user": {"login": "brillout"}, "created_at": "2026-10-29T16:16:50Z", "author_association": "MEMBER", "path": "getPageContextFromHooks.ts", "body": "Why swallow the error?"},
  {"html_url": "https://github.com/vikejs/vike/pull/3636#discussion_r999", "url": "https://api.github.com/repos/vikejs/vike/pulls/comments/999", "user": {"login": "nitedani-agent"}, "created_at": "2026-10-30T16:00:00Z", "author_association": "CONTRIBUTOR", "path": "a.ts", "body": "$BADGED", "reactions": {"total_count": 1}}],
"repos/vikejs/vike/pulls/comments/999/reactions": [{"user": {"login": "brillout"}, "content": "+1", "created_at": "2026-10-30T16:30:00Z"}],
"repos/vikejs/vike/pulls/3636/commits": [
  {"sha": "808c79d840a66d73b4a54774b121a693e40759e8", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "minor refactor", "committer": {"date": "2026-10-30T13:58:16Z"}}},
  {"sha": "1111111111111111111111111111111111111111", "author": {"login": "nitedani"}, "parents": [{}], "commit": {"message": "fix\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", "committer": {"date": "2026-10-30T14:00:00Z"}}},
  {"sha": "2222222222222222222222222222222222222222", "author": {"login": "brillout"}, "parents": [{}, {}], "commit": {"message": "Merge branch 'main'", "committer": {"date": "2026-10-30T14:00:00Z"}}},
  {"sha": "9999999aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "sorted by a session", "committer": {"date": "2026-10-30T14:00:00Z"}}},
  {"sha": "4444444444444444444444444444444444444444", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "our #3648, squashed on the stacked base", "committer": {"date": "2026-10-30T14:30:00Z"}}}],
"repos/vikejs/vike/pulls/3650/reviews": [
  {"html_url": "https://github.com/vikejs/vike/pull/3650#pullrequestreview-50", "user": {"login": "brillout"}, "submitted_at": "2026-10-30T06:04:58Z", "author_association": "MEMBER", "state": "COMMENTED", "body": "I agree and it's very much on the radar"}],
"repos/vikejs/vike/pulls/3650/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3650#discussion_r51", "user": {"login": "brillout"}, "created_at": "2026-10-30T17:17:39Z", "author_association": "MEMBER", "path": "docs/react.md", "body": "With Vike, you can directly depend on React"}],
"repos/vikejs/vike/issues/3659/comments": [
  {"html_url": "https://github.com/vikejs/vike/pull/3659#issuecomment-3659001", "url": "u", "user": {"login": "brillout"}, "created_at": "2026-10-30T12:30:00Z", "author_association": "MEMBER", "body": "a lesson on a badged PR someone else opened", "reactions": {"total_count": 0}}],
"repos/vikejs/vike/pulls/3659/commits": [],
"repos/vikejs/vike/pulls/3659/reviews": [],
"repos/vikejs/vike/pulls/3659/comments": [],
"repos/vikejs/vike/pulls/3648": {"merged_at": "2026-10-29T08:30:00Z", "merge_commit_sha": "4444444444444444444444444444444444444444"},
"repos/vikejs/vike/pulls/3648/files": [{"filename": "packages/vike/a.ts"}],
"repos/vikejs/vike/commits": [
  {"sha": "5555555555555555555555555555555555555555", "html_url": "https://github.com/vikejs/vike/commit/5555555555555555555555555555555555555555", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "refactor a", "committer": {"date": "2026-10-30T15:00:00Z"}}},
  {"sha": "4444444444444444444444444444444444444444", "html_url": "h4", "author": {"login": "nitedani-agent"}, "parents": [{}], "commit": {"message": "our PR's squash", "committer": {"date": "2026-10-29T08:30:00Z"}}},
  {"sha": "7777777777777777777777777777777777777777", "html_url": "https://github.com/vikejs/vike/commit/7777777777777777777777777777777777777777", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "#3660 squashed by the maintainer", "committer": {"date": "2026-10-30T15:30:00Z"}}},
  {"sha": "6666666666666666666666666666666666666666", "html_url": "h6", "author": {"login": "brillout"}, "parents": [{}], "commit": {"message": "elsewhere", "committer": {"date": "2026-10-30T15:00:00Z"}}}],
"repos/vikejs/vike/commits/5555555555555555555555555555555555555555": {"files": [{"filename": "packages/vike/a.ts"}]},
"repos/vikejs/vike/commits/6666666666666666666666666666666666666666": {"files": [{"filename": "packages/vike/b.ts"}]},
"search:o/quiet": {"items": []},
"search:o/quiet:merged": {"items": []}
}
EOF
python3 - "$T/gh.json" <<'PY'  # our #3594 has 251 commits: GitHub's list gives 250, the compare all of them, the maintainer's oldest first
import json, sys
m = json.load(open(sys.argv[1]))
ours = [{'sha': f'{n:040x}', 'author': {'login': 'nitedani'}, 'parents': [{}], 'commit': {'message': 'step\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', 'committer': {'date': '2026-10-30T12:00:00Z'}}} for n in range(1, 251)]
theirs = {'sha': 'dd77a1e' + '0' * 33, 'author': {'login': 'brillout'}, 'parents': [{}], 'commit': {'message': 'minor refactor: rename', 'committer': {'date': '2026-10-29T18:00:00Z'}}}
m['repos/vikejs/vike/pulls/3594/commits'] = ours
m['repos/vikejs/vike/compare/ba5e...4ead'] = {'commits': [theirs] + ours}
json.dump(m, open(sys.argv[1], 'w'))
PY
cat > "$T/bin/gh" <<EOF
#!/usr/bin/env python3
import json, re, sys, time, urllib.parse
open("$T/gh-calls", "a").write(' '.join(sys.argv[1:]) + '\n')
m = json.load(open("$T/gh.json"))
if sys.argv[1:3] == ['api', 'graphql']:
    key = 'graphql:' + next(a.split('=', 1)[1] for a in sys.argv if a.startswith('id='))
    print(json.dumps(m[key])); sys.exit()
p = sys.argv[-1]; key = p.split('?')[0]
if key == 'search/issues':
    key = 'search:' + re.search(r'repo:([\w./-]+)', p)[1] + (':merged' if 'is:merged' in p else '')
if key not in m:
    sys.exit(f"unexpected gh {p}")
v = m[key]
q = urllib.parse.unquote_plus(p)
if key.endswith(':merged') and 'items' in v:
    v = {**v, 'items': [i for i in v['items'] if i.get('merged_at', '9') >= re.search(r'merged:>=(\S+)', q)[1]]}
if 'all' in v:  # GitHub's search: what the updated: range matches, at most 1000 of it
    span, start = re.search(r'updated:(\S+)\.\.(\S+)', q), re.search(r'(?:updated|merged|closed):>=(\S+)', q)
    lo, hi = (span[1], span[2]) if span else (start[1] if start else '', '9')
    hit = [i for i in v['all'] if lo <= i['updated_at'] <= hi]
    v = {'total_count': len(hit), 'items': hit[:1000]}  # paged below
if key.startswith('search:') and 'total_count' not in v:  # every search answer counts what it matched
    v = {**v, 'total_count': len(v['items'])}
if key.startswith('search:'):  # one page of 100 a request, logged with its query, its count and when
    n = int(re.search(r'[?&]page=(\d+)', p)[1]); v = {**v, 'items': v['items'][(n - 1) * 100:n * 100]}
    open("$T/searches", "a").write(f"{time.time()}\t{n}\t{v['total_count']}\t{q}\n")
print(json.dumps([v]))
EOF
cat > "$T/bin/t3" <<EOF
#!/bin/sh
echo "t3 \$*" >> "$T/t3-calls"
[ -e "$T/t3-down" ] && { echo "server not reachable" >&2; exit 1; }
case "\$2" in
  add) touch "$T/t3-project" ;;
  start) [ -e "$T/t3-project" ] || exit 1; printf '%s\n' "\$6" > "$T/prompt"; echo thread-1 ;;
esac
EOF
chmod +x "$T/bin/"*; export PATH="$T/bin:/usr/bin:/bin"  # no real t3 or gh is ever reachable

# ---------- list: each kind a maintainer leaves on our work, and their reviews on others' PRs, after the mark, not yet sorted ----------
out=$(python3 "$R/bin/project-learn" list vikejs/vike); echo "$out" > "$T/list1"
check "list: the maintainer's PR conversation comment that reached no project file, in their own words (the quote left out)" 1 \
  "$(grep -cF $'2026-10-30T17:28:25Z\tcomment\tbrillout\thttps://github.com/vikejs/vike/pull/3636#issuecomment-6529075994\tI love these kind of refactors' "$T/list1")"
check "list: a review's approval, an inline comment, their commit on our PR, a follow-up" "1 1 1 1" \
  "$(grep -c $'\treview\tbrillout\t.*pullrequestreview-1\tAPPROVED' "$T/list1") $(grep -c $'\tinline\tbrillout\t.*discussion_r4414894877\tgetPageContextFromHooks.ts: Why swallow' "$T/list1") $(grep -c $'\tcommit\tbrillout\t.*/pull/3636/commits/808c79d' "$T/list1") $(grep -c $'\tfollow-up\tbrillout\t.*/commit/5555555.*\tchanges packages/vike/a.ts from #3648: refactor a' "$T/list1")"
check "list: new reactions on our PR body and our comment, though the project file cites both posts for older lessons" "1 1" \
  "$(grep -c $'\treaction\tbrillout\thttps://github.com/vikejs/vike/pull/3636\theart on our post' "$T/list1") $(grep -c $'\treaction\tbrillout\t.*issuecomment-333\t+1 on our comment' "$T/list1")"
check "list: reactions on our inline comment (REST) and on our review's body (GraphQL: reviews have no REST reactions endpoint)" "1 1" \
  "$(grep -c $'\treaction\tbrillout\t.*discussion_r999\t+1 on our inline comment' "$T/list1") $(grep -c $'\treaction\tbrillout\t.*pullrequestreview-3\tHOORAY on our review' "$T/list1")"
check "list: their review body and inline comment on someone else's PR updated since the mark" "1 1" \
  "$(grep -c $'\tothers-review\tbrillout\thttps://github.com/vikejs/vike/pull/3650#pullrequestreview-50\tCOMMENTED: I agree' "$T/list1") $(grep -c $'\tothers-inline\tbrillout\t.*3650#discussion_r51\tdocs/react.md: With Vike' "$T/list1")"
check "list: left out: before the mark, already cited, a bystander and their reaction, a bare COMMENTED review, our commit, a merge, a sorted sha, our squash, another file, someone else's issue" "0 0 0 0 0 0 0 0 0 0" \
  "$(grep -c 6491486934 "$T/list1") $(grep -c 'issuecomment-111' "$T/list1") $(grep -c $'\teve\t' "$T/list1") $(grep -c pullrequestreview-2 "$T/list1") $(grep -c 1111111 "$T/list1") $(grep -c 2222222 "$T/list1") $(grep -c 9999999 "$T/list1") $(grep -c 4444444 "$T/list1") $(grep -c 6666666 "$T/list1") $(grep -c 3700 "$T/list1")"
check "list: a badged PR opened by a login gh isn't signed in as is ours: its maintainer comment listed; a PR of theirs untouched since the mark, holding no badge, lists nothing" "1 0" \
  "$(grep -c $'\tcomment\tbrillout\t.*/pull/3659#issuecomment-3659001' "$T/list1") $(grep -c '/pull/3600' "$T/list1")"
check "list: their PR whose only badge is our inline comment is our work: their conversation reply and their reaction on our inline comment" "1 1" \
  "$(grep -c $'\tcomment\tbrillout\t.*/pull/3651#issuecomment-3651001' "$T/list1") $(grep -c $'\treaction\tbrillout\t.*/pull/3651#discussion_r53\t+1 on our inline comment' "$T/list1")"
check "list: their PR whose only badge is our review body is our work: their conversation reply listed" 1 "$(grep -c $'\tcomment\tbrillout\t.*/pull/3652#issuecomment-3652001' "$T/list1")"
check "list: our PR over GitHub's 250 commits: read whole from the compare of its base and head, the maintainer's oldest commit listed" 1 "$(grep -c $'\tcommit\tbrillout\t.*/pull/3594/commits/dd77a1e' "$T/list1")"
check "list: the squash of a badged PR merged from another login is no follow-up" 0 "$(grep -c 7777777 "$T/list1")"
check "list: their issue holding our badged comment is our work (found by reading its comments: GitHub's search misses some): their reply there listed; eve's issue, whose comment only names claude.png, isn't; no comment search is made" "1 0 0" \
  "$(grep -c $'\tcomment\tbrillout\t.*/issues/1707#issuecomment-1707002\tNothing' "$T/list1") $(grep -c 3700001 "$T/list1") $(grep -c 'in:comments' "$T/gh-calls")"
until=$(tail -n1 "$T/list1" | awk '{print $7}'); vmark=$(tail -n1 "$T/list1" | cut -d' ' -f6-)  # <repo> <until> <sha7>@<time>...
check "list: our merged PR's squash commit, on a PR stacked on it, is not the maintainer's commit" 0 "$(grep -c $'\tcommit\t.*/pull/3636/commits/4444444' "$T/list1")"
cp "$T/gh.json" "$T/gh.full"; old=$(date -u -d '-90 days' +%FT%TZ)
python3 - "$T/gh.json" "$old" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
m['search:vikejs/vike:merged']['items'][0]['merged_at'] = m['repos/vikejs/vike/pulls/3648']['merged_at'] = sys.argv[2]
json.dump(m, open(sys.argv[1], 'w'))
PY
python3 "$R/bin/project-learn" list vikejs/vike --since "$(date -u -d '-1 year' +%F)" > "$T/year" 2>&1; rc=$?; cp "$T/gh.full" "$T/gh.json"
check "list a year back: our PR merged 90 days ago (outside the 60-day follow-ups), its squash on a PR stacked on it is not the maintainer's commit" "0 0 1" \
  "$rc $(grep -c $'\tcommit\t.*/pull/3636/commits/4444444' "$T/year") $(grep -c $'\tcommit\tbrillout\t.*/pull/3636/commits/808c79d' "$T/year")"
check "list: 17 items, oldest first, ending with the mark that covers them and carries their commits" "17 2026-10-29T16:16:50Z 1" \
  "$(grep -vc '^#' "$T/list1") $(sed -n 2p "$T/list1" | cut -f1) $(tail -n1 "$T/list1" | grep -cE "^# read whole: project-learn mark vikejs/vike $until( [0-9a-f]{7}@[^ ]+)+$")"
check "list: GET calls and GraphQL queries only" "0 0" "$(grep -v '^api graphql ' "$T/gh-calls" | grep -vEc '^api (--paginate --slurp )?[^-]') $(grep '^api graphql ' "$T/gh-calls" | grep -c 'mutation')"
cp "$P/vikejs/vike.md" "$T/vike.md"; printf '%s\n' '# vikejs/vike' '## Who decides' 'nobody named' > "$P/vikejs/vike.md"
check "list: with ## Who decides naming nobody, GitHub's member association makes them a maintainer: their comment and their reaction" "1 1" \
  "$(python3 "$R/bin/project-learn" list vikejs/vike > "$T/l"; grep -c 'issuecomment-6529075994' "$T/l") $(grep -c $'\treaction\tbrillout\t.*\theart on our post' "$T/l")"
cp "$T/vike.md" "$P/vikejs/vike.md"

check "list <GitHub URL>: the same 17 items as <owner/repo>" "17 1" "$(python3 "$R/bin/project-learn" list https://github.com/vikejs/vike | grep -vc '^#') $(cmp -s <(python3 "$R/bin/project-learn" list https://github.com/vikejs/vike | grep -v '^#') <(python3 "$R/bin/project-learn" list vikejs/vike | grep -v '^#') && echo 1 || echo 0)"
# a project-file line cites its evidence short, in the repo's scope; the study holds the full link, or nothing
cp "$P/vikejs/vike.study.md" "$T/vike.study.md"
printf '%s\n' '- a comment #3636/c6529075994, an inline one #3636/r4414894877, one in full scope vikejs/vike#3651/c3651001' \
  '- one with its full link in the study #1707/c1707002, a review #3636/v1; another repo'"'"'s number other/repo#3659/c3659001' >> "$P/vikejs/vike.md"
echo '- "postpone": https://github.com/vikejs/vike/issues/1707#issuecomment-1707002' >> "$P/vikejs/vike.study.md"
python3 "$R/bin/project-learn" list vikejs/vike > "$T/l"
check "list: left out: what the project file cites by short ref alone (a comment, an inline comment, a review, one with its repo), or short with the full link in the study; another repo's same number listed" "0 0 0 0 0 1 12" \
  "$(grep -c 6529075994 "$T/l") $(grep -c discussion_r4414894877 "$T/l") $(grep -c $'pullrequestreview-1\t' "$T/l") $(grep -c 3651001 "$T/l") $(grep -c 1707002 "$T/l") $(grep -c 3659001 "$T/l") $(grep -vc '^#' "$T/l")"
cp "$T/vike.md" "$P/vikejs/vike.md"; cp "$T/vike.study.md" "$P/vikejs/vike.study.md"

# ---------- mark: its own Learned line in the study, forward only, up to what a list covered, never over the cap ----------
check "mark: refuses a time before the mark, and one in the future; the study untouched" "1 1 Studied: 2026-10-29|# vike study" \
  "$(python3 "$R/bin/project-learn" mark vikejs/vike 2026-10-28T00:00:00Z >/dev/null 2>&1; echo $?) $(python3 "$R/bin/project-learn" mark vikejs/vike 2099-01-01T00:00:00Z >/dev/null 2>&1; echo $?) $(head -n2 "$P/vikejs/vike.study.md" | paste -sd'|')"
yes word | head -n 2501 >> "$P/vikejs/vike.md"
check "mark: refuses while the project file is over 2500 words, saying so" "1 1" \
  "$(python3 "$R/bin/project-learn" mark vikejs/vike "$until" 2>"$T/err" >/dev/null; echo $?) $(grep -c 'over the 2500-word cap' "$T/err")"
cp "$T/vike.md" "$P/vikejs/vike.md"
python3 "$R/bin/project-learn" mark $vmark >/dev/null
check "mark: a Learned line under Studied, which keeps the full study's date (its 30-day re-study still due)" "Studied: 2026-10-29|Learned: $until|# vike study|- a quote" "$(grep -v '^Commits read: ' "$P/vikejs/vike.study.md" | paste -sd'|')"
check "list after the mark: nothing new" 0 "$(python3 "$R/bin/project-learn" list vikejs/vike | grep -vc '^#')"
python3 "$R/bin/project-learn" mark $vmark >/dev/null
check "mark again: one Learned line, moved in place" "1 2" "$(grep -c '^Learned:' "$P/vikejs/vike.study.md") $(grep -n '^Learned:' "$P/vikejs/vike.study.md" | cut -d: -f1)"
check "mark: refuses a time before the Learned line, though after Studied" 1 "$(python3 "$R/bin/project-learn" mark vikejs/vike 2026-10-29T12:00:00Z >/dev/null 2>&1; echo $?)"
printf 'Studied: 2026-10-29\n' > "$P/vikejs/vike.study.md"
check "with no Learned line, a full study's date is the mark, at that day's start" "after 2026-10-29T00:00:00Z" "$(TZ=Etc/GMT-1 python3 "$R/bin/project-learn" list vikejs/vike | head -n1 | grep -o 'after [^ ]*')"

# ---------- start: once a day; a repo with nothing new is marked without a thread; the rest go to one T3 thread ----------
printf '# o/quiet\n## Who decides\nboss\n' > "$P/o/quiet.md"; printf 'Studied: 2026-10-29\n' > "$P/o/quiet.study.md"
printf '# o/nostudy\n' > "$P/o/nostudy.md"
touch "$T/t3-down"
check "start with T3 down: exit 1, a runs.txt line saying it failed and why" "1 1" \
  "$(python3 "$R/bin/project-learn" start >/dev/null 2>&1; echo $?) $(grep -c "^$(date -u +%F) .* FAILED: t3 thread start failed: server not reachable" "$L/runs.txt")"
rm "$T/t3-down"; mv "$T/bin/t3" "$T/t3.off"
check "start with no t3 on PATH: exit 1, a runs.txt line saying so" "1 1" \
  "$(python3 "$R/bin/project-learn" start >/dev/null 2>&1; echo $?) $(grep -c "FAILED: no t3 on PATH" "$L/runs.txt")"
mv "$T/t3.off" "$T/bin/t3"; : > "$T/t3-calls"
out=$(python3 "$R/bin/project-learn" start); rc=$?
check "start after a failed run the same day: runs; o/quiet marked to now without a thread, its Studied kept; vike's list waits for the thread" "0 Studied: 2026-10-29 1 0" \
  "$rc $(head -n1 "$P/o/quiet.study.md") $(grep -c "^Learned: $(date -u +%F)T" "$P/o/quiet.study.md") $(grep -c '^Learned:' "$P/vikejs/vike.study.md")"
check "start: one thread, started after adding the folder as a T3 project, its prompt naming the cap and vike's list" "1 1 1 1" \
  "$(grep -c "^t3 project add --title project-learn $L$" "$T/t3-calls") $(grep -c "^t3 thread start --title Project-file learning $(date -u +%F) $L " "$T/t3-calls" | sed 's/^2$/1/') $(grep -c 'over 2500 words' "$T/prompt") $(tail -n1 "$T/prompt" | grep -cx "Lists: $L/lists/vikejs__vike.txt")"
check "start: the prompt names this project-learn by its path for the mark (T3 starts the thread with its own PATH) and the projects folder" "1 1" \
  "$(grep -c "\`project-learn\` being \`$R/bin/project-learn\`" "$T/prompt") $(grep -c "studies are in $P;" "$T/prompt")"
check "start: the day's run recorded with its thread and the repos it sorts" 1 "$(grep -c "^$(date -u +%F) .* thread thread-1; 1 to sort: vikejs/vike$" "$L/runs.txt")"
check "start: a repo without a study is skipped, saying so" 1 "$(echo "$out" | grep -c '^o/nostudy: no study')"
: > "$T/t3-calls"
check "start again the same day: nothing listed, no thread" "already 0" "$(python3 "$R/bin/project-learn" start | grep -o already) $(wc -l < "$T/t3-calls")"

printf '%s\n' "$(date -u +%F) $(date -u +%FT%TZ) thread thread-2; 1 to sort: vikejs/vike; FAILED: o/other (gh failed)" > "$L/runs.txt"; : > "$T/t3-calls"
check "start the same day after a run whose thread started though one repo's list failed: no second thread" "already 0" "$(python3 "$R/bin/project-learn" start | grep -o already) $(wc -l < "$T/t3-calls")"

# a repo whose list fails, over the cap: the thread still condenses it, its failure named
rm "$L/runs.txt"; printf '# o/broken\n## Who decides\nboss\n' > "$P/o/broken.md"; yes word | head -n 2501 >> "$P/o/broken.md"; printf 'Studied: 2026-10-29\n' > "$P/o/broken.study.md"; : > "$T/t3-calls"
python3 "$R/bin/project-learn" start >/dev/null 2>&1; rc=$?
check "start: an over-cap repo whose list fails goes to the thread to condense, its list saying so; the run names the failure and exits 1" "1 1 1 1" \
  "$rc $(tail -n1 "$T/prompt" | grep -cx "Lists: $L/lists/o__broken.txt $L/lists/vikejs__vike.txt") $(head -n1 "$L/lists/o__broken.txt" | grep -c "^# o/broken: the list failed (.*unexpected gh.*): condense the project file only; don't mark it$") $(grep -c "^$(date -u +%F) .* thread thread-1; 2 to sort: o/broken vikejs/vike; FAILED: o/broken (" "$L/runs.txt")"
rm "$P/o/broken.md" "$P/o/broken.study.md"

# ---------- GitLab: the project file names the repo's GitLab URL, so glab reads it; invented answers in the shapes glab gives ----------
# (the award emoji are made up in the shape of the empty answers glab gives)
mkdir -p "$P/g"
printf '%s\n' '# g/r' '' 'GitLab (https://gitlab.com/g/r). Use `glab`, not `gh`.' '## Who decides' \
  'boss (Boss Person) merges. The main authors per area: api: Boss Person, carol.' > "$P/g/r.md"
printf 'Studied: 2026-10-28\n' > "$P/g/r.study.md"
GB='<img src=\"https://github.com/claude.png\" width=\"20\" height=\"20\" alt=\"Claude\"> *Claude wrote this*'
GP=projects/g%2Fr; W=https://gitlab.com/g/r
note() { # id type author created body [new_path] [award]
  local pos=null award=''
  [ -n "${6:-}" ] && pos="{\"newPath\": \"$6\"}"
  [ -n "${7:-}" ] && award="{\"name\": \"$7\"}"
  printf '{"id": "gid://gitlab/%s/%s", "system": false, "author": {"username": "%s"}, "createdAt": "%s", "body": "%s", "position": %s, "awardEmoji": {"nodes": [%s]}}' "$2" "$1" "$3" "$4" "$5" "$pos" "$award"; }
CF=src/api/flow.py
cat > "$T/glab.json" <<EOF
{
"graphql:mergeRequests": {"data": {"project": {"mergeRequests": {"count": 3, "pageInfo": {"hasNextPage": false, "endCursor": null}, "nodes": [
  {"iid": "32", "webUrl": "$W/-/merge_requests/32", "description": "$GB", "updatedAt": "2026-10-30T20:18:56Z", "awardEmoji": {"nodes": [{"name": "thumbsup"}]},
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [
     $(note 9001 Note boss 2026-10-30T01:41:27Z "$GB" '' thumbsup),
     {"id": "gid://gitlab/Note/9002", "system": true, "author": {"username": "boss"}, "createdAt": "2026-10-30T01:12:44Z", "body": "marked this merge request as **draft**", "position": null, "awardEmoji": {"nodes": []}},
     $(note 9003 Note boss 2026-10-29T15:03:09Z "or give it a new tag, so it can be filtered"),
     $(note 9004 Note boss 2026-10-29T15:02:51Z "The gallery could collect these too.")]}},
  {"iid": "26", "webUrl": "$W/-/merge_requests/26", "description": "$GB", "updatedAt": "2026-10-28T23:44:05Z", "awardEmoji": {"nodes": []},
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [
     $(note 9005 DiffNote boss 2026-10-28T23:43:47Z "$GB" "$CF"),
     $(note 9006 DiffNote boss 2026-10-28T16:35:16Z "Not like this. Why is code here?" "$CF")]}},
  {"iid": "50", "webUrl": "$W/-/merge_requests/50", "description": "Ha párhuzamosan érkeznek", "updatedAt": "2026-10-30T10:00:00Z", "awardEmoji": {"nodes": []},
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [
     $(note 501 DiffNote carol 2026-10-30T09:00:00Z "Run this in CI" .gitlab-ci.yml),
     $(note 502 Note carol 2026-10-30T09:05:00Z "a conversation note on their MR")]}}]}}}},
"graphql:issues": {"data": {"project": {"issues": {"count": 3, "pageInfo": {"hasNextPage": false, "endCursor": null}, "nodes": [
  {"iid": "8", "webUrl": "$W/-/work_items/8", "description": "# their design issue", "updatedAt": "2026-10-30T20:00:00Z",
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [
     $(note 9010 Note nitedani 2026-10-30T19:00:00Z "$GB"),
     $(note 9011 Note boss 2026-10-30T19:30:00Z "Let's postpone this")]}},
  {"iid": "7", "webUrl": "$W/-/work_items/7", "description": "$GB", "updatedAt": "2026-10-30T22:51:36Z",
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [
     $(note 9007 Note boss 2026-10-30T22:37:50Z "There is sample code for this in the app already"),
     {"id": "gid://gitlab/Note/9008", "system": true, "author": {"username": "boss"}, "createdAt": "2026-10-31T04:14:04Z", "body": "mentioned in commit 1234abcd", "position": null, "awardEmoji": {"nodes": []}}]}},
  {"iid": "5", "webUrl": "$W/-/work_items/5", "description": "# their issue", "updatedAt": "2026-10-28T15:27:34Z",
   "notes": {"pageInfo": {"hasNextPage": false}, "nodes": [$(note 9009 Note boss 2026-10-28T15:30:00Z "a note on an issue not ours")]}}]}}}},
"$GP/merge_requests/32/award_emoji": [{"name": "thumbsup", "user": {"username": "boss"}, "created_at": "2026-10-30T19:00:00.000Z"}],
"$GP/merge_requests/32/notes/9001/award_emoji": [{"name": "thumbsup", "user": {"username": "boss"}, "created_at": "2026-10-30T02:00:00.000Z"}],
"$GP/merge_requests/32/commits": [
  {"id": "5afe5afe00000000000000000000000000000000", "parent_ids": ["a"], "author_name": "Boss Person", "committed_date": "2026-10-29T12:00:00.000+00:00", "title": "#7: our MR's squash", "message": "#7: our MR's squash", "web_url": "$W/-/commit/5afe5afe00000000000000000000000000000000"}],
"$GP/issues/7/award_emoji": [],
"$GP/merge_requests/26/commits": [
  {"id": "aaaa111111000000000000000000000000000000", "parent_ids": ["a"], "author_name": "nitedani-agent", "committed_date": "2026-10-28T20:58:41.000+01:00", "title": "#7: a fix", "message": "#7: a fix\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n", "web_url": "$W/-/commit/aaaa111111000000000000000000000000000000"},
  {"id": "bbbb222222000000000000000000000000000000", "parent_ids": ["a", "b"], "author_name": "Boss Person", "committed_date": "2026-10-28T18:59:07.000+01:00", "title": "Merge remote-tracking branch 'origin/master'", "message": "Merge remote-tracking branch 'origin/master'", "web_url": "$W/-/commit/bbbb222222000000000000000000000000000000"},
  {"id": "c0ffee0000000000000000000000000000000000", "parent_ids": ["a"], "author_name": "Boss Person", "committed_date": "2026-10-28T21:10:00.000+01:00", "title": "rename", "message": "rename\n", "web_url": "$W/-/commit/c0ffee0000000000000000000000000000000000"}],
"$GP/merge_requests:merged": [{"iid": 26, "merged_at": "$(date -u -d '-3 days' +%FT%T.000Z)", "merge_commit_sha": null, "squash_commit_sha": "5afe5afe00000000000000000000000000000000", "description": "$GB"}],
"$GP/merge_requests/26/diffs": [{"new_path": "$CF", "old_path": "$CF"}],
"$GP/repository/commits": [
  {"id": "5afe5afe00000000000000000000000000000000", "parent_ids": ["a"], "author_name": "Boss Person", "committed_date": "2026-10-28T23:44:04.000+00:00", "title": "#7: our MR's squash", "message": "#7: our MR's squash", "web_url": "$W/-/commit/5afe5afe00000000000000000000000000000000"},
  {"id": "a70f00d000000000000000000000000000000000", "parent_ids": ["a"], "author_name": "carol", "committed_date": "$(date -u -d '-1 days' +%FT%T.000+00:00)", "title": "flow: CI fix", "message": "flow: CI fix", "web_url": "$W/-/commit/a70f00d000000000000000000000000000000000"},
  {"id": "a70f00e000000000000000000000000000000000", "parent_ids": ["a"], "author_name": "carol", "committed_date": "$(date -u -d '-1 days' +%FT%T.000+00:00)", "title": "flow: lint", "message": "flow: lint", "web_url": "$W/-/commit/a70f00e000000000000000000000000000000000"},
  {"id": "b0b0000000000000000000000000000000000000", "parent_ids": ["a"], "author_name": "carol", "committed_date": "$(date -u -d '-1 days' +%FT%T.000+00:00)", "title": "elsewhere", "message": "elsewhere", "web_url": "$W/-/commit/b0b0000000000000000000000000000000000000"}],
"$GP/repository/commits/a70f00d000000000000000000000000000000000/diff": [{"new_path": "$CF"}],
"$GP/repository/commits/a70f00e000000000000000000000000000000000/diff": [{"new_path": "$CF"}],
"$GP/repository/commits/b0b0000000000000000000000000000000000000/diff": [{"new_path": "README.md"}],
"$GP/members/all": [{"username": "boss", "name": "Boss Person", "access_level": 30}, {"username": "carol", "name": "Carol Doe", "access_level": 20}]
}
EOF
cat > "$T/bin/glab" <<EOF
#!/usr/bin/env python3
import json, re, sys, time
open("$T/glab-calls", "a").write(' '.join(a.replace(chr(10), ' ') for a in sys.argv[1:]) + '\n')
m = json.load(open("$T/glab.json"))
if 'graphql' in sys.argv:
    q = next(a for a in sys.argv if a.startswith('query='))
    print(json.dumps(m['graphql:' + re.search(r'project\(fullPath: \\\$p\) \{ (\w+)\(', q)[1]])); sys.exit()
p = sys.argv[-1]; key = p.split('?')[0] + (':merged' if 'state=merged' in p else '')
page = int(re.search(r'[?&]page=(\d+)', p)[1])
if key not in m:
    sys.exit(f"unexpected glab {p}")
print(json.dumps(m[key] if page == 1 else m.get(f'{key}:page{page}', [])))
EOF
# MR 32's awards fill a first page, so the maintainer's is on the second
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); k="projects/g%2Fr/merge_requests/32/award_emoji"; m[k+":page2"]=m[k]; m[k]=[{"name":"eyes","user":{"username":"eve"},"created_at":"2026-10-30T18:00:00.000Z"}]*100; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json"
chmod +x "$T/bin/glab"; : > "$T/gh-calls"
python3 "$R/bin/project-learn" list g/r > "$T/gl"; rc=$?; cp "$T/glab-calls" "$T/glab-calls.list"
check "GitLab: read through glab, never gh; GET calls and GraphQL queries only; award emoji read only for the two posts that have one (MR 32's on two pages), and for our issue (GraphQL has no awardEmoji on an issue)" "0 0 0 0 4" \
  "$rc $(wc -l < "$T/gh-calls") $(grep -v '^api --hostname gitlab.com graphql ' "$T/glab-calls" | grep -vc '^api --hostname gitlab.com projects/[^ ]*page=[0-9]*$') $(grep '^api --hostname gitlab.com graphql ' "$T/glab-calls" | grep -c mutation) $(grep -c award_emoji "$T/glab-calls")"
check "GitLab: the maintainer's note and threaded note on our MR, their inline note, their note on our issue" "1 1 1 1" \
  "$(grep -cF $'2026-10-29T15:02:51Z\tcomment\tboss\t'"$W/-/merge_requests/32#note_9004"$'\tThe gallery' "$T/gl") $(grep -c $'\tcomment\tboss\t.*#note_9003\tor give it a new tag' "$T/gl") $(grep -c $'\tinline\tboss\t.*26#note_9006\tsrc/api/flow.py: Not like this' "$T/gl") $(grep -c $'\tcomment\tboss\t.*work_items/7#note_9007' "$T/gl")"
check "GitLab: award emoji on our MR and on our note; the maintainer's commit on our MR; their inline note on someone else's MR; a follow-up on a file of our merged MR" "1 1 1 1 1" \
  "$(grep -c $'\treaction\tboss\t'"$W/-/merge_requests/32"$'\tthumbsup on our MR' "$T/gl") $(grep -c $'\treaction\tboss\t.*#note_9001\tthumbsup on our comment' "$T/gl") $(grep -c $'2026-10-28T20:10:00Z\tcommit\tBoss Person\t.*/commit/c0ffee0' "$T/gl") $(grep -c $'\tothers-inline\tcarol\t.*50#note_501\t.gitlab-ci.yml: Run this in CI' "$T/gl") $(grep -c $'\tfollow-up\tcarol\t.*/commit/a70f00d.*\tchanges src/api/flow.py from !26: flow: CI fix' "$T/gl")"
check "GitLab: left out: our badged notes, system notes, our commit, a merge, our MR's squash on master, another file, a conversation note on their MR, an issue not ours" "0 0 0 0 0 0 0 0" \
  "$(grep 'note_9001' "$T/gl" | grep -vc $'\treaction\t') $(grep -c 'note_9002\|note_9008' "$T/gl") $(grep -c aaaa111 "$T/gl") $(grep -c bbbb222 "$T/gl") $(grep -c 5afe5af "$T/gl") $(grep -c b0b0000 "$T/gl") $(grep -c note_502 "$T/gl") $(grep -c 'work_items/5' "$T/gl")"
cp "$P/g/r.md" "$T/gr.md"; echo '- an MR note !32/n9004, an issue note #7/n9007, one with its repo g/r!26/n9006; another repo'"'"'s x/y!50/n501' >> "$P/g/r.md"
python3 "$R/bin/project-learn" list g/r > "$T/gl2"; cp "$T/gr.md" "$P/g/r.md"
check "GitLab: left out: what the project file cites by short ref alone (an MR note, an issue note, one with its repo); another repo's same number listed" "0 0 0 1" \
  "$(grep -c note_9004 "$T/gl2") $(grep -c note_9007 "$T/gl2") $(grep -c note_9006 "$T/gl2") $(grep -c note_501 "$T/gl2")"

# a first study: no project file or study yet names the forge, so the repo's URL does
mkdir "$T/first"; mv "$P/g/r.md" "$P/g/r.study.md" "$T/first/"; : > "$T/gh-calls"; : > "$T/glab-calls"
python3 "$R/bin/project-learn" list https://gitlab.com/g/r.git --since 2026-10-28T00:00:00Z > "$T/first/out" 2>&1; rc=$?
check "list <GitLab URL> with no project file or study (a first study): read through glab, never gh, ending with the mark" "0 0 1 1" \
  "$rc $(wc -l < "$T/gh-calls") $(grep -c "^api --hostname gitlab.com graphql .*p=g/r " "$T/glab-calls" | sed 's/^[1-9][0-9]*$/1/') $(tail -n1 "$T/first/out" | grep -c '^# read whole: project-learn mark g/r ')"
check "a first GitLab study, no ## Who decides: a member at access level 30 (Developer, the lowest that can push) is a maintainer (their note and their commit listed), one at 20 isn't" "1 1 0" \
  "$(grep -c $'\tcomment\tboss\t.*#note_9004' "$T/first/out") $(grep -c $'\tcommit\tBoss Person\t.*/commit/c0ffee0' "$T/first/out") $(grep -c $'\tcarol\t' "$T/first/out")"
mv "$T/first/r.md" "$T/first/r.study.md" "$P/g/"
check "GitLab: GitLab returning fewer MRs than it counts fails the list, saying so" "1 1" \
  "$(cp "$T/glab.json" "$T/glab.full"; python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["graphql:mergeRequests"]["data"]["project"]["mergeRequests"]["count"]=5; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json"; python3 "$R/bin/project-learn" list g/r >/dev/null 2>"$T/err"; echo $?; cp "$T/glab.full" "$T/glab.json") $(grep -c 'GitLab returned 3 of the 5 mergeRequests of g/r' "$T/err")"
check "GitLab: our merged MR's squash commit, on an MR stacked on it, is not the maintainer's commit" 0 "$(grep -c $'\tcommit\t.*/commit/5afe5af' "$T/gl")"
cp "$T/glab.json" "$T/glab.full"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["projects/g%2Fr/merge_requests:merged"][0]["merged_at"]=sys.argv[2]; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json" "$(date -u -d '-90 days' +%FT%T.000Z)"
python3 "$R/bin/project-learn" list g/r --since "$(date -u -d '-1 year' +%F)" > "$T/gl-year" 2>&1; rc=$?; cp "$T/glab.full" "$T/glab.json"
check "GitLab, a year back: our MR merged 90 days ago (outside the 60-day follow-ups), its squash on an MR stacked on it is not the maintainer's commit" "0 0 1" \
  "$rc $(grep -c $'\tcommit\t.*/commit/5afe5af' "$T/gl-year") $(grep -c $'\tcommit\tBoss Person\t.*/commit/c0ffee0' "$T/gl-year")"
check "GitLab: their issue holding our badged note is our work: their reply there listed" 1 "$(grep -c $'\tcomment\tboss\t.*work_items/8#note_9011\tLet' "$T/gl")"
check "GitLab: an MR with over 100 comments fails the list, naming it, rather than reading part of it" "1 1" \
  "$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["graphql:mergeRequests"]["data"]["project"]["mergeRequests"]["nodes"][0]["notes"]["pageInfo"]["hasNextPage"]=True; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json"; python3 "$R/bin/project-learn" list g/r >/dev/null 2>"$T/err"; echo $?) $(grep -c 'merge_requests/32 has over 100 comments' "$T/err")"
# the pacing measured in-process, from the start times pace() records: a stub's own start-up time never moves them
cp "$T/glab.full" "$T/glab.json"; paced=$(python3 - "$R/bin/project-learn" <<'PY'
import contextlib, importlib.machinery, importlib.util, io, sys
loader = importlib.machinery.SourceFileLoader('project_learn', sys.argv[1])
pl = importlib.util.module_from_spec(importlib.util.spec_from_loader('project_learn', loader)); loader.exec_module(pl)
starts, real = [], pl.pace
pl.pace = lambda log, s: (real(log, s), starts.append(log[-1]))
with contextlib.redirect_stdout(io.StringIO()):
    pl.main(['list', 'g/r'])
print(int(len(starts) > 5 and min(b - a for a, b in zip(starts, starts[1:])) >= 1.2))
PY
)
check "GitLab: every glab call, each page its own, starts at least 1.2 s after the last (gitlab.com's per-user rate limit, shared with sessions); MR 32's second page read" "1 1" \
  "$paced $(grep -c 'merge_requests/32/award_emoji?per_page=100&page=2$' "$T/glab-calls.list")"
check "GitLab: two commits change our merged MR's file, two follow-ups, and the MR's diffs are read once" "2 1" \
  "$(grep -c $'\tfollow-up\tcarol\t.*from !26: flow' "$T/gl") $(grep -c 'merge_requests/26/diffs' "$T/glab-calls.list")"
check "GitLab: 11 items, ending with the mark that covers them" "11 1" "$(grep -vc '^#' "$T/gl") $(tail -n1 "$T/gl" | grep -c '^# read whole: project-learn mark g/r ')"

# a GitLab repo glab can't read (not logged in, no access, moved: GraphQL answers a null project, exit 0), or no glab at all:
# that repo is FAILED in runs.txt with why, and every other repo is still listed and sent to the thread or marked
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["graphql:mergeRequests"]=m["graphql:issues"]={"data":{"project":None}}; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json"
python3 "$R/bin/project-learn" list g/r >/dev/null 2>"$T/err"; rc=$?
check "GitLab: a null project fails the list naming the repo and why, no traceback" "1 1 0" "$rc $(grep -c "glab on gitlab.com can't read g/r (not logged in" "$T/err") $(grep -c Traceback "$T/err")"
rm -f "$L/runs.txt" "$T/prompt"; python3 "$R/bin/project-learn" start >/dev/null 2>"$T/err"; rc=$?
check "start: a GitLab repo glab can't read is FAILED in runs.txt with why; vike still goes to the thread; no traceback" "1 1 1 0" \
  "$rc $(grep -c "^$(date -u +%F) .* thread thread-1; 1 to sort: vikejs/vike; FAILED: g/r (project-learn: glab on gitlab.com can't read" "$L/runs.txt") $(tail -n1 "$T/prompt" | grep -cx "Lists: $L/lists/vikejs__vike.txt") $(grep -c Traceback "$T/err")"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["graphql:mergeRequests"]="an answer of an unexpected shape"; json.dump(m,open(sys.argv[1],"w"))' "$T/glab.json"
rm -f "$L/runs.txt" "$T/prompt"; python3 "$R/bin/project-learn" start >/dev/null 2>"$T/err"; rc=$?
check "start: any exception in one repo's list (here an answer of an unexpected shape) is that repo's FAILED line; vike still goes to the thread" "1 1 1 0" \
  "$rc $(grep -c "; 1 to sort: vikejs/vike; FAILED: g/r (AttributeError: " "$L/runs.txt") $(tail -n1 "$T/prompt" | grep -cx "Lists: $L/lists/vikejs__vike.txt") $(grep -c Traceback "$T/err")"
mkdir "$T/noglab"; ln -s "$T/bin/gh" "$T/bin/t3" /usr/bin/python3 /usr/bin/touch "$T/noglab/"  # every command start runs, but glab
rm -f "$L/runs.txt" "$T/prompt"; PATH="$T/noglab" /usr/bin/python3 "$R/bin/project-learn" start >/dev/null 2>"$T/err"; rc=$?
check "start with no glab on PATH: the GitLab repo FAILED saying so; vike still goes to the thread; no traceback" "1 1 1 0" \
  "$rc $(grep -c "; 1 to sort: vikejs/vike; FAILED: g/r (project-learn: no glab on PATH" "$L/runs.txt") $(tail -n1 "$T/prompt" | grep -cx "Lists: $L/lists/vikejs__vike.txt") $(grep -c Traceback "$T/err")"

# a maintainer's commit made before the mark and pushed after it: listed once (its date is when it was made, not pushed)
printf '# o/late\n## Who decides\nboss merges.\n' > "$P/o/late.md"; lm=$(date -u -d '-1 hour' +%FT%TZ); printf 'Studied: 2026-10-01\nLearned: %s\n' "$lm" > "$P/o/late.study.md"
python3 - "$T/gh.json" "$(date -u -d '-30 min' +%FT%TZ)" "$(date -u -d '-3 hours' +%FT%TZ)" "$(date -u -d '-2 days' +%FT%TZ)" "$(date -u -d '-5 days' +%FT%TZ)" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); B = '<img src="x" alt="Claude"> *Claude wrote this*'
m['search:o/late'] = {'items': [{'number': 5, 'pull_request': {}, 'user': {'login': 'nitedani-agent'}, 'updated_at': sys.argv[2], 'body': B,
                                  'url': 'https://api.github.com/repos/o/late/issues/5', 'html_url': 'https://github.com/o/late/pull/5', 'reactions': {'total_count': 0}}]}
m['search:o/late:merged'] = {'items': []}
for k in ('issues/5/comments', 'pulls/5/reviews', 'pulls/5/comments'):
    m[f'repos/o/late/{k}'] = []
m['repos/o/late/pulls/5/commits'] = [{'sha': 'cafe' + '0' * 36, 'author': {'login': 'boss'}, 'parents': [{}],
                                      'commit': {'message': 'simplify the loop', 'committer': {'date': sys.argv[3]}}}]
m['search:o/late:merged'] = {'items': [{'number': n, 'pull_request': {}, 'user': {'login': 'nitedani-agent'}, 'body': B} for n in (6, 7)]}
for n in (6, 7):  # two merged PRs of ours change src/a.ts
    m[f'repos/o/late/pulls/{n}'] = {'merged_at': sys.argv[4], 'merge_commit_sha': f'bee{n}' * 10}
    m[f'repos/o/late/pulls/{n}/files'] = [{'filename': 'src/a.ts'}]
m['repos/o/late/commits'] = [{'sha': 'f00d' + '0' * 36, 'html_url': 'https://github.com/o/late/commit/f00d' + '0' * 36, 'author': {'login': 'boss'},
                              'parents': [{}], 'commit': {'message': 'tidy a', 'committer': {'date': sys.argv[3]}}},
                             {'sha': 'a1d0' + '0' * 36, 'html_url': 'https://github.com/o/late/commit/a1d0' + '0' * 36, 'author': {'login': 'boss'},
                              'parents': [{}], 'commit': {'message': 'before our merge', 'committer': {'date': sys.argv[5]}}}]
m['repos/o/late/commits/f00d' + '0' * 36] = {'files': [{'filename': 'src/a.ts'}]}
m['repos/o/late/commits/a1d0' + '0' * 36] = {'files': [{'filename': 'src/a.ts'}]}
json.dump(m, open(sys.argv[1], 'w'))
PY
printf 'Commits read: 1111111@%s fffffff@%s\n' "$(date -u -d '-9 days' +%FT%TZ)" "$(date -u -d '-2 days' +%FT%TZ)" >> "$P/o/late.study.md"; : > "$T/gh-calls"; touch "$T/late.t0"
first=$(python3 "$R/bin/project-learn" list o/late); python3 "$R/bin/project-learn" mark $(echo "$first" | tail -n1 | cut -d' ' -f6-) >/dev/null
check "list: a maintainer's commit on our PR made before the mark and pushed after it is listed; once marked, it isn't listed again, the study recording it" "1 0 1" \
  "$(echo "$first" | grep -c $'\tcommit\tboss\thttps://github.com/o/late/pull/5/commits/cafe0') $(python3 "$R/bin/project-learn" list o/late | grep -c $'\tcommit\t') $(grep -c '^Commits read: cafe000@' "$P/o/late.study.md")"
check "list: a maintainer's follow-up on the default branch made before the mark and pushed after it is listed; once marked, it isn't listed again, the study recording it" "1 0 1" \
  "$(echo "$first" | grep -c $'\tfollow-up\tboss\thttps://github.com/o/late/commit/f00d0.*changes src/a.ts from #6') $(python3 "$R/bin/project-learn" list o/late | grep -c $'\tfollow-up\t') $(grep -c '^Commits read: .*f00d000@' "$P/o/late.study.md")"
s=$(grep -o 'repos/o/late/commits?since=[^&]*' "$T/gh-calls" | head -n1 | cut -d= -f2); lag=$(( $(date -d "$lm" +%s) - $(date -d "$s" +%s) >= 7 * 86400 ))
check "list: the default branch's commits are asked for from at least 7 days before the mark, on GitHub and GitLab" "1 1" "$lag $(grep -c 'repository/commits?since=2026-10-21T00:00:00Z&' "$T/glab-calls.list")"
check "list: a follow-up touching files of two merged PRs of ours is one item naming both, and one sha on the mark line" "1 1 1" \
  "$(echo "$first" | grep -c $'\tfollow-up\t.*/commit/f00d0') $(echo "$first" | grep -c 'changes src/a.ts from #6, #7: tidy a') $(echo "$first" | tail -n1 | grep -o 'f00d000@' | wc -l)"
check "list: a default-branch commit made before our earliest merge has no files read (it can't follow any merge), and isn't listed" "0 0" \
  "$(grep -c 'repos/o/late/commits/a1d0' "$T/gh-calls") $(echo "$first" | grep -c a1d0)"
check "list only prints: no file under ~/.mergeworthy outside the projects folder changed since the late lists" 0 "$(find "$HOME/.mergeworthy" -newer "$T/late.t0" -type f ! -path "$P/*" | wc -l)"
check "mark: Commits read keeps the listed commits of the last 7 days, the study's earlier ones too, dropping one 9 days old" "0 1 1" "$(grep -c 1111111 "$P/o/late.study.md") $(grep -c '^Commits read: .*cafe000@' "$P/o/late.study.md") $(grep -c '^Commits read: .*fffffff@' "$P/o/late.study.md")"
rm "$P/o/late.md" "$P/o/late.study.md"

# a trial run on copies: both folders through the environment, relative, from another directory; the thread runs in the learn folder
C="$T/cwd"; mkdir -p "$C/rel/projects/vikejs"; cp "$T/vike.md" "$C/rel/projects/vikejs/vike.md"; printf 'Studied: 2026-10-29\n' > "$C/rel/projects/vikejs/vike.study.md"
cp "$P/vikejs/vike.study.md" "$T/vike.study.real"; rm -f "$L/runs.txt" "$T/prompt"
(cd "$C" && MERGEWORTHY_PROJECTS=rel/projects MERGEWORTHY_LEARN_DIR=rel/learn python3 "$R/bin/project-learn" start >/dev/null 2>&1)
cmd=$(sed -n 's/.*`project-learn` being `\([^`]*\)`.*/\1/p' "$T/prompt")
(cd "$C/rel/learn" && bash -c "$cmd $(tail -n1 lists/vikejs__vike.txt | cut -d' ' -f5-)" >/dev/null 2>&1)
check "start from another directory with relative MERGEWORTHY_PROJECTS and MERGEWORTHY_LEARN_DIR: runs.txt and the list in the learn folder, none in HOME's; the prompt names both folders absolute; the thread's mark, run from the learn folder, moves the copy's study, not the real one" "1 1 0 1 1 1" \
  "$(grep -c 'thread thread-1; 1 to sort: vikejs/vike' "$C/rel/learn/runs.txt" 2>/dev/null) $(tail -n1 "$T/prompt" | grep -cx "Lists: $C/rel/learn/lists/vikejs__vike.txt") $(ls "$L/runs.txt" 2>/dev/null | wc -l) \
$(grep -cF "being \`MERGEWORTHY_PROJECTS=$C/rel/projects MERGEWORTHY_LEARN_DIR=$C/rel/learn $R/bin/project-learn\`. The project files and studies are in $C/rel/projects;" "$T/prompt") $(grep -c '^Learned: ' "$C/rel/projects/vikejs/vike.study.md") $(cmp -s "$P/vikejs/vike.study.md" "$T/vike.study.real" && echo 1 || echo 0)"

# a search that matched more than GitHub returns (it stops at 1000): the list fails rather than treat the rest as nothing
printf '# o/big\n## Who decides\nboss merges.\n' > "$P/o/big.md"; printf 'Studied: 2026-10-29\n' > "$P/o/big.study.md"
python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["search:o/big"]={"total_count":1500,"items":[]}; m["search:o/big:merged"]={"items":[]}; json.dump(m,open(sys.argv[1],"w"))' "$T/gh.json"
python3 "$R/bin/project-learn" list o/big >/dev/null 2>"$T/err"; rc=$?
rm -f "$L/runs.txt"; python3 "$R/bin/project-learn" start >/dev/null 2>&1
check "list: a search GitHub cuts short (0 of 1500) in every part down to one second fails, saying so; start records it under FAILED and leaves its mark" "1 1 1 0" \
  "$rc $(grep -c "counts 1500 items, all updated in one second (GitHub's search stops at 1000)" "$T/err") $(grep -c 'FAILED: .*o/big (project-learn: the search' "$L/runs.txt") $(grep -c '^Learned:' "$P/o/big.study.md")"
rm "$P/o/big.md" "$P/o/big.study.md"
python3 - "$T/gh.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
issue = lambda n, at: {'number': n, 'user': {'login': 'eve'}, 'updated_at': at, 'url': f'https://api.github.com/repos/o/huge/issues/{n}', 'body': ''}
m['search:o/huge'] = {'all': [issue(n, f'2026-{1 + n % 9:02}-{1 + n % 28:02}T{n % 24:02}:{n % 60:02}:00Z') for n in range(2500)]}
m['search:o/huge:merged'] = m['search:o/huge']
m['search:o/short'] = {'total_count': 150, 'items': [issue(n, '2026-05-05T05:05:05Z') for n in range(120)]}
m['search:o/second'] = {'all': [issue(n, '2026-05-05T05:05:05Z') for n in range(1001)]}
json.dump(m, open(sys.argv[1], 'w'))
PY
: > "$T/gh-calls"; : > "$T/searches"; got=$(PYTHONPATH="$R/hooks" python3 -c 'from gh_common import search; print(len({i["number"] for i in search("repo:o/huge updated:>=2025-11-01")}))')
check "search: 2500 matches, over GitHub's 1000, read whole by halving the updated: range from its start, each part within 1000" "2500 1 1" \
  "$got $(grep -c 'updated:>=2025-11-01&' "$T/gh-calls") $(grep -q 'updated:2025-11-01T00:00:00Z\.\.' "$T/gh-calls" && echo 1)"
check "search: a part counting over 1000 costs its first page alone, split at once; no page is read twice" "0 0" \
  "$(awk -F'\t' '$3 > 1000 && $2 > 1' "$T/searches" | wc -l) $(cut -f2,4 "$T/searches" | sort | uniq -d | wc -l)"
: > "$T/searches"; got=$(PYTHONPATH="$R/hooks" python3 -c 'import collections, gh_common; gh_common.SEARCHES = collections.deque(maxlen=5); gh_common.SEARCH_WINDOW = 1
starts, real = [], gh_common.pace; gh_common.pace = lambda log, s: (real(log, s), starts.append(log[-1]))
print(len(gh_common.search("repo:o/huge is:pr closed:>=2025-11-01")), int(len(starts) > 10 and min(b - a for a, b in zip(starts, starts[5:])) >= 0.999))')
check "search: requests paced (here 5 in any 1 s, GitHub's 30 a minute scaled down); a search with no updated:>= splits from its own closed:>= (the merged search's merged:>= alike)" "2500 1 1 0" \
  "$got $(grep -c 'closed:>=2025-11-01 updated:2025-11-01T00:00:00Z\.\.' "$T/searches" | sed 's/^[1-9][0-9]*$/1/') $(grep -c 'updated:2008' "$T/searches")"
: > "$T/searches"; got=$(PYTHONPATH="$R/hooks" python3 -c 'import collections, gh_common; gh_common.SEARCHES = collections.deque(maxlen=100)
print(len(gh_common.search("repo:o/huge is:pr is:merged merged:>=2025-11-01")))')
check "search: followups()' merged search, over 1000, splits from its own merged:>=" "2500 1" \
  "$got $(grep -c 'merged:>=2025-11-01 updated:2025-11-01T00:00:00Z\.\.' "$T/searches" | sed 's/^[1-9][0-9]*$/1/')"
PYTHONPATH="$R/hooks" python3 -c 'from gh_common import search; search("repo:o/short updated:>=2026-01-01")' 2>"$T/err"; rc=$?
check "search: under 1000, a read returning fewer than it counts (120 of 150) exits, so no mark moves past the rest" "1 1" "$rc $(grep -c "returned 120 of its 150 items" "$T/err")"
PYTHONPATH="$R/hooks" python3 -c 'from gh_common import search; search("repo:o/huge is:pr")' 2>"$T/err"; rc=$?
check "search: over 1000 with no lower bound to split from: exits saying so" "1 1" "$rc $(grep -c "counts 2500 items, over the 1000 GitHub's search returns, and has no lower bound" "$T/err")"
PYTHONPATH="$R/hooks" python3 -c 'from gh_common import search; search("repo:o/second updated:>=2026-01-01")' 2>"$T/err"; rc=$?
check "search: 1001 updated in one second can't be split further: exits saying so" "1 1" "$rc $(grep -c "counts 1001 items, all updated in one second" "$T/err")"

# ---------- gh_output: a stub gh answering each call from the next line of $F/answers (<exit>\t<text>), `gh api rate_limit` from $F/limits ----------
F="$T/flaky"; mkdir -p "$F"
cat > "$F/gh" <<EOF
#!/usr/bin/env python3
import sys
if sys.argv[1:] == ['api', 'rate_limit']:
    print(open("$F/limits").read()); sys.exit()
open("$F/calls", "a").write(' '.join(sys.argv[1:]) + '\n')
lines = open("$F/answers").read().splitlines(); code, text = lines[0].split('\t', 1); open("$F/answers", "w").write(''.join(l + '\n' for l in lines[1:]))
print(text, file=sys.stderr if int(code) else sys.stdout); sys.exit(int(code))
EOF
chmod +x "$F/gh"
flaky() { # <path> <answer>...: gh_pages(<path>)'s first page and the waits it slept, each answer used once
  printf '%s\n' "${@:2}" > "$F/answers"; : > "$F/calls"
  PATH="$F:$PATH" PYTHONPATH="$R/hooks" python3 -c 'import math, sys, gh_common; waits = []; gh_common.time.sleep = waits.append
try: print(gh_common.gh_pages(sys.argv[1], paginate=False), end=" ")
finally: print([math.ceil(w) for w in waits], end="")' "$1" 2>"$F/err"; }
limits() { echo "{\"resources\": {\"core\": {\"remaining\": $1, \"reset\": $(( $(date +%s) + $2 ))}, \"search\": {\"remaining\": $3, \"reset\": $(( $(date +%s) + $4 ))}, \"graphql\": {\"remaining\": 5000, \"reset\": 0}}}" > "$F/limits"; }
limits 5000 3600 30 60
OK=$'0\t{"n": 1}'
check "gh_output: a network timeout, then a 502, then the answer: retried after 5 s and 30 s, the page returned" "[{'n': 1}] [5, 30] 3" \
  "$(flaky repos/o/x $'1\tGet "https://api.github.com/repos/o/x": dial tcp 140.82.121.5:443: i/o timeout' $'1\tgh: HTTP 502' "$OK") $(wc -l < "$F/calls")"
check "gh_output: a network failure that outlasts its retries exits naming the call, after 3 tries" "[5, 30] 1 1 3" \
  "$(flaky repos/o/x $'1\tgh: Server Error (HTTP 503)' $'1\tgh: Server Error (HTTP 503)' $'1\tgh: Server Error (HTTP 503)'; echo " $?") $(grep -c '^-c: gh api repos/o/x failed: gh: Server Error (HTTP 503)$' "$F/err") $(wc -l < "$F/calls")"
limits 0 3600 0 30
check "gh_output: a search's rate limit lifting in 30 s (the core one spent for an hour) is waited out, then the page returned" "[{'n': 1}] [31] 2" \
  "$(flaky 'search/issues?q=x' $'1\tgh: API rate limit exceeded for user ID 1. (HTTP 403)' "$OK") $(wc -l < "$F/calls")"
check "gh_output: the core rate limit spent for an hour exits at once, naming the reset" "[] 1 1 1" \
  "$(flaky repos/o/x $'1\tgh: API rate limit exceeded for user ID 1. (HTTP 403)'; echo " $?") $(grep -cE '^-c: gh api repos/o/x failed: gh: API rate limit exceeded for user ID 1. \(HTTP 403\); resets at [0-9T:-]+Z$' "$F/err") $(wc -l < "$F/calls")"
limits 4000 3600 30 60
check "gh_output: a secondary rate limit (calls left) waits GitHub's minute, then the page returned" "[{'n': 1}] [60] 2" \
  "$(flaky repos/o/x $'1\tgh: You have exceeded a secondary rate limit. Please wait a few minutes before you try again. (HTTP 403)' "$OK") $(wc -l < "$F/calls")"
check "gh_output: a 404 exits at once with gh's error, no retry" "[] 1 1 1" \
  "$(flaky repos/o/x $'1\tgh: Not Found (HTTP 404)'; echo " $?") $(grep -c '^-c: gh api repos/o/x failed: gh: Not Found (HTTP 404)$' "$F/err") $(wc -l < "$F/calls")"

[ "$fails" = 0 ] && echo "project-learn: all cases pass" || { echo "project-learn: $fails case(s) failed"; exit 1; }
