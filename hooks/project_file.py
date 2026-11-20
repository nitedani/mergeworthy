"""The project file's word cap (task §Project file): every agent reads it whole, so it holds only what one can read every time;
its quotes and data stay in the uncapped study. bin/project-learn's `mark` and pre-agent-dedupe refuse a file over it."""
import os

CAP = 2500  # user decision 2026-10-31: 2500 words
# the project files; another folder through the environment, for a trial run on copies (a relative one is from where it starts)
PROJECTS = os.path.abspath(os.environ.get('MERGEWORTHY_PROJECTS') or os.path.expanduser('~/.mergeworthy/projects'))


def words(path):
    """The file's words, as `wc -w` counts them."""
    with open(path, errors='replace') as f:
        return len(f.read().split())
