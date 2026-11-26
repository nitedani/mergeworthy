#!/usr/bin/env python3
"""Whether a message the user typed asks for a merge, a push to a default branch, a release or an ask-first command (pre-bash-guard).
Its cases are tests/owner-ask.tsv."""
import re

# What runs only on the owner's ask: the words of a sentence that asks for it, the project file's `## Merging` order that stands in for one,
# and the reply that asks for it
ASKED_FOR = {'merge': (r'merge\w*', r'Merge each PR as soon as it is ready\b', 'merge'),
             'push': (r'push(?!\w*\s+(?:for|back)\b)\w*|releas\w*|publish\w*', r'Push to {branch}(?!\S)', 'push'),  # a release asked for pushes its version commit
             'release': (r'releas\w*|publish\w*', None, 'release'),
             'ask-first': (r'update\w*|restart\w*|frissít\w*', None, 'update')}
NEGATED = re.compile(r"\b(?:don'?t|\w+n['’]t|do not|never|not|no|who|why|ne|nem|majd|várj|varj|wait|later|after|once|when|until|if|ha|miután)\b", re.I)
# a clause that opens with another request to report back ("then tell me if CI fails") says nothing about the action, and "don't wait" holds nothing back
FOLLOW_UP = re.compile(r"(?:(?:then|and|aztán|aztan|és|majd|just|please|pls)\W+)*(?:(?:tell|ping|notify|message|show)\s+me|let\s+me\s+know|report\s+back|szólj|szolj|jelezz|írd\s+meg|ird\s+meg)\b", re.I)
NO_WAIT = re.compile(r"\b(?:don'?t|do not|no need to|ne|nem kell)\s+(?:wait|várj|varj|várni|varni)\b", re.I)
# an ask opens a clause, after a list bullet and the words of these classes at most; each class is a reason a word may stand there, so a word
# missing from one is added to its class. "merge conflicts", "release notes" and "update plan" name a thing, not the action
OPENERS = {'courtesy': r'please|pls|plz|kérlek|kerlek|légyszi|legyszi',
           'go-ahead': r'ok(?:ay)?|oké|oke|yes|yeah|yep|sure|alright|igen|rendben',
           'sequence': r'now|just|then|so|also|for now|aztán|aztan|most|akkor|szóval',
           'request': r"let['’]?s|let us|i want you to|i'd like you to|i need you to|(?:can|could|would|will) you|go ahead and|you can|feel free to"}
LEAD = rf"(?:[-*•]\s*)?(?:(?:{'|'.join(OPENERS.values())})\W+)*"
MENTION = r'(?!\s+(?:conflicts?|requests?|notes?|plans?|queue)\b)'

PR_REF = re.compile(r'(?:github\.com/([\w.-]+/[\w.-]+)/pull/|gitlab\.com/([\w./-]+?)/-/merge_requests/|\b([\w.-]+/[\w./-]*[\w-])[#!]|[#!])(\d+)\b')  # a PR, an MR (!N)

def asks(text, kind, repo=None, num=None, branch=None):
    """Whether text (a message the user typed) asks for kind on its target, read by the clauses (split at commas, semicolons and an "and"
    before a word) of each sentence holding kind's words, once URLs, `(Re-invocation of` lines and the word mergeworthy are taken out: False
    when a clause negates them or puts them off, naming the target or none (a "don't wait", or a clause asking to be told that names neither
    them nor a target, holds nothing back); True when a clause opens with them in no past form (-ed), the sentence is no question, and the
    clause names the target: PR num of repo when it (else the text) names PRs, the branch pushed when it names a branch (`to <branch>`,
    `<branch> branch`); else None."""
    refs = lambda t: [((m[1] or m[2] or m[3] or '').lower(), m[4]) for m in PR_REF.finditer(t)]
    bare = lambda t: re.sub(r'https?://\S+|\bmergeworthy\w*|^\s*\(Re-invocation of .*', ' ', t, flags=re.I)
    words = rf'\b(?:{ASKED_FOR[kind][0]})\b{MENTION}'
    def named(c):  # the targets clause c names: a merge's PRs as (repo, number), a push's branches, as words or `inline code`
        if kind == 'merge': return refs(c)
        return {x for x in re.findall(r'\bto\s+(?:the\s+)?(?:branch\s+)?([\w./-]*[\w-])|([\w./-]*[\w-])\s+branch\b', c.replace('`', ''), re.I) for x in x if x and x.lower() not in ('the', 'a', 'this', 'that')} if kind == 'push' else set()
    def hits(t): return any(r in ('', (repo or '').lower()) and n == str(num) for r, n in t) if kind == 'merge' else (branch or '') in t  # git's branch names are case-sensitive
    def holds(c):  # c negates the action or puts it off; a follow-up naming neither the action nor a target, or a "don't wait", holds nothing
        if not re.search(words, bare(c), re.I) and not named(c) and FOLLOW_UP.match(bare(c).strip()): return False
        return bool(NEGATED.search(NO_WAIT.sub(' ', bare(c))))
    found = None
    for s in re.split(r'(?<=[.!?])\s+|\n', text):
        if not re.search(words, bare(s), re.I): continue
        clauses = re.split(r'[,;]|\b(?:and|és)\b(?!\s*(?:[#!]\d|https?:|[\w.-]+/[\w./-]*[#!]\d))', s)
        held = [c for c in clauses if holds(c)]
        if any(not named(c) or hits(named(c)) for c in held): return False
        found = found or not s.rstrip().endswith('?') and any(
            c not in held and re.match(LEAD + r'(?!\w*ed\b)' + words, bare(c).strip(), re.I) and (not (t := named(c) or (refs(text) if kind == 'merge' else [])) or hits(t)) for c in clauses) or None
    return found
