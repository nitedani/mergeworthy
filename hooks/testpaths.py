"""Which changed files are tests, by path alone, for pr-steps small, the drift count (drift.py), the watcher's SHAPE STALE
and loc-breakdown: test directories (tests/, __tests__/, e2e/, specs/, unit_tests/), *.test.* and *.spec.*, a name starting with
test and then an uppercase letter, - or _ (pytest's test_*.py, a shared suite like testRun.ts, test-utils.ts; not testimonial.ts),
pytest's conftest.py, and *_test.* (Go, pytest). A POSIX ERE that Python's re reads the same: pr-steps matches it in mawk, which
has no \\w."""
TESTS = r'(^|/)(tests?|__tests__|e2e|specs?|[A-Za-z0-9_.-]*_tests?)/|\.(test|spec)\.|(^|/)\.test[A-Za-z-]*\.|(^|/)test[A-Z_-][^/]*$|(^|/)conftest\.py$|_test\.[A-Za-z]+$'
# What is no code, for the finality counter and pr-steps small's line count: tests, docs, lockfiles and changesets
NOT_CODE = TESTS + r'|(^|/)docs?/|\.md$|lock\.(json|yaml)$|\.lock$|(^|/)\.changeset/'
# Build output: a dist/ path segment (a committed build bundle), plus what generated() finds marked in .gitattributes
GENERATED = r'(^|/)dist/'
# What a shape pass doesn't rate, and the changed lines past which the code it rated is new work: SHAPE STALE's count, and the round cap's
NOT_SHAPE = TESTS + r'|(^|/)(pnpm-lock\.yaml|package-lock\.json|yarn\.lock)$|' + GENERATED
STALE_LINES = 80

def generated(repo, paths):
    """The paths (from the top of checkout repo, as git diff prints them) that are build output: GENERATED, or
    `linguist-generated` (set or true) in its .gitattributes."""
    import re, subprocess  # here: the hooks that import this for TESTS alone don't pay for them
    git = lambda *a, **k: subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, **k).stdout
    a = git('-C', git('rev-parse', '--show-toplevel').strip() or '.', 'check-attr', '--stdin', '-z', 'linguist-generated',
        input='\0'.join(paths)).split('\0')  # path, attribute, value, ...
    return {p for p in paths if re.search(GENERATED, p)} | {p for p, v in zip(a[0::3], a[2::3]) if v in ('set', 'true')}

if __name__ == '__main__':  # no argument: TESTS; `not-code`: NOT_CODE; `generated`: those of the paths on stdin (a line each) in the checkout here
    import sys
    if sys.argv[1:] == ['generated']: print(*sorted(generated('.', sys.stdin.read().splitlines())), sep='\n')
    elif sys.argv[1:] == ['not-code']: print(NOT_CODE)
    else: print(TESTS)
