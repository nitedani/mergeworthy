"""The text a post's reviewer was handed. The hooks that start a reviewer (pre-agent-dedupe, pre-bash-guard) check unlinted() on its
output while they admit the launch, and call launch() once nothing refused it; gate-pass calls reviewed(), so a verdict counts only
for the draft's text at that launch, whatever the files' times say."""
import hashlib, os, re, time

FOOTER = 'Harness changes since my last note: '  # the line gate-pass appends after the review: '\n' + FOOTER + '<compare link>\n'


def unfooted(data):
    """The bytes of a draft without the footer line gate-pass appended to it, which no reviewer reads."""
    return re.sub(rb'\n' + re.escape(FOOTER.encode()) + rb'<\S+>\n\Z', b'', data)


def draft_of(out):
    """The draft a review output is named after: <name>.md for <name>.review.out and <name>.review-r<N>.out; None for any other name."""
    return m[1] + '.md' if (m := re.fullmatch(r'(.+)\.review(-r\d+)?\.out', out)) else None


def misnamed(out):
    """Why a reviewer's output out can't be tied to its draft: a .out file in a drafts/ folder not named <name>.review.out; '' otherwise."""
    if draft_of(out) or not re.search(r'/drafts/.*\.out\Z', out):
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
    """Records that a reviewer the hook admitted (unlinted(out) passed, and nothing else refused it) starts on out's draft: moves a
    verdict an earlier launch left in out to <out>.prev, and writes <out>.launch as `<sha256 of the draft without its footer> <epoch>`.
    Nothing when out names no draft that exists."""
    draft = draft_of(out)
    if not draft or not os.path.isfile(draft):
        return
    sha = hashlib.sha256(unfooted(open(draft, 'rb').read())).hexdigest()
    if os.path.exists(out):
        os.replace(out, out + '.prev')
    with open(out + '.launch', 'w') as f:
        f.write(f'{sha} {int(time.time())}\n')


def reviewed(out, draft):
    """(why, epoch): why a gate refuses out's verdict for draft (no valid launch record, or another text launched; '' when its reviewer
    was handed draft's text, footer aside), and the epoch of that launch (None without a valid record)."""
    try: m = re.fullmatch(r'([0-9a-f]{64}) (\d+)\n?', open(out + '.launch').read())
    except OSError: m = None
    if not m:
        return (misnamed(out) or f"{out} has no recorded review launch: start the reviewer through delegate_task, the Agent tool, "
                f"`codex exec -o {out}` or `claude -p … > {out}`, which records the text it is handed (post step 3)"), None
    if m[1] != hashlib.sha256(unfooted(open(draft, 'rb').read())).hexdigest():
        return (f"the draft changed after its review {out} was launched: lint it again (post step 2), then send it back to the reviewer "
                "(post step 3)"), int(m[2])
    return '', int(m[2])
