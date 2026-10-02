#!/usr/bin/env python3
"""Tests for mechanisms/post-lint.py. Run: python3 test_post_lint.py (exit 0 = all pass).
Fixtures are written under ./post-lint-cases/ (never /tmp). Cases marked (real) are replies posted to a maintainer."""
import os, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, '..', 'mechanisms', 'post-lint.py')
CASES = os.path.join(HERE, 'post-lint-cases')
shutil.rmtree(CASES, ignore_errors=True); os.makedirs(CASES)

HOW_ABOUT = "How about we remove this line? Docs shouldn't be bloated with very seldom edge cases?"
SUGGESTION = "How about more future proof:\n```suggestion\nThe content of a non-HTML page.\n```\n"

BADGE = '<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**'

# `gh api user --jq .type` for METHODOLOGY_BADGE=auto prints $FAKE_GH_TYPE
FAKE_BIN = os.path.join(CASES, 'bin'); os.makedirs(FAKE_BIN)
open(os.path.join(FAKE_BIN, 'gh'), 'w').write('#!/bin/sh\necho "$FAKE_GH_TYPE"\n'); os.chmod(os.path.join(FAKE_BIN, 'gh'), 0o755)

def run(name, draft, parent=None, extra=(), env=None):
    d = os.path.join(CASES, name + '.md')
    # every agent post starts with the badge; 'no-badge' cases test its absence
    if 'tracker' not in extra and not name.startswith(('no-badge', 'badge-')):
        draft = BADGE + ' ' + draft
    open(d, 'w').write(draft)
    if parent is not None:
        open(os.path.join(CASES, name + '.parent.md'), 'w').write(parent)
    base = {k: v for k, v in os.environ.items() if not k.startswith('METHODOLOGY_')}
    base['PATH'] = FAKE_BIN + os.pathsep + base['PATH']
    r = subprocess.run([sys.executable, LINT, d, *extra], capture_output=True, text=True, env={**base, **(env or {})})
    return r.returncode, r.stdout + r.stderr

# (name, draft, parent, extra args, expected substring or None for a clean pass[, env])
T = [
    ('no-badge', 'Done in abc1234.\n', None, ('--parent', 'none'), 'missing badge'),
    # bare Done to a question-shaped comment (real)
    ('bare-done-question', 'Done in 25f2aa02e6 (also removed from `llms.txt`).\n', HOW_ABOUT, (), "bare 'Done'"),
    # (real, answering "Also fairly obvious, I think we can remove this line")
    ('bare-done-ithink', 'Done in d113b5eeff (also in `llms.txt`).\n', 'Also fairly obvious, I think we can remove this line', (), "bare 'Done'"),
    # the same "Done" to a suggestion block or a plain instruction is fine
    ('done-suggestion', 'Done in b7d65f13ed.\n', SUGGESTION, (), None),
    ('done-instruction', 'Done in 74f1ea0d76.\n', "Let's define a function e.g. setHeadersWithMultipleCookies", (), None),
    # a reply that says what was checked passes
    ('checked', 'Removed the paragraph above instead, in b4c4ebd6ed: "seldom edge cases" fits it, while the `Content-Type` line is needed by every non-HTML page.\n', HOW_ABOUT, (), None),
    # parent passed explicitly
    ('explicit-parent', 'Done in abc1234.\n', None, ('--parent', os.path.join(CASES, 'bare-done-question.parent.md')), "bare 'Done'"),
    # a reply needs its parent, unless it answers nobody
    ('no-parent', 'Done in abc1234.\n', None, (), 'no parent'),
    ('parent-none', 'Ready for review: CI is green on abc1234.\n', None, ('--parent', 'none'), None),
    # process machinery (real)
    ('process', '**Review round:** a fresh-context Claude Opus subagent. Codex (`gpt-6-astra`) failed with "Your workspace is out of credits".\n', None, ('--parent', 'none'), 'process in the thread'),
    ('process-rating', 'Every function is rated 8/10 or higher now.\n', None, ('--parent', 'none', '--kind', 'pr'), 'process in the thread'),
    ('commit-review-table', '\n\n| Commit | What it does, and the idea behind it | Rating |\n| --- | --- | --- |\n| abc1234 rename | Names it after what it returns. | 9/10 (a short reason) |\n', None, ('--parent', 'none'), None),
    ('process-tracker-ok', '- Review round 2 done\n', None, ('--kind', 'tracker'), None),
    # a question handed back without a recommendation (real)
    ('ask-no-rec', 'Unlisted options go into `build`. Do you mean they should go to the config root instead?\n', 'As a user I would rather see an error.', (), 'question without your recommendation'),
    ('ask-with-rec', 'Unlisted options go into `build`, where Vite puts them too. I recommend keeping that; OK?\n', 'As a user I would rather see an error.', (), None),
    # quoted questions of the other person don't count
    ('quoted-q', '> Why test/abort/ ?\n\nNo reason; moved to `test/playground/` in 9ee67b5112.\n', 'Why test/abort/ ? How about test/playground/ instead?', (), None),
    # meta-promises and thanks for approvals
    ('understood', 'Understood: I will look closer next time.\n', None, ('--parent', 'none'), 'banned phrase'),
    ('thanks-lgtm', 'Thanks for the LGTM; opening the PR next.\n', None, ('--parent', 'none'), 'banned phrase'),
    # existing checks still work
    ('emdash', 'Fixed in abc1234 — the header is sent.\n', 'Let\'s fix it', (), 'em dash'),
    ('too-long', ' '.join(['word'] * 81) + '\n', 'Let\'s fix it', (), 'words > 80'),
    # METHODOLOGY_BADGE: off never needs the badge; auto needs it only for a human account
    ('badge-off', 'Done in abc1234.\n', None, ('--parent', 'none'), None, {'METHODOLOGY_BADGE': 'off'}),
    ('badge-auto-bot', 'Done in abc1234.\n', None, ('--parent', 'none'), None, {'METHODOLOGY_BADGE': 'auto', 'FAKE_GH_TYPE': 'Bot'}),
    ('badge-auto-user', 'Done in abc1234.\n', None, ('--parent', 'none'), 'missing badge', {'METHODOLOGY_BADGE': 'auto', 'FAKE_GH_TYPE': 'User'}),
    # METHODOLOGY_REVIEW_TRACE: a review record may carry the process only when it goes in a PR comment
    ('review-record', 'Review round 1: the charter found 2 issues, both fixed in abc1234.\n', None, ('--kind', 'review-record'), None, {'METHODOLOGY_REVIEW_TRACE': 'comment'}),
    ('review-record-hidden', 'Review round 1: clean.\n', None, ('--kind', 'review-record'), 'stay in the artifact root'),
]

fails = 0
for name, draft, parent, extra, want, *env in T:
    code, out = run(name, draft, parent, extra, *env)
    ok = (code == 0 and not out) if want is None else (code == 1 and want in out)
    if not ok:
        fails += 1
        print(f"FAIL {name}: exit {code}, expected {'clean' if want is None else repr(want)}\n{out}")
print(f"{len(T) - fails}/{len(T)} passed")
sys.exit(1 if fails else 0)
