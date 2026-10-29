#!/usr/bin/env python3
"""What a final message says, for stop-lint's message checks: an offer or hand-back, its GENUINE-FORK lines, its Running list,
the PRs its opening calls done, and the PR states its sentences claim. Text in, findings out: nothing here reads GitHub or T3."""
import re


def authored(message):
    """The message without code, quotes and quoted lines: the agent's own words."""
    # quoted words are someone else's (a user's "should I ...?", a banned phrase being discussed): not an offer
    return re.sub(r'```.*?```|`[^`\n]*`|"[^"\n]*"|[“„][^”\n]*”|^>[^\n]*$', ' ', message, flags=re.S | re.M)


# An offer, or a hand-back of work the agent can do or wait for itself ("tell me when to re-check CI", "nothing will notify me")
OFFER = (r"(when you say (go|so)|say the word|(do|would) you (want|like) me to|want me to|shall I\b|should I\b|if you want|if you'd (rather|like)|your call|"
         r"is yours to|up to you|or would you rather|which do you (want|prefer)|let me know (if|when|whether)|"
         r"(?:^[\s>*\-•]*|[.!?:;,]\s*|\b(?:or|and|just|please)\s+)(?:tell me (when|to|if|whether)|ask me (to|when|if)|ping me)|nothing (will|would|is going to) (notify|wake|tell) me|(won't|will not|doesn't|does not|can't) (notify|wake) me)\b")
def offer(message): return re.search(OFFER, authored(message), re.I | re.M)
def forks(text): return {re.sub(r'\W+', ' ', f).strip().lower() for f in re.findall(r'^GENUINE-FORK:(.*)$', text, re.M)}


def running_list(message):
    """What a `Running:` label or heading lists, lowercased; None when the message has none."""
    running = re.search(r'^(?:#+ *Running\b|[-*\s]*\*{0,2}Running\*{0,2}:)(.*(?:\n[ \t]*[-*\d].*)*)', message, re.M)
    return running and running.group(1).lower()


# The words that take back a claim, one row per language; a word added here holds for the done opening and the PR states alike
LEX = {
    'NEGATION': {'en': r"not|no|none|nothing|neither|nor|never|nobody|\w+n['’]t", 'hu': r"nem|nincs\w*|sincs\w*|sem|semmi\w*|senki|soha"},
    'FUTURE': {'en': r"will|would|\w+['’]ll|going to|tomorrow|later|soon|next|expect\w*|wait\w*", 'hu': r"lesz\w*|lenne\w*|majd|holnap\w*|később|hamarosan"},
    'CONDITION': {'en': r"once|when|if|until|after|before|unless|whether", 'hu': r"ha|amint|amikor|mihelyt|amíg|\w+-ig"},
    'CONJUNCTION': {'en': r"and|but|so", 'hu': r"és|de|ezért|viszont"},
}
FUTURE, CONDITION, CONJUNCTION = (re.compile(rf"\b(?:{LEX[k]['en']}|{LEX[k]['hu']})\b", re.I) for k in ('FUTURE', 'CONDITION', 'CONJUNCTION'))
# English negates before the claim ("is not ready"; "ready with no issues" still claims), Hungarian on either side ("kész még nem vagyok")
NEGATION_EN, NEGATION_HU = (re.compile(rf"\b(?:{LEX['NEGATION'][l]})\b", re.I) for l in ('en', 'hu'))
PART = re.compile(r"[,;:](?=\s|$)")  # not the colon of https:
CLAUSE = re.compile(rf"(?={CONJUNCTION.pattern})", re.I)


def asserted(sentence, i):
    """Whether the words at sentence[i] state something as true now: no negation in their clause, an English one only before them
    ("none is ready", "kész még nem vagyok"; "ready with no issues" still claims), no plan in their clause ("it will be ready",
    "és kész lesz"), no condition in their part or opening the next one ("once it is ready", "kész, ha zöld a CI"). A question
    still claims ("Kész van?" next to a draft MR is refused, as on main). A part ends at a comma, semicolon or colon; a clause also
    before a conjunction."""
    before, (part, *after) = PART.split(sentence[:i])[-1], PART.split(sentence[i:], 1)
    lead = CLAUSE.split(before)[-1]
    clause = lead + CLAUSE.split(part)[0]
    return not (NEGATION_EN.search(lead) or NEGATION_HU.search(clause) or FUTURE.search(clause) or CONDITION.search(before + part)
                or after and CONDITION.match(after[0].lstrip()))


DONE = r"\b(?:(?:is|are|all|work's|it's) (?:done|finished|complete)\b|ready (?:for review|to merge)|kész\b|elkészült|befejeztem)"
LINK = r'https://(github\.com|gitlab\.[\w.]+)/([\w.-]+/[\w./-]+?)(?:/-)?/(?:pull|merge_requests)/(\d+)'
SENTENCE = r'(?<=[.!?])\s+|\n+'


def done_links(message):
    """(host, path, number) of each PR or MR the opening sentence calls done, at most 10: those it links ("#1 is ready for
    review", while #26 is a draft), else every one the message links; [] when it calls nothing done."""
    first = re.split(SENTENCE, authored(message).strip())[0]
    if not any(asserted(first, m.start()) for m in re.finditer(DONE, first, re.I)): return []
    return list(dict.fromkeys(re.findall(LINK, first) or re.findall(LINK, message)))[:10]


# `#N`, `owner/repo#N`, its URL, `PR #N`, `CI on #N` as a sentence's subject; "My reply to #12 is a draft" has another subject
REF = r"(?:https://github\.com/(?P<r1>[\w.-]+/[\w.-]+)/pull/(?P<n1>\d+)|(?<![\w/])(?P<r2>[\w.-]+/[\w.-]+)?#(?P<n2>\d+)\b)"
SUBJECT = r"(?:^[\s>*\-•\d.)]*|(?<=[,;:(])\s*|\b(?:and|but|so|now)\s+)(?:(?:the\s+)?PR\s*)?\(?" + REF + \
          r"\)?(?:\s*\([^()\n]{0,80}\))?(?:'s\s+(?:CI|checks?|jobs?)|:\s*(?:CI|checks?|jobs?))?\s+"
STATE = {'a draft': r"(?:is|remains|stays)\s+(?:still\s+|now\s+)?(?:a\s+|in\s+)?draft\b", 'ready for review': r"is\s+(?:now\s+)?(?:ready for review|out of draft|marked ready)\b",
         'merged': r"(?:is|was|got|has been)\s+(?:now\s+)?merged\b", 'green': r"(?:is|are)\s+(?:now\s+|all\s+)?(?:green|passing)\b", 'red': r"(?:is|are)\s+(?:still\s+|now\s+)?(?:red|failing)\b"}
ON = r"\s+(?:on|for|of)\s+(?:PR\s*)?" + REF
CLAIMS = [(c, re.compile(rx, re.I)) for c, rx in [(c, SUBJECT + x) for c, x in STATE.items()] + [
    (c, r"\b(?:CI|checks?)" + ON + r"\s+" + STATE[c]) for c in ('green', 'red')] + [
    (c, r"\b(?:CI|checks?|jobs?)\s+" + STATE[c] + ON) for c in ('green', 'red')] + [('green', r"\ball\s+\d+\s+(?:CI\s+)?(?:checks|jobs)\s+pass(?:ed)?" + ON)]]


def state_claims(message):
    """(state, (repo or None, number), sentence) for each PR state a sentence claims, in the message's order."""
    return [(c, (m['r1'] or m['r2'], m['n1'] or m['n2']), sentence) for sentence in re.split(SENTENCE, authored(message))
            for c, rx in CLAIMS for m in rx.finditer(sentence)
            if not re.search(r"\blocal(ly)?\b", sentence, re.I) and asserted(sentence, m.end() - 1)]


def linked_repos(message): return re.findall(r'github\.com/([\w.-]+/[\w.-]+)/pull/\d+', message)
