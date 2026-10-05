#!/usr/bin/env python3
"""Which comments the watcher reports and owes a reply for (1.5): a maintainer's on a thread the agent opened, and the
user's with /ai or /agent anywhere; nothing else. Run: python3 tests/test_watcher.py (exit 0 = all pass)."""
import importlib.util, os, sys
os.environ['GH_WATCH_ME'] = 'me'
spec = importlib.util.spec_from_file_location('gh_watch', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'watcher', 'gh-watch.py'))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
gated = frozenset({w._norm('/ai posted by the agent itself')})
def u(login, assoc='NONE', type='User'): return {'login': login, 'assoc': assoc, 'type': type}
cases = [
    ('maintainer (member)', u('maint', 'MEMBER'), 'Can you rename this?', True),
    ('maintainer (owner)', u('maint', 'OWNER'), 'LGTM', True),
    ('collaborator', u('maint', 'COLLABORATOR'), 'nit', True),
    ('contributor', u('someone', 'CONTRIBUTOR'), 'Any update?', False),
    ('stranger', u('someone'), '/ai fix it', False),
    ('bot', u('ci[bot]', 'NONE', 'Bot'), 'build failed', False),
    ('you, no call', u('me', 'OWNER'), 'I think this is fine', False),
    ('you, /ai', u('me', 'OWNER'), '/ai why does this fail?', True),
    ('you, /agent mid-text', u('me'), 'hmm\n/agent take a look', True),
    ('you, /aiden', u('me'), 'ask /aiden', False),
    ('you, path', u('me'), 'see src/ai/index.ts', False),
    ('agent post quoting /ai', u('me'), '/ai posted by the agent itself', False),
]
fails = [n for n, user, body, want in cases if w.answerable(user, body, gated) != want]
for n in fails: print('FAIL', n)
print(f'{len(cases) - len(fails)}/{len(cases)} passed'); sys.exit(1 if fails else 0)
