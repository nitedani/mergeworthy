"""Tests of the watcher's share of GitHub's API budget (watcher/gh-watch.py), offline: a stand-in GitHub (watch_sim.py) with
ETags and rate-limit headers, a simulated clock, and the real watcher code. Usage: tests/watch-budget.py [repo root]
Prints "case: <got> (want <want>)"; exits 0 only when every case matches."""
import collections, contextlib, importlib.util, itertools, json, os, re, shutil, sys, tempfile, threading

R = os.path.realpath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import watch_sim as ws

T = tempfile.mkdtemp()
os.environ.update(HOME=f'{T}/home', GH_WATCH_ME='me')
os.makedirs(f'{T}/home/.claude')
fails, counter = 0, itertools.count()


def check(name, want, got):
    global fails
    print(f"{name}: {got} (want {want})")
    if want != got:
        fails += 1
        print("  ^ FAIL")


def fresh_home():
    """A clean ~/.mergeworthy and ~/.claude, so a case starts from nothing."""
    shutil.rmtree(f'{T}/home', ignore_errors=True)
    os.makedirs(f'{T}/home/.claude')
    os.makedirs(f'{T}/home/.mergeworthy')


def load(d, sim, daemon=None):
    """The watcher as a daemon of watch dir d would run it: a fresh module (a restart is a new process), the sim's clock, events into d/events.log."""
    spec = importlib.util.spec_from_file_location(f'ghw{next(counter)}', f'{R}/watcher/gh-watch.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.HERE, m.STATE, m.THREADS = d, f'{d}/gh-watch-state.json', f'{d}/threads.txt'
    m.time, m.datetime = ws.clock_for(sim, daemon)
    def emit(line):
        with open(f'{d}/events.log', 'a') as f:
            f.write(line + '\n')
    m.emit = emit
    return m


def make_dirs(names=None):
    dirs = {}
    for name, threads in ws.DIRS.items():
        if names and name not in names:
            continue
        d = f'{T}/{name}'
        shutil.rmtree(d, ignore_errors=True)  # no state from an earlier case
        os.makedirs(d)
        open(f'{d}/threads.txt', 'w').write('\n'.join(threads) + '\n')
        open(f'{d}/repos.txt', 'w').close()
        open(f'{d}/events.log', 'w').close()
        open(f'{d}/gh-watch.pid', 'w').write(str(os.getpid()))
        dirs[name] = d
    open(f'{T}/home/.claude/gh-watch-dirs.txt', 'w').write('\n'.join(dirs.values()) + '\n')
    open(f'{T}/home/.mergeworthy/main-watch', 'w').write(dirs.get('d1', '') + '\n')
    return dirs


def tag(line):
    t = line.split()
    return ' '.join(t[:3] if len(t) > 2 and t[2] == 'comment' else t[:4])


def events(dirs):
    out = []
    for name, d in dirs.items():
        out += [(name, tag(l)) for l in open(f'{d}/events.log') if l.startswith('###')]
    return sorted(out)


def simulate(restart_at=1800, hours=5400):
    """Seven daemons for 90 minutes; at restart_at every one of them is stopped and started again (a plugin update).
    -> (gh, events per dir, the events expected, errors)"""
    fresh_home()
    sim = ws.Sim()
    gh = ws.FakeGitHub(sim)
    expected = ws.build_world(gh)
    dirs = make_dirs()
    def start():
        for name, d in dirs.items():
            sim.spawn(name, lambda daemon, d=d: load(d, sim, daemon).main())
    with ws.Shim(gh):
        start()
        sim.run_until(ws.T0 + restart_at)
        sim.stop_all()
        start()
        sim.run_until(ws.T0 + hours)
        sim.stop_all()
    return gh, events(dirs), expected(), sim.errors


# ---------- 1. seven daemons and a restart, for an hour ----------
gh, got, want, errors = simulate()
core, graphql = gh.count('core'), gh.count('graphql')
BUDGET = int(os.environ.get('WATCH_BUDGET', 500))
detail_counts = collections.Counter(p for t, m, p, s, r in gh.log if re.fullmatch(r'repos/[^/]+/[^/]+/commits/[0-9a-f]{40}', p) and s != 304)
print(f"measured over the simulated 90 minutes: core calls {core}, graphql calls {graphql}, 304 answers {sum(1 for e in gh.log if e[3] == 304)}, commit-detail reads {sum(detail_counts.values())} of {len(detail_counts)} commits")
check("simulation: no daemon crashed", [], [e[1].strip().splitlines()[-1] for e in errors])
check(f"seven daemons and a restart for 90 minutes: counted calls within {BUDGET}", True, core <= BUDGET)
check("no commit's detail is read: follow-ups are project-learn's", 0, sum(detail_counts.values()))
check("events: each comment and /agent command arrives once, in the right dir; no FOLLOW-UP", want, got)
restart_core = gh.count("core", upto=ws.T0 + 2300) - gh.count("core", upto=ws.T0 + 1800)
print(f"measured: core calls in the 500 s after the restart: {restart_core}")
check("a restart of all seven costs few calls: counted calls in the 500 s after it are at most 8", True, restart_core <= 8)




# ---------- 2. the cases below each start from a fresh machine ----------
@contextlib.contextmanager
def world(**kw):
    fresh_home()
    sim = ws.Sim()
    gh = ws.FakeGitHub(sim)
    ws.build_world(gh)
    dirs = make_dirs(**kw)
    with ws.Shim(gh):
        yield sim, gh, dirs


def case(name, want):
    def deco(fn):
        try:
            got = fn()
        except Exception as e:
            got = f"error: {type(e).__name__}: {e}"
        check(name, want, got)
    return deco


def lines(d, prefix='###'):
    return [l.strip() for l in open(f'{d}/events.log') if l.startswith(prefix)]


@case("rate limit: the remaining calls GitHub reports are kept in the shared state, and the level follows them (ok / reserve below 1500 / low below 500), until the reset", "4999 0 1 2 0")
def _():
    with world() as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        m.request('user')
        out = [json.load(open(f'{T}/home/.mergeworthy/shared-watch.json'))['rate']['core']['remaining'], m.level()]
        for left in (1400, 400):
            gh.remaining = left
            m.request('user')
            out.append(m.level())
        sim.now = gh.reset + 1  # the window is over
        out.append(m.level())
        return ' '.join(map(str, out))


def calls_of(tick_with, left):
    """Paths requested by one round of a daemon of d1 (and d2) when GitHub reports `left` calls remaining."""
    with world() as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        gh.remaining = left
        mark = len(gh.log)
        try:
            m.request('user')  # a call that tells the daemon how much is left
            mark = len(gh.log)
            tick_with(m, sim)
        except AttributeError as e:  # the watcher before the budget has no request() or tick()
            return [f"error: {e}"]
        return [p for t, mth, p, s, r in gh.log[mark:]]


def two_rounds(m, sim):
    m.tick()  # the first scans, then the shared jobs
    sim.now += 700
    m.tick()


ok_paths, reserve_paths, low_paths = calls_of(two_rounds, 4000), calls_of(two_rounds, 1400), calls_of(two_rounds, 400)
discovery = lambda p: p.startswith('search/') or bool(re.fullmatch(r'repos/[^/]+/[^/]+/(issues|pulls)/comments', p.split('?')[0]))


@case("budget: with 1400 calls left the shared work (discovery) does nothing and the daemon's own threads are still scanned", "False True")
def _():
    return f"{any(discovery(p) for p in reserve_paths)} {any(p.endswith('/issues/101/comments') for p in reserve_paths)}"


@case("budget: with 4000 left the same rounds do the shared work (control)", True)
def _():
    return any(discovery(p) for p in ok_paths)


@case("budget: with 400 left only the notifications fast path is called", ["notifications"])
def _():
    return sorted(set(low_paths))


def pause_case(secondary, length=1800):
    with world() as (sim, gh, dirs):
        a, b = load(dirs['d1'], sim), load(dirs['d2'], sim)
        gh.limited_until, gh.secondary = sim.now + length, secondary
        for _ in range(5):  # five rounds of two daemons during the pause
            a.tick(); b.tick()
            sim.now += 10
        refused = sum(1 for e in gh.log if e[3] == 403)
        until = json.load(open(f'{T}/home/.mergeworthy/shared-watch.json'))['pause_until']
        shown = [lines(dirs[d], 'note: API budget') for d in ('d1', 'd2')]
        a2 = load(dirs['d1'], sim)  # a restart in the middle of the pause says nothing more
        a2.tick()
        sim.now = until + 1  # the pause is over
        gh.limited_until = 0
        a2.tick()
        woke = sum(1 for d in ('d1', 'd2') for l in open(f'{dirs[d]}/events.log') if a.EVENT.search(l))
        return refused, int(until - ws.T0), [len(x) for x in shown], shown[0][0] if shown[0] else '', len(lines(dirs['d1'], 'note: API budget')), woke, len(gh.log) > refused


@case("rate limit answer (403): one 403 stops every daemon; each logs one `note: API budget: paused until <reset>` and wakes nobody, none more after its restart; calls resume after the reset", "(1, 1800, [1, 1], 'note: API budget: paused until 2026-10-09T12:30:00Z', 1, 0, True)")
def _():
    return str(pause_case(False))


@case("secondary rate limit (403 with Retry-After 120): paused for those 120 s", "(1, 120, [1, 1], 'note: API budget: paused until 2026-10-09T12:02:00Z', 1, 0, True)")
def _():
    return str(pause_case(True, 120))


@case("conditional request: the second GET of a list sends If-None-Match, GitHub answers 304, it counts nothing and reads as no news; a changed list is a 200 again", "[1, 304, [], 1, 2, 2]")
def _():
    with world() as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        store, url = {}, 'repos/vikejs/vike/issues/101/comments?per_page=100'
        first = len(m.paged(url, store))
        out = [first, m.request(url, store=store).status, m.paged(url, store), gh.count('core')]
        gh.comment('vikejs/vike', 101, 'alice', 'new')
        return str(out + [len(m.paged(url, store)), gh.count('core')])


@case("conditional request through `gh api -i` (GH_HOST set): gh exits 1 on a 304 and still prints the headers; it is read as a 304", [200, 304])
def _():
    with world() as (sim, gh, dirs):
        os.environ['GH_HOST'] = 'github.com'
        try:
            m = load(dirs['d1'], sim)
            store, url = {}, 'repos/vikejs/vike/issues/101/comments?per_page=100'
            return [m.request(url, store=store).status, m.request(url, store=store).status]
        finally:
            del os.environ['GH_HOST']


@case("validators wait for the caller: with `pending` the store is unchanged until the caller keeps them (a failed scan must not turn its retry into a 304)", "0 1")
def _():
    with world() as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        store, pending = {}, {}
        m.request('repos/vikejs/vike/issues/101/comments?per_page=100', store=store, pending=pending)
        out = [len(store)]
        store.update(pending)
        return f"{out[0]} {len(store)}"


@case("a daemon's thread scans cost nothing when nothing changed, and nothing after a restart (ETags are in its state file)", "0 0")
def _():
    with world() as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        m.run_scan()
        n = gh.count('core')
        sim.now += 400
        m.run_scan()
        again = gh.count('core') - n
        sim.now += 400
        load(dirs['d1'], sim).run_scan()
        return f"{again} {gh.count('core') - n - again}"


@case("discovery: seven daemons at the same moment read each repo's two comment feeds once, not seven times; due again after 5 minutes, but only for a repo something moved in", "12 12 14")
def _():
    with world() as (sim, gh, dirs):
        mods = [load(d, sim) for d in dirs.values()]
        n = lambda: sum(1 for e in gh.log if e[2].endswith('/comments') and e[2].count('/') == 4)
        before = n()
        for m in mods:
            m.shared_pass()
        first = n() - before
        sim.now += 200
        for m in mods:
            m.shared_pass()
        second = n() - before
        gh.comment('vikejs/vike', 101, 'alice', 'something moves in one repo')
        sim.now += 101
        for m in mods:
            m.shared_pass()
        return f"{first} {second} {n() - before}"


@case("leases: while one daemon holds the lease another skips the shared jobs and asks GitHub for nothing; when it is free the job runs once", "False 0 1")
def _():
    with world() as (sim, gh, dirs):
        a, b = load(dirs['d1'], sim), load(dirs['d2'], sim)
        with a.lease():
            with b.lease() as theirs:
                mark = len(gh.log)
                b.shared_pass()
                skipped = len(gh.log) - mark
        b.shared_pass()
        runs = len([e for e in gh.log if e[2].endswith('/issues/comments')]) > 0
        return f"{theirs} {skipped} {int(runs)}"


@case("leases: two daemons starting a pass together, one blocked inside its first call: the other returns at once, and the pass ran once", "True 1")
def _():
    with world() as (sim, gh, dirs):
        a, b = load(dirs['d1'], sim), load(dirs['d2'], sim)
        gate = threading.Event()
        gh.hold = gate
        t = threading.Thread(target=a.shared_pass)
        t.start()
        for _ in range(500):  # a is now inside its first request
            if gh.hold is None:
                break
            threading.Event().wait(.01)
        mark = len(gh.log)
        b.shared_pass()
        b_calls = len(gh.log) - mark
        gate.set()
        t.join(10)
        b.shared_pass()  # a is done: the jobs are not due again
        discovery = [e for e in gh.log if e[2].endswith('/issues/comments')]
        return f"{b_calls == 0} {len(discovery) // len(set(e[2] for e in discovery))}"


@case("shared jobs survive a restart: a new process finds the jobs not due and calls nothing", 0)
def _():
    with world() as (sim, gh, dirs):
        load(dirs['d1'], sim).shared_pass()
        mark = len(gh.log)
        load(dirs['d2'], sim).shared_pass()
        return len(gh.log) - mark


@case("a renamed repo's old path (301 Moved Permanently) is followed to its new one, so its items come back", [6106953944])
def _():
    with world(names=['d1']) as (sim, gh, dirs):
        m = load(dirs['d1'], sim)
        asked = []
        def get(path, headers):
            asked.append(path)
            if path.startswith('repos/o/old/'):
                return m.Resp(301, {'location': 'https://api.github.com/repos/o/new/issues/12/comments'}, '{"message": "Moved Permanently"}')
            return m.Resp(200, {}, '[{"id": 6106953944}]')
        m.http_get = get
        return [c['id'] for c in m.paged('repos/o/old/issues/12/comments')]

shutil.rmtree(T, ignore_errors=True)
print(f"failures: {fails}")
sys.exit(1 if fails else 0)
