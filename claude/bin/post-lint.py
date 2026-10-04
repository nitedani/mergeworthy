#!/usr/bin/env python3
"""post-lint <draft.md> [--kind reply|pr|issue|inline|tracker|proposal|review-record] [--parent <file>|none]: checks a draft before it is posted to GitHub.
Exit 1 with one line per finding. Checks: banned phrases, "stacked on" without gh stack, bare #N refs
(must be owner/repo#N unless --repo matches), length budgets, unclassified maintainer notes, em dashes,
process machinery in the thread, questions without a recommendation, and a bare "Done" answering a question.
A reply or inline comment needs the comment it answers: <draft stem>.parent.md next to it, or --parent <file>;
--parent none for a comment that answers nobody.
Settings: METHODOLOGY_BADGE on|off|auto requires the badge always, never, or for a human account;
METHODOLOGY_REVIEW_TRACE=comment allows --kind review-record."""
import os, re, sys, subprocess
def setting(name, default):
    """METHODOLOGY_<name> from the environment, else from settings.env next to this script (written by install-methodology)."""
    f = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.env')
    saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
    return os.environ.get(f'METHODOLOGY_{name}') or saved.get(f'METHODOLOGY_{name}', default)
args = sys.argv[1:]
USAGE = "usage: post-lint <draft.md> [--kind reply|pr|issue|inline|tracker|proposal|review-record] [--repo owner/repo] [--parent <file>|none]"
def arg(name, default):
    if name not in args: return default
    i = args.index(name)
    if i + 1 >= len(args): sys.exit(USAGE)
    return args[i + 1]
if not args: sys.exit(USAGE)
path = args[0]; kind = arg('--kind', 'reply'); repo = arg('--repo', None)
kind = {'comment': 'reply'}.get(kind, kind)
if kind not in ('reply', 'pr', 'issue', 'inline', 'tracker', 'proposal', 'review-record'): sys.exit(USAGE)  # tracker: umbrella body or decisions comment, a growing list with no word budget
if kind == 'review-record' and setting('REVIEW_TRACE', 'hidden') != 'comment':
    sys.exit('review records stay in the artifact root (METHODOLOGY_REVIEW_TRACE=hidden)')
record = kind in ('tracker', 'review-record')  # records carry the process, with no word budget
text = open(path).read()
# An issue draft's first line may be its title ("Title: …"): the budget is for the body
text = re.sub(r'\ATitle:[^\n]*\n', '', text)
# Posts by the agent share the user's account: each starts with the Claude badge, so readers see who wrote it.
# The other checks run on the text after the badge.
BADGE = '<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**'
has_badge = text.lstrip().startswith(BADGE)
if has_badge:
    text = text.lstrip()[len(BADGE):].lstrip()
# What GitHub renders as the author's prose. Code (fenced, inline), quotes of others and
# HTML comments are neither linted nor counted; tables, images and URLs are evidence: linted, not counted.
prose = re.sub(r'^(```|~~~).*?^\1[^\n]*$', '', text, flags=re.S | re.M)
prose = re.sub(r'<!--.*?-->', '', prose, flags=re.S)
prose = re.sub(r'^\s*(?:[-*]\s+)?>.*$', '', prose, flags=re.M)
prose = re.sub(r'`[^`\n]*`', 'CODE', prose)
counted = re.sub(r'^\s*\|.*$', '', prose, flags=re.M)                 # table rows
counted = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', counted)                  # images
counted = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', counted)              # links: keep the text
counted = re.sub(r'https?://\S+', 'URL', counted)
findings = []
BANNED = [r'\bin this run\b', r"\bdoesn't establish\b", r'\bworth noting\b', r'\bhappy to\b', r'\blet me know\b',
          r'\bpushback welcome\b', r'\bsay the word\b', r'\bwant me to\b', r'\bshall I\b', r'\bif you want\b',
          r"\bif you'd rather\b", r'\byour call\b', r'\bI hope this helps\b', r'\bgreat question\b', r'\bdelve\b',
          r'\bleverage\b', r'\brobust\b', r'\bseamless(ly)?\b', r'\bcomprehensive\b', r'\bA risk I am handing over\b',
          r'\bthanks for the (LGTM|approval|review)\b', r"\bI'll treat\b", r'^\s*Understood\b']
for b in BANNED:
    for m in re.finditer(b, prose, flags=re.I | re.M):
        findings.append(f"banned phrase: {m.group(0).strip()!r}")
if '—' in prose:
    findings.append("em dash (—): rewrite the sentence")
for m in re.finditer(r'\bstacked on\b[^\n]*|\bstack(s|ed)? on (top of )?([\w.-]+/[\w.-]+)?#\d+[^\n]*', prose, flags=re.I):
    findings.append(f"'stacked on' claim ({m.group(0)[:60]!r}): only with gh stack; otherwise write 'depends on #N'")
for m in re.finditer(r'(?<![\w/.-])#(\d+)\b', prose):
    if not repo:
        findings.append(f"bare #{m.group(1)}: write owner/repo#{m.group(1)} (or pass --repo when it's the same repo)")
    elif subprocess.run(['gh', 'api', f'repos/{repo}/issues/{m.group(1)}', '--silent'], capture_output=True).returncode != 0:
        findings.append(f"bare #{m.group(1)} doesn't exist in {repo}: another repo's item? write owner/repo#{m.group(1)}")
words = len(re.findall(r"[A-Za-z0-9][\w'’-]*", counted))
chars = len(re.sub(r'\s+', ' ', counted).strip())
sentences = len(re.findall(r'[.!?](?=\s|$)', re.sub(r'\b(e\.g|i\.e|etc|vs)\.', '', counted).strip())) or 1
if kind == 'reply' and words > 80:
    findings.append(f"{words} words > 80 for a reply: cut what the reader doesn't need")
pr_budget = 250 if re.search(r'^#+ .*\b(notes|decisions)\b|^Decisions\b', text, re.I | re.M) else 150  # a PR with decisions for the maintainer may run longer
if kind == 'pr' and words > pr_budget:
    findings.append(f"{words} words > {pr_budget} for a PR body (tables, code, images and URLs not counted): cut what the reader doesn't need")
if kind == 'proposal' and words > 600:  # a design walkthrough (methodology 1.4 step 4)
    findings.append(f"{words} words > 600 for a proposal: cut what the reader doesn't need")
if kind == 'issue' and chars > 400:
    findings.append(f"{chars} characters > 400 for an issue (tables, code, images and URLs not counted): keep one finding")
if kind == 'inline' and sentences > 2:
    findings.append(f"{sentences} sentences > 2 for an inline comment")
# maintainer notes must be classified
for m in re.finditer(r'^\s*(?:[-*]|\d+\.)?\s*\*\*(Left to you|For you to decide|Note|Remark)[^\n]*', text, flags=re.M | re.I):
    line = m.group(0)
    if not re.search(r'\b(bug|limitation|not a regression|decision needed)\b', line, re.I) or not re.search(r'blocks', line, re.I):
        findings.append(f"unclassified note: {line.strip()[:70]!r} needs <bug|limitation|not a regression|decision needed> · blocks …: yes/no · next: …")
if len(re.findall(r'^\s*(?:[-*]|\d+\.)\s+[^\n|]*·\s*blocks', text, flags=re.M | re.I)) >= 2:
    findings.append("notes as a list of 'kind · blocks · next' lines: put them in one table | Note | Kind | Blocks merge | Next |")
# a follow-up is opened before the post, never parked as advice (methodology 1.6 notes, 1.1.7)
for row in re.findall(r'^\|(?:[^|\n]*\|){3}([^|\n]*)\|\s*$', text, flags=re.M):
    if re.search(r'\b(recommend|follow-up|follow up|later)\b', row, re.I):
        findings.append(f"notes table Next {row.strip()[:50]!r}: open the follow-up first and link it (PR <url>), fix it (fixed in <sha>), or write 'nothing, because …'")
# a found defect is fixed in this change, not parked in prose (methodology 1.1.7): the same bug elsewhere is related
for m in re.finditer(r"[^.\n]*\b(separate issue|separate PR|out of scope|left for later|for later|a later PR|follow-up issue|another PR)\b[^.\n]*", prose, re.I):
    findings.append(f"deferral {m.group(0).strip()[:70]!r}: fix it in this change, open the PR now and link it, or quote the user's OK (1.1.7)")
badge = setting('BADGE', 'on')  # auto: only a human account (`gh api user` type User, not Bot) needs it
if kind != 'tracker' and not has_badge and (badge == 'on' or badge == 'auto' and
        subprocess.run(['gh', 'api', 'user', '--jq', '.type'], capture_output=True, text=True).stdout.strip() == 'User'):
    findings.append(f"missing badge: start the post with {BADGE}")
# the process stays in the artifact root: the reader gets results, not how the agent produced them
if not record:
    PROCESS = [r'\breview rounds?\b', r'\b(refactor|verification|dry) pass(es)?\b', r'\bcharter\b', r'\bgpt-\d[\w.-]*',
               r'\bcodex\b', r'\bsub-?agents?\b', r'\bout of credits\b', r'\bCHANGES-REQUESTED\b', r'\b(posting|fast) gate\b',
               r'\b\d+(\.\d+)?/10\b', r'\brated (every|each)\b']
    # A maintainer who asks for a review ("Review each of my commits") wants per-item ratings: allowed then
    _parent = re.sub(r'\.md$', '', path) + '.parent.md'
    _parent = arg('--parent', None) if arg('--parent', None) not in (None, 'none') else _parent
    # ...and so does the commit-review table itself (| Commit | What it does, and the idea behind it | Rating |), whatever else the reply answers
    if re.search(r'^\|\s*Commit\s*\|.*\|\s*Rating\s*\|', text, re.M) or \
            (__import__('os').path.exists(_parent) and re.search(r'\breview\b', open(_parent).read(), re.I)):
        PROCESS = [b for b in PROCESS if '/10' not in b]
    for b in PROCESS:
        for m in re.finditer(b, prose, flags=re.I):
            findings.append(f"process in the thread: {m.group(0)!r}: give the result, keep reviews, rounds and ratings in the artifact root")
# a question to the reader carries our recommendation
asks = [q.strip() for q in re.findall(r'[^.!?\n]*\?(?=\s|$)', prose)]
if not record and asks and not re.search(r"\b(I recommend|recommend|I'd|I would|I propose|I suggest|I'll go with)\b|^GENUINE-FORK:", prose, re.I | re.M):
    findings.append(f"question without your recommendation ({asks[0][-60:]!r}): decide or measure it yourself, or say what you'd pick and why")
# a bare "Done" to a question or a soft suggestion: say what you checked, or push back
if kind in ('reply', 'inline'):
    parent_arg = arg('--parent', None)
    stem = re.sub(r'\.md$', '', path) + '.parent.md'
    parent_path = parent_arg if parent_arg not in (None, 'none') else (stem if parent_arg is None else None)
    if parent_arg is None and not __import__('os').path.exists(stem):
        findings.append(f"no parent: save the comment you answer as {stem}, or pass --parent none for a comment that answers nobody")
    elif parent_path:
        parent = open(parent_path).read()
        suggestion_block = re.search(r'^```suggestion', parent, re.M)
        parent_prose = re.sub(r'^(```|~~~).*?^\1[^\n]*$', '', parent, flags=re.S | re.M)
        parent_prose = re.sub(r'^\s*>.*$', '', parent_prose, flags=re.M)
        question = re.search(r"\?|\b(how about|what about|I think|maybe|shouldn't|why|would it|could we|can we|isn't)\b", parent_prose, re.I)
        bare = re.sub(r'\b[0-9a-f]{7,40}\b|\([^)]*\)', '', counted)
        if question and not suggestion_block and re.match(r'\s*(Done|Fixed|Removed|Applied|Changed|Reverted|Updated)\b', counted) \
                and len(re.findall(r"[A-Za-z][\w'-]*", bare)) <= 4:
            findings.append("bare 'Done' answering a question or a soft suggestion: say what you checked and why you agree, or push back")
for f in findings: print(f)
sys.exit(1 if findings else 0)
