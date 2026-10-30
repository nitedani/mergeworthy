"""A watch dir's threads.txt, as every reader of it reads it: one thread per line, `owner/repo N` or `owner/repo#N` on GitHub,
`gitlab.com/<path> N` or `<path>#N` for a GitLab issue and `<path> !N` or `<path>!N` for a merge request; a # after whitespace or
at a line's start begins a comment. Lines are only read, never rewritten: hooks and gh-watch-start append to the file unlocked.
`threads_file.py <threads.txt> <repo> <number>` exits 0 when the file lists that thread (gh-watch-start's check)."""
import re, sys

GL = 'gitlab.com/'
LINE = re.compile(r'(?P<repo>[\w.-]+(?:/[\w.-]+)+?)(?:\s*(?P<sep>[#!])|\s+)(?P<num>\d+)(?:\s+#.*)?')


def parse(l):
    """-> (repo, number) with a merge request's number as `!N`; None for a blank or comment line; False for a bad one."""
    s = l.strip()
    if not s or s.startswith('#'):
        return None
    m, gl = LINE.fullmatch(s), s.startswith(GL)
    if not m or not gl and (m['repo'].count('/') != 1 or m['sep'] == '!') or gl and m['repo'].count('/') < 2:
        return False
    return m['repo'], ('!' if m['sep'] == '!' else '') + m['num']


def read(path):
    """-> ([(repo, number)] without repeats, [bad lines]) for threads.txt at path; none for a missing file."""
    threads, bad = {}, []
    try:
        text = open(path, errors='replace').read()
    except FileNotFoundError:
        text = ''
    for l in text.splitlines():
        t = parse(l)
        if t:
            threads[t] = None
        elif t is False:
            bad.append(l.strip())
    return list(threads), bad


def lists(path, repo, num):
    return (repo, str(num)) in read(path)[0]


if __name__ == '__main__':
    sys.exit(0 if lists(*sys.argv[1:4]) else 1)
