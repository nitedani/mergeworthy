"""Which changed files are tests, by path alone, for pr-steps small, pre-bash-guard's finality counter, the watcher's SHAPE STALE
and loc-breakdown: test directories (tests/, __tests__/, e2e/, specs/, unit_tests/), *.test.* and *.spec.*, a name starting with
test and then an uppercase letter, - or _ (pytest's test_*.py, a shared suite like testRun.ts, test-utils.ts; not testimonial.ts),
pytest's conftest.py, and *_test.* (Go, pytest). A POSIX ERE that Python's re reads the same: pr-steps matches it in mawk, which
has no \\w."""
TESTS = r'(^|/)(tests?|__tests__|e2e|specs?|[A-Za-z0-9_.-]*_tests?)/|\.(test|spec)\.|(^|/)\.test[A-Za-z-]*\.|(^|/)test[A-Z_-][^/]*$|(^|/)conftest\.py$|_test\.[A-Za-z]+$'

if __name__ == '__main__':
    print(TESTS)
