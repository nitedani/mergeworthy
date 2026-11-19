"""The text a post's reviewer was handed. The hooks that start a reviewer (pre-agent-dedupe, pre-bash-guard) call launch() on its
output; gate-pass calls reviewed(), so a verdict counts only for the draft's text at that launch, whatever the files' times say."""
import hashlib, os, re, time


def draft_of(out):
    """The draft a review output is named after: <name>.md for <name>.review.out and <name>.review-r<N>.out; None for any other name."""
    return m[1] + '.md' if (m := re.fullmatch(r'(.+)\.review(-r\d+)?\.out', out)) else None


def launch(out):
    """Records that a reviewer starts on out's draft: refuses (returns why) unless the draft passed post-lint in its current text, moves
    a verdict an earlier launch left in out to <out>.prev, and writes <out>.launch as `<sha256 of the draft> <epoch>`. '' when out
    names no draft that exists, or the launch is recorded."""
    draft = draft_of(out)
    if not draft or not os.path.isfile(draft):
        return ''
    sha = hashlib.sha256(open(draft, 'rb').read()).hexdigest()
    try: lint = open(draft + '.lint.sha').read().strip()
    except OSError: lint = ''
    if lint != sha:
        return f"{draft} has no passing post-lint for its current text: run post-lint first, then the review."
    if os.path.exists(out):
        os.replace(out, out + '.prev')
    with open(out + '.launch', 'w') as f:
        f.write(f'{sha} {int(time.time())}\n')
    return ''


def reviewed(out, text):
    """Why a gate refuses out's verdict for a draft whose bytes are text: no launch recorded, or another text launched; '' when the
    reviewer was handed text."""
    try: sha = open(out + '.launch').read().split()[0]
    except (OSError, IndexError):
        return (f"{out} has no recorded review launch: start the reviewer through delegate_task, the Agent tool, `codex exec -o {out}` "
                f"or `claude -p … > {out}`, which records the text it is handed (post step 3)")
    if sha != hashlib.sha256(text).hexdigest():
        return (f"the draft changed after its review {out} was launched: lint it again (post step 2), then send it back to the reviewer "
                "(post step 3)")
    return ''
