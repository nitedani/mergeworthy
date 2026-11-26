"""Review loops (delegate §Review rounds): pre-agent-dedupe and pre-bash-guard ask admit() whether round `<loop>-r<N>` of a code
review may run, and record a round that ran with register(); pr-steps and gate-pass ask close() whether a loop's ledger closes it,
and pr-steps asks open_seats() whether a step's other reviewers closed. A round is refused once the heads its brief pins show the
branch hasn't moved since four earlier rounds of its loop, after an earlier one there when the ledger its brief names doesn't show
the last round brought a fixed blocker or should, and as a fresh reader's second."""
import glob, itertools, json, os, re, subprocess, sys
import agent_jobs, ledger, review_journal, testpaths

# {loop: {'rounds': [[n, the heads its brief pinned, the reports it wrote]], 'threads': the T3 threads or Claude agents its rounds ran in, 'outs': its reports, 'seated': a step's seat, 'step': the step pr-steps recorded it for}}
LOOPS = os.path.expanduser('~/.claude/review-loops.json')
# what a loop recorded before review-loops.json: rounds {loop: [[n, heads]]}, threads {loop: [thread]}
OLD = {'rounds': os.path.expanduser('~/.claude/review-rounds.json'), 'threads': os.path.expanduser('~/.claude/review-threads.json')}


def round_of(name):
    """A review round `<loop>-r<N>`, maybe followed by the date or head SHA a reused clientRequestId needs: the match, loop and N."""
    return re.fullmatch(r'(.+)-r(\d+)', re.sub(r'(-\d{4}-\d{2}-\d{2}|-[0-9a-f]{7,40})+$', '', name.strip()))


def _json(path):
    try: data = json.load(open(path))
    except (OSError, ValueError): return {}
    return data if isinstance(data, dict) else {}


def record(loop, loops=None):
    """loop's record in loops (default: review-loops.json), else what the files before it hold for loop."""
    r = (_json(LOOPS) if loops is None else loops).get(loop)
    if isinstance(r, dict): return r
    return {k: _json(path).get(loop, []) for k, path in OLD.items()}


def seat_loops(seat):
    """The loops whose rounds ran in the reviewer seat: {loop: its first round's journal event, or None for a round only
    review-loops.json or the files before it hold (a brief naming no checkout)}."""
    data, old = _json(LOOPS), _json(OLD['threads'])  # read once: a message to a thread that never reviewed waits on nothing
    here = {l: None for l in {*data, *old} if seat in (data[l].get('threads', []) if isinstance(data.get(l), dict) else old.get(l, []))}
    return {**here, **review_journal.seat_of(seat)}


def continues(loop, n, here):
    """Whether round n of loop continues one of the loops here (seat_loops) that ran in the seat it is sent to: a later round of
    one of them, or round 1 of `<slice>-reverify`, `-recheck` or `-fresh` of one's slice, or of `<loop>-ask<N>` of one (delegate §Review rounds)."""
    if n >= 2: return loop in here
    m = re.fullmatch(r'(.+)-(?:(reverify|recheck|fresh)|ask\d+)', loop)
    return bool(m) and any((l.rsplit('-', 1)[0] if m[2] else l) == m[1] for l in here)


CAP = 4  # rounds per loop on one head (delegate §Review rounds)
FANOUT = r'^Fan-out: converge §Running the agents$'  # a round 1 seating a step's reviewers at once (delegate §Reviewers)


def declared(brief):
    """(the step a round's brief declares by its line `Review: <step> [<part>]`, the seats its line `Seats: <seat>, …` does, the
    seat or loop its line `Fallback: <seat> failed …` names first, which it fills), each None without."""
    st, se = re.search(r'^[ \t>*-]*Review:[ \t]*(' + '|'.join(STEPS) + r')\b', brief, re.M), re.search(r'^[ \t>*-]*Seats:[ \t]*(.+)$', brief, re.M)
    fb = re.search(r'^[ \t>*-]*Fallback:[ \t]*([^\s<,:;]+)', brief, re.M)
    return st and st[1], se and [x for x in re.split(r'[\s,]+', se[1]) if x] or None, fb and fb[1]


def register(loop, n, heads, thread=None, post=False, outs=(), seated=False, checkouts=(), led=None, step=None, seats=None, fills=None, company=None):
    """Records round n of loop that ran: the thread it ran in, and, for a code review, the heads its brief pinned, the reports it
    writes (outs) and whether it is one of its step's seats (seated: its round 1 brief's FANOUT line), in review-loops.json and in
    the journal of each change its brief names (checkouts), with the ledger it names (led), the step its `Review:` line declares
    the seats its `Seats:` line does, the seat its `Fallback:` line fills and the company it ran on."""
    failed = []  # each record is written though the other's write failed, then the first failure is raised
    if not post:
        for c in dict.fromkeys(filter(None, map(review_journal.change_of, checkouts))):
            try: review_journal.append(c, {'ev': 'round', 'loop': loop, 'n': n, 'heads': heads, 'outs': sorted({os.path.realpath(o) for o in outs}), 'thread': thread, 'seated': seated, 'checkouts': list(checkouts), 'ledger': led, 'step': step, 'seats': seats, 'fills': fills, 'company': company})
            except OSError as e: failed.append(e)
    def ran(loops):
        r = loops[loop] = record(loop, loops)
        if thread and thread not in r['threads']: r['threads'].append(thread)
        if not post:
            r['rounds'].append([n, heads, sorted({os.path.realpath(o) for o in outs})])
            r['outs'] = sorted(set(r.get('outs', [])) | {os.path.realpath(o) for o in outs})
            r['seated'] = r.get('seated') or seated
    try:
        if thread or not post: agent_jobs.locked_update(LOOPS, ran)
    except OSError as e: failed.append(e)
    if failed: raise failed[0]


PENDING = os.path.expanduser('~/.claude/review-pending')  # a Bash command's admitted rounds and post launches, until it ended


def pend(key, rounds, launches):
    """Holds, for the Bash command key (own_actions.key), the register() arguments of the review rounds it runs and the draft sha
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
        for r in held['rounds']: register(*r)


STEPS = ('verify', 'reverify', 'shape', 'fresh', 'small', 'post', 'docs')  # what a loop checks (its brief's `Review: <step>`)


def lineage(checkout):
    """{loop: {'rounds': [[n, heads, outs]], 'first': its round 1's event}} of the loops in the journal of checkout's change whose
    rounds' pinned heads are all in its HEAD's history (rounds that pinned none left out)."""
    found = {}
    for e in review_journal.events(review_journal.change_of(checkout) or ''):
        if e['heads'] and all(desc(checkout, h, 'HEAD') for h in e['heads']):
            r = found.setdefault(e['loop'], {'rounds': [], 'first': e})
            r['rounds'].append([e['n'], e['heads'], e['outs']])
    return found


def same_company_seat(loop, tops):
    """Whether loop's round 1 on the lineage of one of the checkouts tops was a seat (its FANOUT line) on the main session's
    company, whose later rounds stay on it (delegate §Reviewers)."""
    return any((r := lineage(t).get(loop)) and r['first'].get('seated') and r['first'].get('company') == 'claudeAgent' for t in tops)


def step_of(loop, first):
    """The step a loop checks: its round 1's `Review: <step>`, else its name's `<step-or-slice>` (a slice's: verify)."""
    stem = loop.rsplit('-', 1)[0]
    return first.get('step') or (stem if stem in STEPS else 'verify')


def open_seats(report, recorded, step, checkout='.'):
    """The other seats of report's step on checkout's lineage, each still open: a loop whose round 1 seated it (its FANOUT line
    or `Seats:`) checking step, or one its round 1's `Seats: <seat>, …` declares that never ran, none of whose reports is in
    recorded (the outputs pr-steps recorded on the head), and no loop filling it (its round 1's `Fallback: <seat>`) closed.
    A step closes only once every seat's loop did."""
    report, on = os.path.realpath(report), lineage(checkout)
    mine = [l for l, r in on.items() if any(report in outs for _, _, outs in r['rounds'])]
    named = {f"{l.rsplit('-', 1)[0]}-{s}" for l in mine for s in on[l]['first'].get('seats') or ()}
    seats = {l for l, r in on.items() if (r['first'].get('seated') or r['first'].get('seats')) and step_of(l, r['first']) == step} | named
    stem = lambda l: l.rsplit('-', 1)[0]
    filled = {f if f.startswith(stem(l) + '-') else f"{stem(l)}-{f}": l for l, r in on.items() if (f := r['first'].get('fills'))}
    done = lambda l: l in mine or l in on and {o for _, _, outs in on[l]['rounds'] for o in outs} & set(recorded)
    return sorted(l for l in seats if not done(l) and not (l in filled and done(filled[l])))


git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
SHA = r'\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b'


def pinned(L):
    """(the checkouts launch L's brief names, their heads that its pinned SHAs equal)."""
    shas = set(re.findall(SHA, L.brief))
    return L.checkouts, sorted({h for t in L.checkouts if (h := git(t, 'rev-parse', 'HEAD').stdout.strip()) and any(h.startswith(x) for x in shas)})


def ledger_named(brief):
    """The ledger path a round's brief names, else None."""
    m = re.search(r'(/[^\s`\'"()]+\.ledger\.md)\b', brief)
    return m and m[1]


desc = lambda t, o, h: git(t, 'merge-base', '--is-ancestor', o, h).returncode == 0


def on_head(loop, n, tops, heads):
    """The rounds before n of loop that ran on heads (in the checkouts tops) or within STALE_LINES of the branch's own changed lines of them."""
    # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
    def own_lines(t, o, h):
        rows = re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M)
        gen = testpaths.generated(t, [p for _, _, p in rows])
        return testpaths.moved([r for r in rows if r[2] not in gen], 'cap')
    def built_on(old):
        # each new head built on the round's heads counts, so a pin that never moves can't stand for a branch that did
        if not old: return not heads
        moved = False
        for h in heads:
            if h in old: moved = True; continue
            on = ((t, o) for t in tops for o in old if desc(t, o, h))
            if (first := next(on, None)) is None: continue
            moved = True
            if not any(own_lines(t, o, h) <= testpaths.STALE_LINES for t, o in itertools.chain([first], on)): return False
        return moved
    return sorted({m for m, old, *_ in rounds_of(loop, tops) if m < n and built_on(old)})


def rounds_of(loop, tops):
    """loop's rounds the journals of the changes of the checkouts tops hold, else review-loops.json's (a round whose brief named
    no checkout, or one recorded before the journal)."""
    found = [x for c in dict.fromkeys(filter(None, map(review_journal.change_of, tops))) for x in review_journal.fold(c).get(loop, {}).get('rounds', [])]
    return found or record(loop)['rounds']


ROUTED = r'(.+)-(?:recheck|fresh)'  # a round routed to a seat's loop (converge steps 2 and 4), counted in its four


def third_seat(loop, tops, brief):
    """Why round 1 of loop, launched fresh, is refused: its step's round 1 on this lineage declared other seats (`Seats:`) and
    the brief neither says what failed (`Fallback:`) nor which loop it takes over (`Continues:`); '' otherwise."""
    stem, seat = loop.rsplit('-', 1) if '-' in loop else (loop, '')
    named = {s for t in tops for l, r in lineage(t).items() if l != loop and l.rsplit('-', 1)[0] == stem for s in r['first'].get('seats') or ()}
    if not named or seat in named or re.search(r'^[ \t>*-]*(Fallback|Continues):[ \t]*[^\s<]', brief, re.M): return ''
    return (f"{loop}-r1 would be a third seat of {stem}, whose round 1 declared {', '.join(sorted(named))}: continue a declared seat, "
            "or, when its launch failed, say so in a line `Fallback: <what failed>`; a seat taking over another's count names it, `Continues: <loop>` (mergeworthy:delegate §Review rounds).\n")


def admit(loop, n, tops, heads, led, owners=(), here=()):
    """Why round n of code review loop is refused, '' when it may run: tops are the checkouts its brief names, heads their heads
    its pins equal, led the ledger path it names (None), owners the loops whose rounds count in its four (a routed round's seat
    loop, the loop a `Continues:` line takes over), here the launcher's checkout, which holds the fixes of a brief naming none (a
    docs reader's, handed rendered pages)."""
    if re.fullmatch(r'fresh(-[^-]+)?', loop) and n >= 2:
        return f"{loop}-r{n}: the fresh reader runs once (mergeworthy:converge step 4); its findings go back to the loops that own them, `<slice>-fresh` (mergeworthy:delegate §Review rounds).\n"
    earlier = on_head(loop, n, tops, heads)
    shared = [f"{o} r{m}" for o in owners for m in on_head(o, 10 ** 9, tops, heads)]
    if shared and len(earlier) + len(shared) >= CAP:
        return (f"{loop}-r{n} counts in the four rounds per head of {', '.join(owners)}, which already ran {', '.join(shared)}"
                + (f" and {loop} {', '.join(f'r{m}' for m in earlier)}" if earlier else '')
                + f" on this head or one within {testpaths.STALE_LINES} changed lines of it: a recheck or a fresh reader's findings go to their seat's loop "
                "within its four (mergeworthy:delegate §Review rounds). List what is still open in the report or the PR body's notes and go on.\n")
    if not earlier: return 
    try: rows, _, last = ledger.read(led) if led and os.path.isfile(led) else ([], [], 0)
    except OSError as e: return f"the ledger {led} can't be read ({e.strerror}), so no round of {loop} is admitted: fix it, or name the loop's ledger (mergeworthy:delegate §Review rounds).\n"
    kept = ledger.owed(rows, last, lambda sha: any(desc(t, sha, 'HEAD') for t in tops or here))
    close = f"Close the loop with `pr-steps <step> <file> --ledger {led or '<ledger>'}` on r{earlier[-1]}'s report when it isn't clean: the agent's own report is the record, never one the main session writes.\n" if earlier else ''
    if len(earlier) >= CAP:
        return (f"{loop} already ran {', '.join(f'r{m}' for m in earlier)} on this head or one within {testpaths.STALE_LINES} changed lines of it "
                f"({', '.join(h[:12] for h in heads) or 'no head pinned'}): a loop gets four rounds per head, and a head past those lines is a new one "
                "(mergeworthy:delegate §Review rounds). "
                + (f"The ledger {led} shows round {last} still brought a blocker or should fixed in a commit: the area keeps taking patches, so its next step is "
                   "the finality pass (mergeworthy:finality step 1, recorded by `pr-steps finality <file>`), not another round. " if kept else "")
                + "List what is still open in the report or the PR body's notes and go on (push, ready, the next step) without waiting for an answer; "
                "only an open blocker keeps the PR in draft. A maintainer's ask on a new head starts a new loop name. " + close)
    if earlier and led and os.path.isfile(led) and last < earlier[-1]:
        return (f"{loop}-r{n} follows r{earlier[-1]}, but the ledger {led} shows round {last} as its last: rule r{earlier[-1]}'s findings in it first "
                f"(each `R{earlier[-1]}.<n> <label> <outcome>`, then `Round: {earlier[-1]}`), then send the round (mergeworthy:delegate §Review rounds).\n")
    import review_launch
    said = [o for m, _, outs in rounds_of(loop, tops) if m in earlier for o in outs if not review_launch.draft_of(o)]
    if led and os.path.isfile(led) and (missing := unruled(rows, said)):
        return (f"{loop}-r{n} follows r{earlier[-1]}, but the ledger {led} doesn't rule every finding of its loop's reports:\n" + '\n'.join(missing)
                + "\nRule each (`R<round>.<n> <label> <outcome>`), then send the round (mergeworthy:delegate §Review rounds).\n")
    if earlier and not kept:
        return (f"{loop}-r{n} follows r{earlier[-1]} on this head or one within {testpaths.STALE_LINES} changed lines of it, and a loop gets its next round only "
                "while its last round brought a blocker or should you kept and fixed (mergeworthy:delegate §Review rounds), but "
                + ("the brief names no `<work folder>/drafts/<review>.ledger.md` to show it: name the loop's ledger in the brief, or end the loop. " if not led else
                   f"{led} doesn't exist: name the loop's ledger, or end the loop. " if not os.path.isfile(led) else
                   f"the ledger {led} shows round {last} brought none `fixed in <sha>`: the loop ends there. ")
                + close)
    return ''


# per kind of loop: the fix outcome that closes a finding, why the completed round leaves the loop open ('' when it doesn't), and
# whether a later round confirming the fix closes it (a post's draft has no sha)
KINDS = {
    'code': ('fixed in <sha>', lambda rows, last, p, reached, ran: '' if ran >= CAP or not ledger.owed(rows, last, reached) else
             f'{p} closes round {last}, which brought a blocker or should fixed in a commit: the loop gets its next round first', False),
    # a fresh reader runs once (admit): its findings are fixed and confirmed in the loops that own them, so its ledger asks no next round
    'fresh': ('fixed in <sha>', lambda rows, last, p, reached, ran: '', False),
    'post': ('fixed in r<N>', lambda rows, last, p, reached, ran: '' if last >= 2 else f'{p} closes round {last}: a verdict that is not clean gets round 2 first', True),
}


def reports_of(report, checkout='.'):
    """report and the reports of its loop's other rounds on checkout's lineage (lineage), leaving out a post's verdict (a fresh
    reader's body verdict), which its post loop's ledger closes."""
    import review_launch
    report = os.path.realpath(report)
    rounds = next((r['rounds'] for r in lineage(checkout).values() if any(report in outs for _, _, outs in r['rounds'])), [])
    return sorted({report} | {o for _, _, outs in rounds for o in outs if not review_launch.draft_of(o)})


def loop_of(report, checkout='.'):
    """The loop a round of which on checkout's lineage wrote report, else None."""
    report = os.path.realpath(report)
    return next((l for l, r in lineage(checkout).items() if any(report in outs for _, _, outs in r['rounds'])), None)


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
    out = misnamed + unbound + [w for w in [still_open(rows, last, path, reached, ran)] if w]
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
    if any(rp in e['outs'] for f in glob.glob(os.path.join(repo, '*.jsonl')) for e in review_journal.events(f)) and not loop_of(rp):
        sys.exit(f"{sys.argv[2]} is the report of a round pinned to a head that isn't in HEAD's history: review this head, then record its report (mergeworthy:delegate §Review rounds)")
    print(*open_seats(sys.argv[2], [l.split()[1] for l in open(sys.argv[3]) if len(l.split()) > 1] if os.path.isfile(sys.argv[3]) else [], sys.argv[4]), sep='\n')
elif __name__ == '__main__':  # loops.py close [--post|--fresh] <ledger> [<checkout>] [--report <the last round's report>]: exits 0 when the ledger closes its loop, else prints what stands
    a, rep = sys.argv[2:], None
    if '--report' in a: i = a.index('--report'); rep = a[i + 1]; del a[i:i + 2]
    kind = {'--post': 'post', '--fresh': 'fresh'}.get(a[0], 'code'); flag = kind != 'code'
    checkout = (a[flag + 1:flag + 2] or ['.'])[0]
    found = close(a[flag], kind=kind, checkout=checkout, reports=reports_of(rep, checkout) if rep else [], loop=rep and loop_of(rep, checkout))
    if found:
        print('the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found), file=sys.stderr)
    sys.exit(1 if found else 0)
