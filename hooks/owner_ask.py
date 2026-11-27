#!/usr/bin/env python3
"""Whether a message the user typed asks for a merge, a push to a default branch, a release or an ask-first command (pre-bash-guard).
Its cases are tests/owner-ask.tsv."""
import json, re
import shellcmd
from t3_tasks import typed

# What runs only on the owner's ask: the words of a sentence that asks for it, the project file's `## Merging` order that stands in for one,
# and the reply that asks for it
ASKED_FOR = {'merge': (r'merge(?!ab)\w*', r'Merge each PR as soon as it is ready\b', 'merge'),  # "mergeable" is a state
             'push': (r'push(?!\w*\s+(?:for|back)\b)\w*|releas\w*|publish\w*', r'Push to {branch}(?!\S)', 'push'),  # a release asked for pushes its version commit
             'release': (r'releas\w*|publish\w*', None, 'release'),
             'ask-first': (r'update\w*|restart\w*|frissít\w*', None, 'update')}
OBJECTS = {'merge': r'(?:(?:the|this|that|my|your|our|both|a|az)\s+)?(?:(?!(?:other|another|next|previous|last|old)\b)[\w-]+\s+)?(?:(?:pr|mr)(?:s|t|ek|eket|-\w+)?|pull requests?|merge requests?|fix(?:es)?|changes?)\b',
           'release': r'(?:(?:a|the)\s+)?(?:new\s+)?(?:(?:major|minor|patch)(?:\s+(?:version|release))?|version|release|package)\b',
           'ask-first': r'(?!)'}
OBJECTS['push'] = rf"(?:the\s+)?(?:changes|commits?|fix(?:es)?|tags?)\b|v?\d+(?:\.\d+)+|{OBJECTS['release']}"
# a package's name after a release's word; a word that says something of the action ("release is out", "or will I", "prep") is none
NAME = r"(?:\s+(?:of|for)\b)?\s*(?!(?:is|isn|was|are|were|went|has|had|have|looks?|seems?|should|will|would|can|could|must|may|might|did|does|do|done|or|and|prep|notes?|first|then|if|when|after|before|until|once)\b)[@\w][\w@/.-]*"
PRONOUN = r'(?:it|this|that|them|these|both|everything|all)(?:\s+(?:one|all|both))?\b'
OPENERS = {'courtesy': r'please|pls|plz|kérlek|kerlek|légyszi|legyszi',
           'go-ahead': r'ok(?:ay)?|oké|oke|yes|yeah|yep|sure|alright|igen|rendben',
           'sequence': r'now|just|then|so|also|for now|aztán|aztan|most|akkor|szóval',
           'request': r"let['’]?s|let us|i want you to|i'd like you to|i need you to|(?:can|could|would|will) you|go ahead and|you can|feel free to"}
# the words that hold the action back in a clause that names it
HOLDS = {'negation': r"don'?t|\w+n['’]t|do not|never|not|no|ne|nem",
         'deferral': r'majd|várj|varj|wait|later|after|until|miután',
         'condition': r'(?<!the )only|once|when|if|ha',
         'reversal': r'cancel\w*|abort\w*|revert\w*|undo|stop',
         'question': r'who|why'}
HOLD = re.compile(rf"\b(?:{'|'.join(HOLDS.values())})\b", re.I)
# a sentence without the action's words that holds it back: "Wait for CI.", "Stop.", "Don't."
HALT = re.compile(rf"(?:[-*•]\s*)?(?:(?:but|so|ok|{OPENERS['courtesy']})\W+)*(?:(?:wait|várj|varj|not yet|hold on|hold off)\b|(?:stop|cancel|don['’]?t|do not|no|ne|nem)[\s.!]*$)", re.I)
# a clause asking to be told after the action ("then tell me if CI fails") says nothing about it, one asking first ("tell me before you proceed") holds it
FOLLOW_UP = re.compile(rf"(?:(?:then|and|aztán|aztan|és|majd|just|{OPENERS['courtesy']})\W+)*(?:(?:tell|ping|notify|message|show)\s+me|let\s+me\s+know|report\s+back|szólj|szolj|jelezz|írd\s+meg|ird\s+meg)\b", re.I)
FIRST = re.compile(r'\b(?:before|first|discuss\w*|proceed\w*|előtte|először)\b', re.I)
NO_WAIT = re.compile(r"\b(?:don['’]?t|do not|no need to|ne|nem kell)\s+(?:wait|várj|varj|várni|varni)\b(?:\s+(?:for|until|till|on)\b.*)?", re.I)
LEAD = rf"(?:[-*•]\s*)?(?:(?:{'|'.join(OPENERS.values())})\W+)*"
REQUEST = rf"(?:[-*•]\s*)?(?:(?:{OPENERS['courtesy']}|{OPENERS['go-ahead']}|{OPENERS['sequence']})\W+)*(?:can|could|would|will) you\b"  # a question that asks
TAIL = rf"(?:{OPENERS['courtesy']}|thanks|thx|ty|now|too|also|as well|today|right away|asap|as soon as (?:you can|possible)|for me|most|amint (?:tudod|lehet))\b"  # courtesy, time
PAST = r'(?!(?!frissít)\w*ed\b)'  # an English past form (merged, released); Hungarian "frissítsed" is an imperative
MENTION = r'(?!\s+(?:conflicts?|requests?|notes?|plans?|queue)\b)'

PR_REF = re.compile(r'(?:github\.com/([\w.-]+/[\w.-]+)/pull/|gitlab\.com/([\w./-]+?)/-/merge_requests/|\b([\w.-]+/[\w./-]*[\w-])[#!]|[#!]|(?i:\b(?:pr|mr|pull request)\s+))(\d+)\b')  # a PR, an MR (!N)
SHAPED = re.compile(r"\d|[/#@_:=~\\]|\w\.\w|^!\w")  # a token that may name a target: a number, a path, a ref, a dotted name, a link
PEEL = re.compile(r"^([(\[{\"'“‘*]*)(.*?)([)\]}\"'”’*.,;:!?]*)$", re.S)  # a token's outer punctuation

def asks(text, kind, repo=None, num=None, branch=None, subject=None, names=()):
    """True when text (a message the user typed) asks for kind on its target (PR num of repo, branch, or subject: a release's tag,
    an ask-first command's line), False when it holds kind back, None when it says neither. names: the command's other names (its repo,
    its package); a token equal to one names no other target, any other token shaped like a target leaves its clause no ask."""
    names = {n.lower() for n in names if n}
    bare = lambda t: re.sub(r'\bmergeworthy\w*', ' ', t, flags=re.I)
    words = rf'\b(?:{ASKED_FOR[kind][0]})\b{MENTION}'
    ask = re.compile(rf"{LEAD}(?:‹t›\s*)?{PAST}{words}(?:\s+be\b)?\s*(?:{PRONOUN}|(?:(?:all|every|each|both)(?:\s+of)?\s+)?(?:{OBJECTS[kind]}))?\s*(?:(?:(?:the|a|az)\s+)?‹t›(?:\s*-\w+)?)?"
                     rf"(?:{NAME if kind in ('release', 'push') else '(?!)'})?(?:\s+(?:in)?to\s+(?:the\s+)?[\w./-]+)?(?:[\s,]*{TAIL})*[\s.!?]*", re.I)
    tok = lambda ours: ' ‹t› ' if ours else ' ‹x› '
    def marked(c):  # c with each target it names in kind's notations as ‹t› (this command's) or ‹x› (another)
        if kind == 'merge':
            return re.sub(r'(?:https?://)?' + PR_REF.pattern, lambda m: tok((m[1] or m[2] or m[3] or '').lower() in ('', (repo or '').lower()) and m[4] == str(num)), c)
        if kind == 'push':  # `to <branch>`, `<branch> branch` or `push <branch>`
            c = re.sub(r'\bto\s+(?:the\s+)?(?:branch\s+)?(?!(?:the|a|this|that)\b)([\w./-]*[\w-])(?:\s+branch\b)?|\b(?!(?:the|a|this|that)\b)([\w./-]*[\w-])\s+branch\b',
                       lambda m: tok((m[1] or m[2]) == branch), c, flags=re.I)
            return re.sub(rf"(\bpush\w*\s+)(?!(?:{PRONOUN}|{TAIL}|{OBJECTS['push']}|the|an?|to|and|then|for|back)(?![\w./-]))([\w./-]*[\w-])",
                          lambda m: m[1] + tok(False), c, flags=re.I)
        if kind == 'release':
            return re.sub(r'(?<![\w./@-])v?\d+(?:\.\d+)+(?:[-+][\w.-]*\w)?(?![\w/-]|\.\w)', lambda m: tok(subject is None or m[0].lower().lstrip('v') == subject.lower().lstrip('v')), c)
        own = set(re.split(r'[^\w.]+', (subject or '').lower())) - {''}  # an ask-first command's words: "update t3" names t3-update
        return re.sub(r'(?<![\w./@#-])[\w.]+(?![\w/@#-])', lambda m: tok(True) if not re.fullmatch(words, m[0], re.I) and any(o.startswith(m[0].lower()) for o in own) else m[0], c)
    def whole(chunk):  # a token marked() left: the pushed branch, one of names, a word, or ‹o› when shaped like a target
        lead, core, trail = PEEL.match(chunk).groups()
        core = core.strip('`')
        if kind == 'push' and core == branch: return lead + tok(True) + trail
        if '‹' in core or not core or core.lower() in names: return chunk
        if kind == 'push' and re.fullmatch(r'v?\d+(?:\.\d+)+', core): return chunk  # a release's version, asked for with a release's word
        return lead + (' ‹o› ' if SHAPED.search(core) else core) + trail
    t = re.sub(r'`([^`\s]+)`', r'\1', re.sub(r'^\s*\(Re-invocation of .*', ' ', text, flags=re.I))  # a target as inline code
    if kind == 'push' and branch:  # the pushed branch as a whole token; git's branch names are case-sensitive
        t = re.sub(r'(?<![^\s(\[{"\'“‘])' + re.escape(branch) + r'(?=[)\]}"\'”’.,;:!?]*(?:\s|$))', '‹T›', t)
        t = re.sub(r'\bto\s+(?:the\s+)?(?:branch\s+)?‹T›(?:\s+branch\b)?|‹T›\s+branch\b', '‹T›', t, flags=re.I)
    t = re.sub(r'\S+', lambda m: whole(m[0]), marked(t).replace('‹T›', tok(True)))
    # what a clause (stripped) says of the action, in a question or not: the first row that matches
    STANCE = (('holds', lambda m, q: FOLLOW_UP.match(m) and FIRST.search(m)),  # "tell me before you proceed"
              ('reports', lambda m, q: FOLLOW_UP.match(m) and re.search(rf'{PAST}{words}', m, re.I)),  # "tell me when you merge it": a hold unless the message asks
              (None, lambda m, q: FOLLOW_UP.match(m)),  # "then tell me if CI fails"
              ('holds', lambda m, q: HOLD.search(NO_WAIT.sub(' ', m))),  # "don't wait for me" holds nothing
              ('asks', lambda m, q: ask.fullmatch(m) and (not q or re.match(REQUEST, m, re.I))))
    stance = lambda m, question: next((st for st, test in STANCE if test(m.strip(), question)), None)
    on = lambda m: '‹t›' in m or '‹x›' not in m  # names the target, or none
    found = reported = None
    for s in re.split(r'(?<=[.!?])\s+|\n', t):
        if not re.search(words, bare(s), re.I):
            if HALT.match(m := bare(s).strip()) and on(m): return False
            continue
        for c in re.split(r'[,;—–]|\s-+\s|(?<![\w-])then(?![\w-])|(?<![\w-])(?:and|és)(?![\w-])(?!\s*‹)', s, flags=re.I):
            st = stance(m := bare(c), s.rstrip().endswith('?'))
            if st == 'holds' and on(m): return False
            reported = reported or st == 'reports' and on(m)
            found = found or st == 'asks' and ('‹t›' in m or on(t)) or None
    return found or (False if reported else None)

def last_typed(transcript_path):
    """The message the user last typed in the session whose transcript is at transcript_path (t3_tasks.typed); '' with none."""
    try:
        for l in shellcmd.rlines(transcript_path or ''):
            if b'"user"' not in l: continue
            try: e = json.loads(l)
            except ValueError: continue
            if isinstance(e, dict) and e.get('type') == 'user' and not e.get('isSidechain') and not e.get('isMeta') and (t := typed((e.get('message') or {}).get('content'))):
                return t
    except OSError: pass
    return ''
