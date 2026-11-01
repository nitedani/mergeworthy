"""What bin/steward and bin/project-learn both read GitHub with: the agent's badge, a maintainer's association, times, and paged
GET calls that exit naming the failed call."""
import collections, datetime, json, os, re, subprocess, sys, time, urllib.parse

BADGE = re.compile(r'\A\s*(?:<img [^>]*alt="(?:Claude|Codex)"[^>]*>\s*)+')  # an agent's post starts with its badge
MAINTAINER = ('OWNER', 'MEMBER', 'COLLABORATOR')
UPDATED = re.compile(r'(?:^| )updated:>=\S+')
LOWER = re.compile(r'(?:^| )(?:updated|merged|closed|created):>=(\S+)')  # a search's own lower bound: each implies updated:>= it
SEARCHES, SEARCH_WINDOW = collections.deque(maxlen=30), 60  # the start times of the last search requests: GitHub allows 30 a minute


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def epoch(s):
    """An ISO time; one without a zone, or a date, is local."""
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def when(s):
    """An ISO time, or a bare date as its 00:00 UTC (epoch() reads one as local)."""
    return epoch(s + 'T00:00:00Z' if re.fullmatch(r'\d{4}-\d\d-\d\d', s) else s)


def pace(log, seconds):
    """Waits until one more call fits log.maxlen calls in any `seconds`; log: a deque of the last calls' start times."""
    if len(log) == log.maxlen:
        time.sleep(max(0.0, log[0] + seconds - time.monotonic()))
    log.append(time.monotonic())


def read(path):
    try:
        return open(path, errors='replace').read()
    except OSError:
        return ''


def gh_pages(path, paginate=True):
    """Every page of a GET as one list (an object answer as a list of itself); paginate=False: its first page only."""
    r = subprocess.run(['gh', 'api', *(['--paginate', '--slurp'] if paginate else []), path], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{os.path.basename(sys.argv[0])}: gh api {path} failed: {r.stderr.strip()[:200]}")
    pages = json.loads(r.stdout or '[]')
    return [x for p in (pages if isinstance(pages, list) else [pages]) for x in (p if isinstance(p, list) else [p])]


def search(q, span=None):
    """Every issue and PR a search matches, one request a page, paced to GitHub's 30 search requests a minute. GitHub's search returns
    at most 1000, so a search whose first page counts more is read as the two halves of its `updated:` range instead (from the
    query's own lower bound to a day from now, so a post updated while it reads moves to a part read later), halving until each part
    is within 1000. Exits when it can't split (no lower bound, or a single second counting more) or a part returns fewer than it
    counts, since a reader would take the rest as nothing. span: the (from, to) seconds this call reads."""
    sub = q if span is None else f"{UPDATED.sub('', q).strip()} updated:{iso(span[0])}..{iso(span[1])}"
    def page(n):
        pace(SEARCHES, SEARCH_WINDOW)
        return gh_pages(f"search/issues?q={urllib.parse.quote_plus(sub, safe=':<>=/')}&per_page=100&page={n}", paginate=False)[0]
    first = page(1)
    total, name = first['total_count'], os.path.basename(sys.argv[0])
    if total <= 1000:
        items = first['items'] + [i for n in range(2, -(-total // 100) + 1) for i in page(n)['items']]
        if len(items) < total:
            sys.exit(f"{name}: the search {sub!r} returned {len(items)} of its {total} items")
        return items
    if span is None:
        if not (m := LOWER.search(q)):
            sys.exit(f"{name}: the search {q!r} counts {total} items, over the 1000 GitHub's search returns, and has no lower bound (updated:>=, merged:>=, closed:>= or created:>=) to split it from")
        span = (int(when(m[1])), int(time.time()) + 86400)
    if span[0] >= span[1]:
        sys.exit(f"{name}: the search {sub!r} counts {total} items, all updated in one second (GitHub's search stops at 1000)")
    mid = (span[0] + span[1]) // 2
    return list({i['url']: i for half in ((span[0], mid), (mid + 1, span[1])) for i in search(q, half)}.values())
