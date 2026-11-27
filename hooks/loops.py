"""Review loops (delegate §Review rounds): pre-agent-dedupe and pre-bash-guard ask whether round `<loop>-r<N>` of a code review may
run, and record a round that ran with register(); pr-steps and gate-pass ask close() whether a loop's ledger closes it, and
pr-steps asks open_seats() whether a step's other seats closed. admit() refuses a fresh reader's second round, or its first again
on this head (fresh_once), then, on a head within STALE_LINES of a loop's earlier rounds, the first of its RULES that objects: a
round past the four of the loops it counts in (routed_cap) or of its own (cap), a ledger that doesn't rule the last round
(ledger_current) or every finding of the loop's reports (findings_ruled), and a last round that brought no fixed blocker or
should (earned). third_seat() refuses a fresh round 1 its step's declared seats leave out, and old_reports() a fresh later round
handed an earlier round's report."""
import collections, glob, json, os, re, subprocess, sys, types
import agent_jobs, drift, ledger, records, review_journal, testpaths

HOST = 'antigravity' if os.environ.get('MERGEWORTHY_HOST') == 'antigravity' else 'claudeAgent'  # the main session's company (hooks/agy.py sets it)
# a post review's {loop: {'threads': the T3 threads or Claude agents its rounds ran in}}, where its later rounds are sent
LOOPS = os.path.expanduser('~/.claude/review-loops.json')
# what the installed version records, rounds {loop: [[n, heads]]} and threads {loop: [thread]}: read until one release after
# the journal is installed on every machine
OLD = {'rounds': os.path.expanduser('~/.claude/review-rounds.json'), 'threads': os.path.expanduser('~/.claude/review-threads.json')}


def round_of(name):
    """A review round `<loop>-r<N>`, maybe followed by the date or head SHA a reused clientRequestId needs: the match, loop and N."""
    return re.fullmatch(r'(.+)-r(\d+)', re.sub(r'(-\d{4}-\d{2}-\d{2}|-[0-9a-f]{7,40})+$', '', name.strip()))


def _json(path):
    try: data = json.load(open(path))
    except (OSError, ValueError): return {}
    return data if isinstance(data, dict) else {}


def handle_loops(handle):
    """The loops whose rounds ran in the reviewer handle (a T3 thread, a Claude agent): {loop: its first round's journal event,
    or None for a post review's round, which review-loops.json holds, or one OLD holds}."""
    data, old = _json(LOOPS), _json(OLD['threads'])  # read once: a message to a thread that never reviewed waits on nothing
    here = {l: None for l in {*data, *old} if handle in (data[l].get('threads', []) if isinstance(data.get(l), dict) else old.get(l, []))}
    return {**here, **{l: evs[0] for l, evs in review_journal.rounds(handle=handle).items()}}


Name = collections.namedtuple('Name', 'subject kind seat')
ROUTED = {'recheck', 'fresh'}  # the kinds of a round routed to a seat's loop of its subject (converge steps 2 and 4), counted in its four


def name(loop):
    """loop's (subject, kind, seat) (delegate §Review rounds): `<loop>-ask<N>` is kind ask of that loop, `<slice>-reverify`,
    `-recheck` and `-fresh` that kind of the slice, with no seat; any other `<step-or-slice>-<seat>` is kind seat, as is a name
    with no dash, its own subject with seat ''."""
    if m := re.fullmatch(r'(.+)-(?:(reverify|recheck|fresh)|(ask)\d+)', loop): return Name(m[1], m[2] or m[3], '')
    subject, _, seat = loop.rpartition('-')
    return Name(subject, 'seat', seat) if subject else Name(loop, 'seat', '')


def follows(loop, l):
    """Whether round 1 of loop continues the loop l: an ask of l, or a reverify, recheck or fresh of l's subject."""
    k = name(loop)
    return k.kind == 'ask' and l == k.subject or k.kind in ('reverify', 'recheck', 'fresh') and name(l).subject == k.subject


def continues(loop, n, here):
    """Whether round n of loop continues one of the loops here (handle_loops) that ran in the reviewer it is sent to: a later round of
    one of them, or a round 1 that follows one (delegate §Review rounds)."""
    return loop in here if n >= 2 else any(follows(loop, l) for l in here)


CAP = 4  # rounds per loop on one head (delegate §Review rounds)
SEATING = 'converge §Running the agents'  # the fan-out of a round 1 seating a step's reviewers at once (delegate §Reviewers)
Directives = collections.namedtuple('Directives', 'step fix_check seats fills continues fanout ledger')


def directives(brief):
    """The lines of a launch's brief the hooks read: the step its `Review: <step> [<part>]` declares and whether that line says
    fix-check, the seats `Seats: <seat>, …` declares, the seat or loop `Fallback: <seat> failed …` names first (which it fills),
    the loops its `Continues: <loop>` lines take over, the step its `Fan-out: <step>` line names, and the ledger path it names
    first; each None without (continues: [])."""
    line = lambda key, value: re.search(r'^[ \t>*-]*' + key + r':[ \t]*' + value, brief, re.M)
    st, se, fb = line('Review', '(' + '|'.join(STEPS) + r')\b'), line('Seats', '(.+)$'), line('Fallback', r'([^\s<,:;]+)')
    fan = re.search(r'^Fan-out: (finality step [23]|design step [34]|pull-request step 5|' + SEATING + ')$', brief, re.M)
    led = re.search(r'(/[^\s`\'"()]+\.ledger\.md)\b', brief)
    return Directives(st and st[1], bool(line('Review', r'[^\n]*\bfix-check\b')), se and [x for x in re.split(r'[\s,]+', se[1]) if x] or None,
                      fb and fb[1], re.findall(r'^[ \t>*-]*Continues:[ \t]*(\S+)', brief, re.M), fan and fan[1], led and led[1])


def register(loop, n, heads, *, thread=None, post=False, outs=(), seated=False, checkouts=(), led=None, step=None, seats=None, fills=None, company=None):
    """Records round n of loop that ran: a post review's thread in review-loops.json; a code review's in the journal of each
    change its brief names (checkouts), else in review_journal.UNPINNED, with the heads its brief pinned, the reports it writes
    (outs), the thread it ran in, whether it is one of its step's seats (seated: its round 1 brief's `Fan-out:` line names
    SEATING), the ledger it names (led), the step its `Review:` line declares, the seats its `Seats:` line does, the seat its
    `Fallback:` line fills and the company it ran on."""
    if post:
        def ran(loops):
            threads = loops.setdefault(loop, {'threads': []})['threads']
            if thread not in threads: threads.append(thread)
        if thread: agent_jobs.locked_update(LOOPS, ran)
        return
    event = {'ev': 'round', 'loop': loop, 'n': n, 'heads': heads, 'outs': sorted({os.path.realpath(o) for o in outs}), 'thread': thread, 'seated': seated,
             'checkouts': list(checkouts), 'ledger': led, 'step': step, 'seats': seats, 'fills': fills, 'company': company}
    for c in dict.fromkeys(filter(None, map(review_journal.change_of, checkouts))) or [review_journal.UNPINNED]: review_journal.append(c, event)


PENDING = os.path.expanduser('~/.claude/review-pending')  # a Bash command's admitted rounds and post launches, until it ended


def pend(key, rounds, launches):
    """Holds, for the Bash command key (own_actions.key), the register() keywords of each review round it runs and the draft sha
    of each post review output it writes (review_launch.set_aside), until post-bash-register settles them."""
    if rounds or launches:
        os.makedirs(PENDING, exist_ok=True)
        with open(os.path.join(PENDING, key + '.json'), 'w') as f: json.dump({'rounds': rounds, 'launches': launches}, f)


def settle(key, ran):
    """The Bash command key ended: what pend() held for it is registered when it ran (exit 0), else dropped."""
    import review_launch
    try: held = json.load(open(p := os.path.join(PENDING, key + '.json'))); os.remove(p)
    except (OSError, ValueError): return
    if ran:
        for out, aside in held["launches"].items(): review_launch.launch(out, aside)
        for r in held['rounds']: register(**r)


STEPS = ('verify', 'reverify', 'shape', 'fresh', 'small', 'post', 'docs')  # what a loop checks (its brief's `Review: <step>`)


def lineage(checkout):
    """{loop: its round events} in the journal of checkout's change whose pinned heads are all in its HEAD's history (rounds that
    pinned none left out)."""
    return review_journal.rounds(review_journal.change_of(checkout), keep=lambda e: e['heads'] and all(desc(checkout, h, 'HEAD') for h in e['heads']))


def same_company_seat(loop, tops):
    """Whether loop's round 1 on the lineage of one of the checkouts tops was a seat (seated) on the main session's
    company, whose later rounds stay on it (delegate §Reviewers)."""
    return any((evs := lineage(t).get(loop)) and evs[0].get('seated') and evs[0].get('company') == HOST for t in tops)


def step_of(loop, first):
    """The step a loop checks: its round 1's `Review: <step>`, else its name's `<step-or-slice>` (a slice's: verify)."""
    stem = name(loop).subject
    return first.get('step') or (stem if stem in STEPS else 'verify')


def open_seats(report, recorded, step, checkout='.'):
    """The other seats of report's step on checkout's lineage, each still open: a loop whose round 1 seated it (seated
    or `Seats:`) checking step, or one its round 1's `Seats: <seat>, …` declares that never ran, none of whose reports is in
    recorded (the outputs pr-steps recorded on the head), and no loop filling it (its round 1's `Fallback: <seat>`) closed.
    A step closes only once every seat's loop did."""
    report, on = os.path.realpath(report), lineage(checkout)
    mine = [l for l, evs in on.items() if any(report in e['outs'] for e in evs)]
    named = {f"{name(l).subject}-{s}" for l in mine for s in on[l][0].get('seats') or ()}
    seats = {l for l, evs in on.items() if (evs[0].get('seated') or evs[0].get('seats')) and step_of(l, evs[0]) == step} | named
    stem = lambda l: name(l).subject
    filled = {f if f.startswith(stem(l) + '-') else f"{stem(l)}-{f}": l for l, evs in on.items() if (f := evs[0].get('fills'))}
    done = lambda l: l in mine or l in on and {o for e in on[l] for o in e['outs']} & set(recorded)
    return sorted(l for l in seats if not done(l) and not (l in filled and done(filled[l])))


git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
SHA = r'\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b'


def pinned(L):
    """(the checkouts launch L's brief names, their heads that its pinned SHAs equal)."""
    shas = set(re.findall(SHA, L.brief))
    return L.checkouts, sorted({h for t in L.checkouts if (h := git(t, 'rev-parse', 'HEAD').stdout.strip()) and any(h.startswith(x) for x in shas)})


desc = lambda t, o, h: git(t, 'merge-base', '--is-ancestor', o, h).returncode == 0


def on_head(loop, n, tops, heads):
    """The rounds before n of loop that ran on heads (in the checkouts tops) or within STALE_LINES of the branch's own changed lines of them."""
    # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
    def own_lines(t, o, h):
        rows = re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M)
        gen = testpaths.generated(t, [p for _, _, p in rows])
        return testpaths.moved([r for r in rows if r[2] not in gen], 'cap')
    def built_on(old):
        # a head neither pinned by the round nor built on its pins is another checkout's; one built on them past the lines leaves it out
        if not old: return not heads
        matched = False
        for h in heads:
            under = [] if h in old else [(t, o) for t in tops for o in old if desc(t, o, h)]
            if h not in old and not under: continue
            matched = True
            if under and not any(own_lines(t, o, h) <= testpaths.STALE_LINES for t, o in under): return False
        return matched
    return sorted({m for m, old, *_ in rounds_of(loop, tops) if m < n and built_on(old)})


def rounds_of(loop, tops):
    """loop's rounds [[n, heads, outs]] the journals of the changes of the checkouts tops hold, else review_journal.UNPINNED's (a
    round whose brief named no checkout), else OLD's."""
    for changes in dict.fromkeys(filter(None, map(review_journal.change_of, tops))), [review_journal.UNPINNED]:
        if found := [[e['n'], e['heads'], e['outs']] for c in changes for e in review_journal.rounds(c).get(loop, [])]: return found
    return [[m, old, []] for m, old, *_ in _json(OLD['rounds']).get(loop, [])]


def third_seat(loop, tops, d):
    """Why round 1 of the seat loop, launched fresh, is refused: its step's round 1 on this lineage declared other seats (`Seats:`)
    and its brief's directives d neither say what failed (`Fallback:`) nor which loop it takes over (`Continues:`); '' otherwise."""
    stem, kind, seat = name(loop)
    named = {s for t in tops for l, evs in lineage(t).items() if l != loop and name(l).subject == stem for s in evs[0].get('seats') or ()}
    if kind != 'seat' or not named or seat in named or d.fills or any(c[:1] != '<' for c in d.continues): return ''
    return (f"{loop}-r1 would be a third seat of {stem}, whose round 1 declared {', '.join(sorted(named))}: continue a declared seat, "
            "or, when its launch failed, say so in a line `Fallback: <what failed>`; a seat taking over another's count names it, `Continues: <loop>` (mergeworthy:delegate §Review rounds).\n")


NUMBER = 'zero one two three four five six seven eight nine'.split()  # CAP in a refusal's words


def fresh_once(loop, n, tops, heads, step):
    """A fresh read's seat (its brief's `Review: fresh`, else its round 1's) runs once: no round 2, nor its round 1 again on this head."""
    fresh = (step or next((evs[0].get('step') for t in tops if (evs := lineage(t).get(loop))), None)) == 'fresh'
    if fresh and (n >= 2 or on_head(loop, 2, tops, heads)):
        again = '' if n >= 2 else f", and this seat already ran on this head or one within {testpaths.STALE_LINES} changed lines of it"
        return (f"{loop}-r{n}: the fresh reader runs once (mergeworthy:converge step 4){again}; its findings go back to the loops that own them, "
                "`<slice>-fresh` (mergeworthy:delegate §Review rounds).\n")
    return ''


def routed_cap(a):
    """A routed round, or one taking over a loop, counts in its owners' four."""
    if not a.routed: return ''
    return (f"{a.loop}-r{a.n} counts in the {NUMBER[CAP]} rounds per head of {', '.join(a.owners)}, which already ran {', '.join(a.shared)}"
            + (f" and {a.loop} {', '.join(f'r{m}' for m in a.earlier)}" if a.earlier else '')
            + f" on this head or one within {testpaths.STALE_LINES} changed lines of it: a recheck or a fresh reader's findings go to their seat's loop "
            "within its four (mergeworthy:delegate §Review rounds). " + a.finality + "List what is still open in the report or the PR body's notes and go on.\n")


def cap(a):
    """A loop gets CAP rounds per head."""
    if len(a.earlier) < CAP: return ''
    return (f"{a.loop} already ran {', '.join(f'r{m}' for m in a.earlier)} on this head or one within {testpaths.STALE_LINES} changed lines of it "
            f"({', '.join(h[:12] for h in a.heads) or 'no head pinned'}): a loop gets {NUMBER[CAP]} rounds per head, and a head past those lines is a new one "
            "(mergeworthy:delegate §Review rounds). "
            + a.finality + "List what is still open in the report or the PR body's notes and go on (push, ready, the next step) without waiting for an answer; "
            "only an open blocker keeps the PR in draft. A maintainer's ask on a new head starts a new loop name. " + a.closing)


def ledger_current(a):
    """The ledger rules the last round before the next is sent."""
    if not (a.led and os.path.isfile(a.led) and a.last < a.earlier[-1]): return ''
    return (f"{a.loop}-r{a.n} follows r{a.earlier[-1]}, but the ledger {a.led} shows round {a.last} as its last: rule r{a.earlier[-1]}'s findings in it first "
            f"(each `R{a.earlier[-1]}.<n> <label> <outcome>`, then `Round: {a.earlier[-1]}`), then send the round (mergeworthy:delegate §Review rounds).\n")


def findings_ruled(a):
    """The ledger rules every finding of the loop's earlier reports on this head."""
    import review_launch
    said = [o for m, _, outs in rounds_of(a.loop, a.tops) if m in a.earlier for o in outs if not review_launch.draft_of(o)]
    if not (a.led and os.path.isfile(a.led) and (missing := unruled(a.rows, said))): return ''
    return (f"{a.loop}-r{a.n} follows r{a.earlier[-1]}, but the ledger {a.led} doesn't rule every finding of its loop's reports:\n" + '\n'.join(missing)
            + "\nRule each (`R<round>.<n> <label> <outcome>`), then send the round (mergeworthy:delegate §Review rounds).\n")


def earned(a):
    """A loop gets its next round only while its last round brought a blocker or should kept and fixed."""
    if a.kept: return ''
    return (f"{a.loop}-r{a.n} follows r{a.earlier[-1]} on this head or one within {testpaths.STALE_LINES} changed lines of it, and a loop gets its next round only "
            "while its last round brought a blocker or should you kept and fixed (mergeworthy:delegate §Review rounds), but "
            + ("the brief names no `<work folder>/drafts/<review>.ledger.md` to show it: name the loop's ledger in the brief, or end the loop. " if not a.led else
               f"{a.led} doesn't exist: name the loop's ledger, or end the loop. " if not os.path.isfile(a.led) else
               f"the ledger {a.led} shows round {a.last} brought none `fixed in <sha>`: the loop ends there. ")
            + a.closing)


RULES = (routed_cap, cap, ledger_current, findings_ruled, earned)  # in the order a launch is told what to fix


def admit(loop, n, tops, heads, led, owners=(), launcher=(), step=None):
    """Why round n of code review loop is refused, '' when it may run: tops are the checkouts its brief names, heads their heads
    its pins equal, led the ledger path it names (None), owners the loops whose rounds count in its four (a routed round's seat
    loop, the loop a `Continues:` line takes over), launcher the launcher's checkout, which holds the fixes of a brief naming none (a
    docs reader's, handed rendered pages), step the step its brief declares (`Review: <step>`)."""
    if why := fresh_once(loop, n, tops, heads, step): return why
    a = types.SimpleNamespace(loop=loop, n=n, tops=tops, heads=heads, led=led, owners=owners, earlier=on_head(loop, n, tops, heads),
                              shared=[f"{o} r{m}" for o in owners for m in on_head(o, 10 ** 9, tops, heads)])
    a.routed = bool(a.shared) and len(a.earlier) + len(a.shared) >= CAP
    if not a.earlier and not a.routed: return ''
    try: a.rows, _, a.last = ledger.read(led) if led and os.path.isfile(led) else ([], [], 0)
    except OSError as e: return f"the ledger {led} can't be read ({e.strerror}), so no round of {loop} is admitted: fix it, or name the loop's ledger (mergeworthy:delegate §Review rounds).\n"
    a.kept = ledger.owed(a.rows, a.last, lambda sha: any(desc(t, sha, 'HEAD') for t in tops or launcher))
    a.finality = (f"The ledger {led} shows round {a.last} still brought a blocker or should fixed in a commit: the area keeps taking patches, so its next step is "
                  "the finality pass (mergeworthy:finality step 1, recorded by `pr-steps finality <file>`), not another round. " if a.kept else "")
    a.closing = f"Close the loop with `pr-steps <step> <file> --ledger {led or '<ledger>'}` on r{a.earlier[-1]}'s report when it isn't clean: the agent's own report is the record, never one the main session writes.\n" if a.earlier else ''
    return next((why for rule in RULES if (why := rule(a))), '')


def old_reports(loop, n, tops, paths, outs, brief):
    """Why round n of loop, launched on a fresh reviewer, is refused for naming (among paths, its outputs outs aside) a report of an
    earlier round of its loop, '' otherwise: a fresh reviewer gets the ledger and the commits since, never the reports
    (delegate §Reviewers); a new agent taking over a seat past its context (`Continues: <loop>`) gets the last one."""
    if n < 2 or directives(brief).continues: return ''
    import review_launch
    mine = {os.path.realpath(o) for o in outs} | {os.path.realpath(w) for w in re.findall(r'\bWrite (/[^\s`\'"():]+)', brief)}
    old = {o for m, _, said in rounds_of(loop, tops) if m < n for o in said if not review_launch.draft_of(o)} - mine
    named = sorted(old & {os.path.realpath(p) for p in paths})
    return (f"{loop}-r{n} goes to a fresh reviewer, whose brief carries the loop's ledger and the commits since, never an earlier round's report, "
            f"but it names {', '.join(named)} (mergeworthy:delegate §Reviewers): take it out; a new agent taking over a seat past its context "
            "names the loop it continues in a line `Continues: <loop>` (converge §Running the agents).\n") if named else ''


# per kind of loop: the fix outcome that closes a finding, why the completed round leaves the loop open ('' when it doesn't), and
# whether a later round confirming the fix closes it (a post's draft has no sha)
KINDS = {
    # a round 4 that still brought a fix closes its loop only once the finality pass is recorded on the head
    'code': ('fixed in <sha>', lambda rows, last, p, reached, ran, checkout: '' if not ledger.owed(rows, last, reached) else
             f'{p} closes round {last}, which brought a blocker or should fixed in a commit: the loop gets its next round first' if ran < CAP else
             '' if finality_on(checkout) else
             f'{p} closes round {last}, its loop\'s fourth on this head, which still brought a blocker or should fixed in a commit: the area keeps taking patches, '
             'so record the finality pass on the head first (mergeworthy:finality step 1, `pr-steps finality <the plan>`)', False),
    # a fresh reader runs once (admit): its findings are fixed and confirmed in the loops that own them, so its ledger asks no next round
    'fresh': ('fixed in <sha>', lambda rows, last, p, reached, ran, checkout: '', False),
    'post': ('fixed in r<N>', lambda rows, last, p, reached, ran, checkout: '' if last >= 2 else f'{p} closes round {last}: a verdict that is not clean gets round 2 first', True),
}


def finality_on(checkout):
    """Whether checkout's HEAD has a `pr-steps finality` record: in its pr-steps record file or its drift note."""
    h = git(checkout, 'rev-parse', 'HEAD').stdout.strip()
    return bool(h) and 'finality' in drift.steps(h, git(checkout, 'notes', f'--ref={records.DRIFT_REF}', 'show', h).stdout)


def wrote(report, checkout='.'):
    """(the loop a round of which on checkout's lineage wrote report, its round events there), else (None, [])."""
    report = os.path.realpath(report)
    return next(((l, evs) for l, evs in lineage(checkout).items() if any(report in e['outs'] for e in evs)), (None, []))


def reports_of(report, checkout='.'):
    """report and the reports of its loop's other rounds on checkout's lineage (lineage), leaving out a post's verdict (a fresh
    reader's body verdict), which its post loop's ledger closes."""
    import review_launch
    return sorted({os.path.realpath(report)} | {o for e in wrote(report, checkout)[1] for o in e['outs'] if not review_launch.draft_of(o)})


def unruled(rows, reports):
    """Each finding `R<round>.<n> <label>` of reports (a path, or (its name, its text, its seat)) that has no row among the ledger's
    rows with its id, the seat's first (`<seat>:R<round>.<n>`) where it has one, and label, a line each: what admit and close both refuse."""
    ruled, out = {r.id: r.label for r in rows}, []
    for rp in reports:
        name, text, seat = rp if isinstance(rp, tuple) else (rp, None, '')
        try: said = [r for r in ledger.rows(open(name, errors='replace').read() if text is None else text) if r.id]
        except OSError: continue
        key = lambda r: f'{seat}:{r.id}' if f'{seat}:{r.id}' in ruled else r.id
        out += [f"{name}: {r.line}  <- {'its ledger row says ' + ruled[key(r)] if key(r) in ruled else 'no ledger row'}: the ledger keeps the seat's id and label, its ruling the outcome"
                for r in said if ruled.get(key(r)) != r.label]
    return out


def close(path, kind='code', checkout='.', reports=(), loop=None):
    """What leaves the loop of the ledger at path open, [] when it closes: each finding of every round is the kind's fix (a code
    fix's sha in checkout's HEAD history, or, outside a post's own ledger, a draft whose gate-pass record holds its text),
    `declined: <why>` or `listed: <where>`, no blocker is listed or open, the completed round leaves the loop closed by the kind's
    rule (a code loop's counts the rounds loop ran on HEAD), every row's id (a word starting with a letter, with a digit) is
    R<round>.<n>, and each finding `R<round>.<n> <label>` the seat's reports hold has its row, with that label."""
    fix, still_open, confirms = KINDS[kind]
    try: rows, others, last = ledger.read(path)
    except OSError as e: return [f'{path}: {e.strerror}']
    misnamed = [f'{line}  <- its id is not R<round>.<n>' for line in others]
    unbound = unruled(rows, reports)
    if not rows: return misnamed + unbound + [f"{path} has no '<id> <label> <outcome>' lines (R<round>.<n> blocker|should|nit {fix}|declined: <why>|listed: <where>)"]
    reached = lambda sha: desc(checkout, sha, 'HEAD')
    # the rounds loop ran on HEAD, as admit counts them; the round number for a ledger whose loop isn't named
    ran = len(on_head(loop, last + 1, [checkout], [git(checkout, 'rev-parse', 'HEAD').stdout.strip()])) if loop else last
    out = misnamed + unbound + [w for w in [still_open(rows, last, path, reached, ran, checkout)] if w]
    for r in rows:
        body = not confirms and r.draft and os.path.join(os.path.dirname(path), r.draft)
        closed = confirms and r.confirmed and r.round < r.confirmed <= last or body and ledger.gated(body) or r.fixed and reached(r.fixed)
        if body and not closed:
            out.append(f'{r.line}  <- {r.draft} has no gate-pass record of its current text')
        elif r.fixed and not closed:
            out.append(f'{r.line}  <- {r.fixed} is not in HEAD\'s history')
        elif r.label == 'blocker' and not closed and not r.declined:
            out.append(f'{r.line}  <- an open blocker keeps the PR in draft')
        elif not closed and not (r.declined or r.listed):
            out.append(f'{r.line}  <- not {fix}, declined: <why> or listed: <where>')
    return out


if __name__ == '__main__' and sys.argv[1:2] == ['seats']:  # loops.py seats <report> <record file> <step>: open_seats, a line each; exits 1 for a report of a round off HEAD's lineage
    rp = os.path.realpath(sys.argv[2])
    repo = os.path.dirname(review_journal.change_of('.') or '/-/-')  # every branch's journal of this repo
    if any(rp in e['outs'] for f in glob.glob(os.path.join(repo, '*.jsonl')) for e in review_journal.events(f)) and not wrote(rp)[0]:
        sys.exit(f"{sys.argv[2]} is the report of a round pinned to a head that isn't in HEAD's history: review this head, then record its report (mergeworthy:delegate §Review rounds)")
    print(*open_seats(sys.argv[2], [l.split()[1] for l in open(sys.argv[3]) if len(l.split()) > 1] if os.path.isfile(sys.argv[3]) else [], sys.argv[4]), sep='\n')
elif __name__ == '__main__' and sys.argv[1:2] == ['round']:  # loops.py round <report>: the round of its loop on HEAD's lineage that wrote report, 0 for none
    rp = os.path.realpath(sys.argv[2])
    print(max([e['n'] for evs in lineage('.').values() for e in evs if rp in e['outs']], default=0))
elif __name__ == '__main__':  # loops.py close [--post|--fresh] <ledger> [<checkout>] [--report <the last round's report>]: exits 0 when the ledger closes its loop, else prints what stands
    a, rep = sys.argv[2:], None
    if '--report' in a: i = a.index('--report'); rep = a[i + 1]; del a[i:i + 2]
    kind = {'--post': 'post', '--fresh': 'fresh'}.get(a[0], 'code'); flag = kind != 'code'
    checkout = (a[flag + 1:flag + 2] or ['.'])[0]
    found = close(a[flag], kind=kind, checkout=checkout, reports=reports_of(rep, checkout) if rep else [], loop=rep and wrote(rep, checkout)[0])
    if found:
        print('the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found), file=sys.stderr)
    sys.exit(1 if found else 0)
