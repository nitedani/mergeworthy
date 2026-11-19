"""The text a post's reviewer was handed. The hooks that start a reviewer (pre-agent-dedupe, pre-bash-guard) call launch() on its
output; gate-pass calls reviewed(), so a verdict counts only for the draft's text at that launch, whatever the files' times say."""
import hashlib, os, re, time

FOOTER = 'Harness changes since my last note: '  # the line gate-pass appends after the review: '\n' + FOOTER + '<compare link>\n'


def unfooted(data):
    """The bytes of a draft without the footer line gate-pass appended to it, which no reviewer reads."""
    return re.sub(rb'\n' + re.escape(FOOTER.encode()) + rb'<\S+>\n\Z', b'', data)


def draft_of(out):
    """The draft a review output is named after: <name>.md for <name>.review.out and <name>.review-r<N>.out; None for any other name."""
    return m[1] + '.md' if (m := re.fullmatch(r'(.+)\.review(-r\d+)?\.out', out)) else None


def launch(out):
    """Records that a reviewer starts on out's draft: refuses (returns why) unless the draft passed post-lint in its current text, moves
    a verdict an earlier launch left in out to <out>.prev, and writes <out>.launch as `<sha256 of the draft without its footer> <epoch>`.
    '' when out names no draft that exists, or the launch is recorded."""
    draft = draft_of(out)
    if not draft or not os.path.isfile(draft):
        return ''
    data = open(draft, 'rb').read()
    try: lint = open(draft + '.lint.sha').read().strip()
    except OSError: lint = ''
    if lint != hashlib.sha256(data).hexdigest():
        return f"{draft} has no passing post-lint for its current text: run post-lint first, then the review."
    if os.path.exists(out):
        os.replace(out, out + '.prev')
    with open(out + '.launch', 'w') as f:
        f.write(f'{hashlib.sha256(unfooted(data)).hexdigest()} {int(time.time())}\n')
    return ''


def reviewed(out, draft):
    """Why a gate refuses out's verdict for draft: no launch recorded, or another text launched; '' when the reviewer was handed
    draft's text, footer aside."""
    try: sha = open(out + '.launch').read().split()[0]
    except (OSError, IndexError):
        return (f"{out} has no recorded review launch: start the reviewer through delegate_task, the Agent tool, `codex exec -o {out}` "
                f"or `claude -p … > {out}`, which records the text it is handed (post step 3)")
    if sha != hashlib.sha256(unfooted(open(draft, 'rb').read())).hexdigest():
        return (f"the draft changed after its review {out} was launched: lint it again (post step 2), then send it back to the reviewer "
                "(post step 3)")
    return ''
