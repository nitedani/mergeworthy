"""The project file's word cap (task §Project file): every agent reads it whole, so it holds only what one can read every time;
its quotes and data stay in the uncapped study. bin/project-learn's `mark` and pre-agent-dedupe refuse a file over it."""
import os, re

CAP = 2500  # user decision 2026-10-31: 2500 words
# the project files, and the learning run's folder with its runs.txt (one line per daily run, bin/project-learn start); another
# folder for each through the environment, for a trial run on copies (a relative one is from where the run starts)
PROJECTS = os.path.abspath(os.environ.get('MERGEWORTHY_PROJECTS') or os.path.expanduser('~/.mergeworthy/projects'))
RUNS = os.path.join(os.path.abspath(os.environ.get('MERGEWORTHY_LEARN_DIR') or os.path.expanduser('~/.mergeworthy/work/project-learn')), 'runs.txt')


def words(path):
    """The file's words, as `wc -w` counts them."""
    with open(path, errors='replace') as f:
        return len(f.read().split())


def _runs():
    try:
        return open(RUNS, errors='replace').read().splitlines()
    except OSError:
        return []


def record_run(at, thread=None, repos=(), failed=(), error=None):
    """Appends a learning run to RUNS and returns its line after the date and time: `FAILED: <error>` when its thread couldn't
    start, else `thread <id>` (or `no thread: nothing to sort`), `; <n> to sort: <repos>`, and `; FAILED: <repo (why)>; …`."""
    line = f"FAILED: {error}" if error else ((f"thread {thread}" if thread else 'no thread: nothing to sort') + f"; {len(repos)} to sort"
                                            + (f": {' '.join(repos)}" if repos else '') + (f"; FAILED: {'; '.join(failed)}" if failed else ''))
    with open(RUNS, 'a') as f:
        f.write(f"{at[:10]} {at} {line}\n")
    return line


def ran_today(today):
    """A run today other than one whose thread couldn't start, which the next start retries."""
    return any(l.startswith(today) and not re.match(r'\S+ \S+ FAILED: ', l) for l in _runs())


def learning_thread(repo):
    """(thread id, start time) of the newest learning run whose thread sorts the repo, else None."""
    for l in reversed(_runs()):
        m = re.match(r'\S+ (\S+) thread (\S+); \d+ to sort: ([^;]*)', l)
        if m and repo in m[3].split():
            return m[2], m[1]
    return None
