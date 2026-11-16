"""The step records pr-steps writes under ~/.claude/pr-steps and the hooks read: one file per commit (quick, the converge steps, gates,
union) and one per repo and branch (preflight, approach)."""
import hashlib, os, re, subprocess, sys
from shellcmd import folder

STORE = os.path.expanduser('~/.claude/pr-steps')


def commit_file(sha):
    """The record file of commit sha."""
    return os.path.join(STORE, sha)


def branch_record(d, kind, branch=None):
    """The pr-steps record kept once per repo and branch (preflight, approach; bin/pr-steps writes through it) of branch, by default the
    checked-out one; None outside git."""
    git = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout.strip()
    common = git('rev-parse', '--git-common-dir')
    if not common:
        return None
    root = os.path.realpath(os.path.join(d, common))
    rec = lambda b: os.path.join(STORE, f'{kind}.' + hashlib.sha256((root + '\n' + b).encode()).hexdigest()[:40])
    branch = branch or git('symbolic-ref', '--short', '-q', 'HEAD') or 'HEAD'
    # a worktree on its own local branch tracking the PR's branch, pushed (refs/remotes/<remote>/…) or local, shares that branch's records
    up = re.sub(r'^refs/(remotes/[^/]+|heads)/', '', git('for-each-ref', '--format=%(upstream)', f'refs/heads/{branch}'))
    return next((rec(b) for b in (branch, up) if b and os.path.exists(rec(b))), rec(branch))


def waits_for(path, kind):
    """Whether code in the repo and branch holding path waits for its kind of record (preflight, approach): not outside git, nor on a branch
    sharing no history with the remote's default branch, such as one holding a PR's screenshots, which holds no code of the product."""
    d = folder(path)
    rec = branch_record(d, kind)
    return bool(rec) and not os.path.exists(rec) and \
        subprocess.run(['git', '-C', d, 'merge-base', 'HEAD', 'refs/remotes/origin/HEAD'], capture_output=True).returncode != 1


def no_preflight(path):
    """Why code can't start yet in the repo and branch holding path for want of its preflight (pull-request step 2), or ''."""
    return waits_for(path, 'preflight') and ("no `pr-steps preflight` record for this repo and branch. Before any code, start the app, then run "
            "`pr-steps preflight <its URL> [Chrome flags]` (or `<PNG the session's browser MCP just took>`), "
            "or `pr-steps preflight 'none, because <why there is no UI or browser-run code>'`") or ''


def no_approach(path):
    """Why code can't start yet in the repo and branch holding path for want of its approach (pull-request step 5), or ''."""
    return waits_for(path, 'approach') and (
        "no `pr-steps approach` record for this repo and branch. Before any code, rate the approaches (mergeworthy:pull-request step 5), "
        "then `pr-steps approach <work folder>/approach.md`. A worktree on its own branch for a PR's work tracks that PR's branch "
        "(`git branch -u <its branch>`) and shares its record") or ''


if __name__ == '__main__':  # bin/pr-steps: the record path of the checked-out branch for kind sys.argv[1]
    print(branch_record(os.getcwd(), sys.argv[1]) or sys.exit(f'{os.getcwd()} is not in a git work tree'))
