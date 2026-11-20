"""The text a post's reviewer was handed. The hooks that start a reviewer (pre-agent-dedupe, pre-bash-guard) check unlinted() on its
output while they admit the launch, and call launch() once the launching hook admitted it; gate-pass calls reviewed(), so a verdict counts only
for the draft's text at that launch, whatever the files' times say. The record is a workflow check of what those hooks see, not proof
of who wrote it."""
import datetime, hashlib, os, re, time
import ledger

# the line gate-pass appends to a draft after its review, in gate-pass's own format
FOOTER = re.compile(rb'\nHarness changes since my last note: <https://github\.com/nitedani/mergeworthy/compare/[0-9a-f]+\.\.\.[0-9a-f]+>\n\Z')


REVIEW_OUT = re.compile(r'(.+)\.review(-r\d+)?\.out')  # a review output's name: <name>.review.out, round N <name>.review-r<N>.out


def in_drafts(path):
    """Whether path's real path lies in a drafts/ folder, where a post's drafts live (post step 1)."""
    return '/drafts/' in os.path.realpath(path)


def draft_of(out):
    """The draft a post's review output is named after: <name>.md for <name>.review.out and <name>.review-r<N>.out in a drafts/
    folder; None for any other name or place."""
    return m[1] + '.md' if (m := REVIEW_OUT.fullmatch(out)) and in_drafts(out) else None


def misnamed(out):
    """Why a reviewer's output out can't be tied to its draft: a .out file whose real path is in a drafts/ folder, not named
    <name>.review.out; '' otherwise."""
    if draft_of(out) or not in_drafts(out) or not out.endswith('.out'):
        return ''
    return (f"{out} is in drafts/ but not named after its draft, so gate-pass can't tell which text its reviewer was handed: "
            "name it <name>.review.out (round N: <name>.review-rN.out) for <name>.md, then launch the review (post step 3)")


def unlinted(out):
    """Why a reviewer can't start on out's draft: it has no passing post-lint for its current text; '' when it has, or out names no
    draft that exists."""
    draft = draft_of(out)
    if not draft or not os.path.isfile(draft):
        return ''
    try: lint = open(draft + '.lint.sha').read().strip()
    except OSError: lint = ''
    if lint != hashlib.sha256(open(draft, 'rb').read()).hexdigest():
        return f"{draft} has no passing post-lint for its current text: run post-lint first, then the review."
    return ''


def launch(out):
    """Records, once the launching hook admitted it (unlinted(out) passed), that a reviewer starts on out's draft: moves a verdict
    an earlier launch left in out to <out>.prev, and writes <out>.launch as `<sha256 of the draft> <epoch>`.
    Nothing when out names no draft that exists."""
    draft = draft_of(out)
    if not draft or not os.path.isfile(draft):
        return
    sha = hashlib.sha256(open(draft, 'rb').read()).hexdigest()
    if os.path.exists(out):
        os.replace(out, out + '.prev')
    with open(out + '.launch', 'w') as f:
        f.write(f'{sha} {int(time.time())}\n')


def reviewed(out, draft):
    """(why, epoch): why a gate refuses out's verdict for draft (no valid launch record, or another text launched; '' when its reviewer
    was handed draft's bytes, or them before one FOOTER line), and the epoch of that launch (None without a valid record)."""
    try: m = re.fullmatch(r'([0-9a-f]{64}) (\d+)\n?', open(out + '.launch').read())
    except OSError: m = None
    if not m:
        return misnamed(out) or (
            f"{out} is not in a drafts/ folder, and only a post's review there records its launch: keep the draft and its review "
            "output in <work folder>/drafts/<thread>/ (post step 1), then launch the review (post step 3)" if not in_drafts(out) else
            f"{out} has no recorded review launch: start the reviewer through delegate_task, the Agent tool, `codex exec -o {out}` "
            f"or `claude -p … > {out}`, which records the text it is handed (post step 3)"), None
    data = open(draft, 'rb').read()
    if m[1] not in {hashlib.sha256(x).hexdigest() for x in (data, FOOTER.sub(b'', data))}:
        return (f"the draft changed after its review {out} was launched: lint it again (post step 2), then send it back to the reviewer "
                "(post step 3)"), int(m[2])
    return '', int(m[2])


def answers(out, draft, ledger_file=None):
    """(why, epoch): why the review in out doesn't let draft be posted, gate-pass's review rule ('' when it does), with its launch's epoch.
    The reviewer was handed draft's text (reviewed()); its verdict is exactly CLEAN, or ledger_file closes the round (ledger.problems, a post's
    rules); the launch postdates the latest human comment thread-context.md beside draft records. out None: a status post, which has no
    review and is checked by draft's own time. Writes nothing."""
    why, at = reviewed(out, draft) if out else ('', int(os.path.getmtime(draft)))
    if why: return f'{draft}: {why}', at
    try: verdict = [l.strip() for l in open(out, errors='replace').read().splitlines() if l.strip()] if out else ['CLEAN']
    except OSError: verdict = []  # its reviewer hasn't written yet
    if verdict != ['CLEAN']:
        found = ledger.problems(ledger_file, post=True) if ledger_file else []
        if not ledger_file or found:
            return ((f'the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found) + '\n' if found else '')
                    + f"review is not exactly CLEAN (it has {len(verdict)} non-empty lines; last: {verdict[-1] if verdict else ''}). The reviewer's "
                    "final message, alone, is the review output; after round 2, pass --ledger <the loop's ledger>"), at
    try: tc = open(os.path.join(os.path.dirname(os.path.realpath(draft)), 'thread-context.md')).read()
    except OSError: tc = ''
    if (m := re.search(r'^- latest-human-comment: id=\d* at=([0-9TZ:-]+)', tc, re.M)):
        try: human = int(datetime.datetime.fromisoformat(m[1].replace('Z', '+00:00')).timestamp())
        except ValueError: human = 0
        if human >= at:
            return (f'thread-context.md records a human comment ({m[1]}) newer than the review: re-read it, revise the draft if it changes '
                    'anything, and review again (mergeworthy:post step 1)'), at
    return '', at
