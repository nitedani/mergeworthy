#!/usr/bin/env python3
"""Whether a message the user typed asks for a merge, a push to a default branch, a release or an ask-first command (pre-bash-guard).
Its cases are tests/owner-ask.tsv."""
import re

# What runs only on the owner's ask: the words of a sentence that asks for it, the project file's `## Merging` order that stands in for one,
# and the reply that asks for it
ASKED_FOR = {'merge': (r'merge(?!ab)\w*', r'Merge each PR as soon as it is ready\b', 'merge'),  # "mergeable" is a state
             'push': (r'push(?!\w*\s+(?:for|back)\b)\w*|releas\w*|publish\w*', r'Push to {branch}(?!\S)', 'push'),  # a release asked for pushes its version commit
             'release': (r'releas\w*|publish\w*', None, 'release'),
             'ask-first': (r'update\w*|restart\w*|frissít\w*', None, 'update')}
# what an ask may name after the word besides its target and a pronoun: a merge its PRs ("the sentry pr", "az osszes prt"), a push its commits,
# a release a new version ("a minor"); a release or a push may also name a package ("vike-react-apollo", "a minor of vike-react-sentry")
OBJECTS = {'merge': r'(?:(?:the|this|that|my|your|our|both|a|az)\s+)?(?:(?!(?:other|another|next|previous|last|old)\b)[\w-]+\s+)?(?:(?:pr|mr)(?:s|t|ek|eket|-\w+)?|pull requests?|merge requests?|fix(?:es)?|changes?)\b',
           'release': r'(?:(?:a|the)\s+)?(?:new\s+)?(?:(?:major|minor|patch)(?:\s+(?:version|release))?|version|release|package)\b',
           'ask-first': r'(?!)'}
OBJECTS['push'] = rf"(?:the\s+)?(?:changes|commits?|fix(?:es)?|tags?)\b|v?\d+(?:\.\d+)+|{OBJECTS['release']}"
# a package's name after a release's word; a word that says something of the action ("release is out", "or will I", "prep") is none
NAME = r"(?:\s+(?:of|for)\b)?\s*(?!(?:is|isn|was|are|were|went|has|had|have|looks?|seems?|should|will|would|can|could|must|may|might|did|does|do|done|or|and|prep|notes?|first|then|if|when|after|before|until|once)\b)[@\w][\w@/.-]*"
PRONOUN = r'(?:it|this|that|them|these|both|everything|all)(?:\s+(?:one|all|both))?\b'
NEGATED = re.compile(r"\b(?:don'?t|\w+n['’]t|do not|never|not|no|who|why|(?<!the )only|cancel\w*|abort\w*|revert\w*|undo|stop|ne|nem|majd|várj|varj|wait|later|after|once|when|until|if|ha|miután)\b", re.I)
# a sentence without the action's words that holds it back: "Wait for CI.", "Stop.", "Don't."
HALT = re.compile(r"(?:[-*•]\s*)?(?:(?:but|so|ok|please|pls)\W+)*(?:(?:wait|várj|varj|not yet|hold on|hold off)\b|(?:stop|cancel|don['’]?t|do not|no|ne|nem)[\s.!]*$)", re.I)
# a clause asking to be told after the action ("then tell me if CI fails") says nothing about it, one asking first ("tell me before you proceed") holds it
FOLLOW_UP = re.compile(r"(?:(?:then|and|aztán|aztan|és|majd|just|please|pls)\W+)*(?:(?:tell|ping|notify|message|show)\s+me|let\s+me\s+know|report\s+back|szólj|szolj|jelezz|írd\s+meg|ird\s+meg)\b", re.I)
FIRST = re.compile(r'\b(?:before|first|discuss\w*|proceed\w*|előtte|először)\b', re.I)
NO_WAIT = re.compile(r"\b(?:don['’]?t|do not|no need to|ne|nem kell)\s+(?:wait|várj|varj|várni|varni)\b(?:\s+(?:for|until|till|on)\b.*)?", re.I)
# an ask opens a clause, after a list bullet and the words of these classes at most; each class is a reason a word may stand there, so a word
# missing from one is added to its class. "merge conflicts", "release notes" and "update plan" name a thing, not the action
OPENERS = {'courtesy': r'please|pls|plz|kérlek|kerlek|légyszi|legyszi',
           'go-ahead': r'ok(?:ay)?|oké|oke|yes|yeah|yep|sure|alright|igen|rendben',
           'sequence': r'now|just|then|so|also|for now|aztán|aztan|most|akkor|szóval',
           'request': r"let['’]?s|let us|i want you to|i'd like you to|i need you to|(?:can|could|would|will) you|go ahead and|you can|feel free to"}
LEAD = rf"(?:[-*•]\s*)?(?:(?:{'|'.join(OPENERS.values())})\W+)*"
REQUEST = rf"(?:[-*•]\s*)?(?:(?:{OPENERS['courtesy']}|{OPENERS['go-ahead']}|{OPENERS['sequence']})\W+)*(?:can|could|would|will) you\b"  # a question that asks
TAIL = rf"(?:{OPENERS['courtesy']}|thanks|thx|ty|now|too|also|as well|today|right away|asap|as soon as (?:you can|possible)|for me|most|amint (?:tudod|lehet))\b"  # courtesy, time
PAST = r'(?!(?!frissít)\w*ed\b)'  # an English past form (merged, released); Hungarian "frissítsed" is an imperative
MENTION = r'(?!\s+(?:conflicts?|requests?|notes?|plans?|queue)\b)'

PR_REF = re.compile(r'(?:github\.com/([\w.-]+/[\w.-]+)/pull/|gitlab\.com/([\w./-]+?)/-/merge_requests/|\b([\w.-]+/[\w./-]*[\w-])[#!]|[#!]|(?i:\b(?:pr|mr|pull request)\s+))(\d+)\b')  # a PR, an MR (!N)

def asks(text, kind, repo=None, num=None, branch=None, subject=None):
    """Whether text (a message the user typed) asks for kind on its target: PR num of repo, the branch pushed, or subject (a release's tag, an
    ask-first command's line). Each sentence holding kind's words is split into clauses (at commas, semicolons, dashes, "then" and an "and"
    before a word) and read once URLs, `(Re-invocation of` lines and the word mergeworthy are out. A clause holds kind back when it negates
    it or puts it off, unless it only asks to be told after it or not to wait (NO_WAIT); it asks when it is kind's word as an imperative
    (after the openers, in no past form), followed by the target, a pronoun, one of kind's OBJECTS, a released package's NAME or nothing,
    then courtesy or a time (TAIL), in a sentence that is no question or a request (`can you`). A clause naming another target neither asks
    nor holds for this one; a clause naming none counts for the target when the message names it or no other. A sentence without kind's
    words holds when it opens with a HALT. False on a hold, else True on an ask, else None."""
    bare = lambda t: re.sub(r'https?://\S+|\bmergeworthy\w*|^\s*\(Re-invocation of .*', ' ', t, flags=re.I)
    words = rf'\b(?:{ASKED_FOR[kind][0]})\b{MENTION}'
    ask = re.compile(rf"{LEAD}(?:‹t›\s*)?{PAST}{words}(?:\s+be\b)?\s*(?:{PRONOUN}|{OBJECTS[kind]})?\s*(?:(?:(?:the|a|az)\s+)?‹t›(?:\s*-\w+)?)?"
                     rf"(?:{NAME if kind in ('release', 'push') else '(?!)'})?(?:\s+(?:in)?to\s+(?:the\s+)?[\w./-]+)?(?:[\s,]*{TAIL})*[\s.!?]*", re.I)
    def marked(c):  # c with each target it names as ‹t› (this command's) or ‹x› (another)
        tok = lambda ours: ' ‹t› ' if ours else ' ‹x› '
        if kind == 'merge':
            return re.sub(r'(?:https?://)?' + PR_REF.pattern, lambda m: tok((m[1] or m[2] or m[3] or '').lower() in ('', (repo or '').lower()) and m[4] == str(num)), c)
        if kind == 'push':  # `to <branch>`, `<branch> branch`, `push <branch>`, or the pushed branch's name; git's branch names are case-sensitive
            c = re.sub(r'\bto\s+(?:the\s+)?(?:branch\s+)?(?!(?:the|a|this|that)\b)([\w./-]*[\w-])(?:\s+branch\b)?|\b(?!(?:the|a|this|that)\b)([\w./-]*[\w-])\s+branch\b',
                       lambda m: tok((m[1] or m[2]) == branch), c.replace('`', ''), flags=re.I)
            c = re.sub(rf'(?<![\w./-]){re.escape(branch)}(?![\w./-])', tok(True), c) if branch else c
            return re.sub(r'(\bpush\w*\s+)(?!(?:it|this|that|them|these|the|a|an|to|all|everything|changes|commits?|fix\w*|tags?|now|please|pls|and|then)\b)([\w./-]*[\w-])',
                          lambda m: m[1] + tok(False), c, flags=re.I)
        if kind == 'release':
            return re.sub(r'\bv?\d+(?:\.\d+)+\b', lambda m: tok(subject is None or m[0].lower().lstrip('v') == subject.lower().lstrip('v')), c)
        own = set(re.split(r'[^\w.]+', (subject or '').lower())) - {''}  # an ask-first command's words: "update t3" names t3-update
        return re.sub(r'[\w.]+', lambda m: tok(True) if not re.fullmatch(words, m[0], re.I) and any(o.startswith(m[0].lower()) for o in own) else m[0], c)
    def stance(m, question):  # 'holds', 'asks' or None for clause m, marked and bare
        if FOLLOW_UP.match(m.strip()) and FIRST.search(m): return 'holds'
        if FOLLOW_UP.match(m.strip()) and not re.search(rf'{PAST}{words}', m, re.I): return None
        if NEGATED.search(NO_WAIT.sub(' ', m)): return 'holds'
        if ask.fullmatch(m.strip()) and (not question or re.match(REQUEST, m.strip(), re.I)): return 'asks'
    on = lambda m: '‹t›' in m or '‹x›' not in m  # names the target, or none
    found = None
    for s in re.split(r'(?<=[.!?])\s+|\n', text):
        if not re.search(words, bare(s), re.I):
            if HALT.match(m := bare(marked(s)).strip()) and on(m): return False
            continue
        for c in re.split(r'[,;—–]|\bthen\b|\b(?:and|és)\b(?!\s*(?:[#!]\d|https?:|[\w.-]+/[\w./-]*[#!]\d))', s):
            st = stance(m := bare(marked(c)), s.rstrip().endswith('?'))
            if st == 'holds' and on(m): return False
            found = found or st == 'asks' and ('‹t›' in m or on(marked(text))) or None
    return found
