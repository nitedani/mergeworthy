#!/usr/bin/env python3
"""What a final message says, for stop-lint's message checks: an offer or hand-back, its GENUINE-FORK lines, its Running list,
the PRs its opening calls done, and the PR states its sentences claim. Text in, findings out: nothing here reads GitHub or T3."""
import re
from post_words import uncoded


def authored(message):
    """The message without code, quotes and quoted lines: the agent's own words."""
    # quoted words are someone else's (a user's "should I ...?", a banned phrase being discussed): not an offer
    return re.sub(r'`[^`\n]*`|"[^"\n]*"|[“„][^”\n]*”|^>[^\n]*$', ' ', uncoded(message, lambda block: ' '), flags=re.M)


# An offer, or a hand-back of work the agent can do or wait for itself ("tell me when to re-check CI", "nothing will notify me")
OFFER = (r"(when you say (go|so)|say the word|(do|would) you (want|like) me to|want me to|shall I\b|should I\b|if you want|if you'd (rather|like)|your call|"
         r"is yours to|up to you|or would you rather|which do you (want|prefer)|let me know (if|when|whether)|"
         r"(?:^[\s>*\-•]*|[.!?:;,]\s*|\b(?:or|and|just|please)\s+)(?:tell me (when|to|if|whether)|ask me (to|when|if)|ping me)|nothing (will|would|is going to) (notify|wake|tell) me|(won't|will not|doesn't|does not|can't) (notify|wake) me)\b")
# A checkable fact left unchecked ("I don't know whether", "I haven't read its source"); its paragraph showing the attempt that
# failed lets it stand: an error a tool printed (404, E404, "error:", timed out, in quotes or code too), or what the agent ran
# and how it failed ("I fetched the tarball; the registry refused it")
UNCHECKED = (r"\bI(?:\s+(?:do|did|have|could)\s*n[o']t|\s+don['’]t|['’]ve\s+not|\s+haven['’]t|\s+didn['’]t|\s+couldn['’]t|\s+could\s+not)\s+(?:yet\s+)?"
             r"(?:checked?|read|looked|inspect\w*|verif\w+|confirm\w*)\b|\bI\s+(?:do\s+not|don['’]t)\s+know\b|\bI(?:['’]m|\s+am)\s+(?:not\s+sure|unsure)\b"
             r"|\bI\s+can(?:not|['’]t)\s+tell\b(?!\s+you)|\b(?:it['’]s|it\s+is|still)\s+(?:unclear|unknown)\s+(?:whether|if)\b"
             r"|\bnem\s+(?:tudom|néztem|ellenőriztem|olvastam)\b")
PRINTED = r"\b(?:E[45]0\d|HTTP\s*[45]0\d|[45]0\d(?:\s+(?:Not\s+Found|Forbidden|Unauthorized))?(?=\W*$|[\s.,;:)])|returned\s+(?:an?\s+)?error|timed\s+out)\b|\berror:"
RAN = r"\b(?:I|we)\s+(?:tried|ran|fetched|downloaded|searched|cloned|installed|requested|called|opened|queried)\b"
FAILED = r"\b(?:fail(?:s|ed)?|refused|denied|unreachable|no\s+access|not\s+(?:public|published)|not\s+found|empty)\b"
def tried(para):
    return re.search(PRINTED, para, re.I) or re.search(RAN, para, re.I) and re.search(FAILED, para, re.I)
PREFERENCE = r"\b(?:whether|if|which|what|how)\s+(?:\w+\s+)?you(?:['’]d)?\s+(?:prefer|want|like|would\s+like|choose|pick)\b"  # theirs to say
def unchecked(message):
    message = uncoded(message, lambda block: block.replace('\n', ' '))  # a code block stays in its paragraph
    for para in re.split(r'\n\s*\n', message):
        if tried(para): continue  # the attempt may sit in quotes or code, which authored() drops
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', authored(para)):
            m = re.search(UNCHECKED, sentence, re.I)
            if m and not re.search(PREFERENCE, sentence, re.I): return m


def offer(message): return re.search(OFFER, authored(message), re.I | re.M)
def forks(text): return {re.sub(r'\W+', ' ', f).strip().lower() for f in re.findall(r'^GENUINE-FORK:(.*)$', text, re.M)}


def running_list(message):
    """What a `Running:` label or heading lists, lowercased; None when the message has none."""
    running = re.search(r'^(?:#+ *Running\b|[-*\s]*\*{0,2}Running\*{0,2}:)(.*(?:\n[ \t]*[-*\d].*)*)', message, re.M)
    return running and running.group(1).lower()


# The words that take back a claim, by where they stand (English, Hungarian); a word added here holds for the done opening and the
# PR states alike. Anything later leaves the claim standing: "ready with no issues", "done after I fixed the tests", "done as
# expected", "done, if you have questions", "Kész van?".
def words(en, hu): return re.compile(rf"\b(?:{en}|{hu})\b", re.I)
TAKE_BACK = {
    # before it in its clause: a negation or an expectation ("none is ready", "I expect it is done")
    'lead': words(r"not|no|none|nothing|neither|nor|never|nobody|\w+n['’]t|expect\w*|wait\w*", r"vár\w*"),
    # in its clause: a plan, or a Hungarian negation ("it will be ready", "kész lesz", "kész még nem vagyok")
    'clause': words(r"will|would|\w+['’]ll|going to|tomorrow|later|soon|next(?! steps?\b| to\b)",
                r"lesz\w*|lenne\w*|majd|holnap\w*|később|hamarosan|nem|nincs\w*|sincs\w*|sem|semmi\w*|senki|soha"),
    # before it in its part: a time word ("once it is ready")
    'before': words(r"once|when|until|after|before", r"amint|amikor|mihelyt|amíg|\w+-ig"),
    # in its part: a condition ("ready if CI passes")
    'part': words(r"if|unless|whether", r"ha"),
}
PART = re.compile(r"[,;:](?=\s|$)")  # not the colon of https:
CLAUSE = re.compile(r"(?=\b(?:and|but|so|és|de|ezért|viszont)\b)", re.I)


def asserted(sentence, i):
    """Whether the words at sentence[i] state something as true now: no TAKE_BACK word where it stands. A part ends at a comma,
    semicolon or colon; a clause also before a conjunction. A URL's words are no one's: each is blanked first, keeping its length."""
    sentence = re.sub(r'https?://\S*[^\s,;:.!?)\]]', lambda m: '_' * len(m[0]), sentence)  # not the punctuation after it
    before, part = PART.split(sentence[:i])[-1], PART.split(sentence[i:], 1)[0]
    lead = CLAUSE.split(before)[-1]
    where = {'lead': lead, 'clause': lead + CLAUSE.split(part)[0], 'before': before, 'part': before + part}
    return not any(rx.search(where[k]) for k, rx in TAKE_BACK.items())


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
