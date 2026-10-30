"""The words a post's checks look for, per language (post-lint, pre-bash-guard), and what in a post renders as code. A repo's language is the `Language: <code>` line of
its project file (~/.mergeworthy/projects/<owner>/<repo>.md); without one, or with a code not listed here, it is English."""
import os, re

ISO = r'\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?Z'  # an ISO time in UTC, the date included
_act = r'(?!(?:see|gett|find|notic|observ|hitt)ing\b)\w+'  # not an observation verb: "I'm seeing …" reports a result, not what is being done
# The first-person present forms a Hungarian status sentence opens with (I, we; definite, indefinite), with the verbal prefixes they take
# (Átnézem, Kijavítom, Letöltöm): a closed list, so any other opener (Látom, Javítottam, Sikeresek a tesztek) goes through the review.
_HU_FORMS = """
    nézem nézek nézzük nézünk  tekintem tekintek tekintjük tekintünk  vizsgálom vizsgálok vizsgáljuk vizsgálunk
    ellenőrzöm ellenőrzök ellenőrizzük ellenőrzünk  javítom javítok javítjuk javítunk  módosítom módosítok módosítjuk módosítunk
    mergelem mergelek mergeljük mergelünk  olvasztom olvasztok olvasztjuk olvasztunk  rebaselem rebaselek rebaseljük rebaselünk
    pusholom pusholok pusholjuk pusholunk  futtatom futtatok futtatjuk futtatunk  tesztelem tesztelek teszteljük tesztelünk
    buildelem buildelek buildeljük buildelünk  építem építek építjük építünk  írom írok írjuk írunk
    frissítem frissítek frissítjük frissítünk  töltöm töltök töltjük töltünk  küldöm küldök küldjük küldünk
    várom várok várjuk várunk  dolgozom dolgozok dolgozunk  foglalkozom foglalkozok foglalkozunk  válaszolok válaszolunk
    készítem készítek készítjük készítünk  csinálom csinálok csináljuk csinálunk  keresem keresek keressük keresünk
    próbálom próbálok próbáljuk próbálunk  reprodukálom reprodukálok reprodukáljuk reprodukálunk  mérem mérek mérjük mérünk
    kezdem kezdek kezdjük kezdünk  folytatom folytatok folytatjuk folytatunk  fejezem fejezek fejezzük fejezünk
    nyitom nyitok nyitjuk nyitunk  zárom zárok zárjuk zárunk  adom adok adjuk adunk  törlöm törölök töröljük törlünk
    telepítem telepítek telepítjük telepítünk  indítom indítok indítjuk indítunk  látogatom látogatok látogatjuk látogatunk
    kapcsolom kapcsolok kapcsoljuk kapcsolunk  találkozom találkozok találkozunk  észrevételezem észrevételezek észrevételezzük észrevételezünk"""
_HU_ACT = rf"(?:át|ki|be|el|le|fel|meg|újra|rá|hozzá|vissza|össze)?(?:{'|'.join(_HU_FORMS.split())})\b"

WORDS = {
    'en': {
        'state': ('State', 'draft'),  # **State: draft** (<why>)
        'effort': ('low', 'medium', 'high', 'xhigh', 'max', 'ultra'), 'effort_word': 'effort',
        'blocks': ('Approach', 'Loop A', 'Loop B', 'Refactor pass', 'Fresh read', 'Gates'),  # converge §Evidence blocks
        'note': ('Note', 'Remark'),
        'notes': ('Note', 'Kind', 'Blocks merge', 'Next'), 'kinds': ('bug', 'limitation', 'not a regression'),
        'imposed': 'imposed by',
        'decision': 'Decision', 'picked': ('I picked (x) because …', r'\bI picked \([a-z]\)'),
        'see': 'What you should see',  # pull-request §Body
        'tracker': ('Tracking: ', 'Decisions', ('Process and requirements', 'Agreed', 'Open')),  # task §Umbrella: title, Decisions comment, its sections
        'recommend': "I recommend|recommend|I'd|I would|I propose|I suggest|I'll go with|I picked",  # a question carries our pick
        'status': {  # post-lint --kind status, and the deadline stop-lint holds a PROMISED line to (its group: the ISO time)
            'by': rf'\b(?:by|before)\s+({ISO})\b', 'by_example': 'by 2026-10-28T16:00Z',
            'on_it': ('On it',), 'then': ('Next', 'Then', 'Now', 'Meanwhile', 'After that'),
            'act': rf"(?:I|we)(?:['’]m| am|['’]re| are)\s+(?:{_act}\s+)?{_act}ing\b|(?:I|we)(?:['’]ll| will)\b", 'act_example': "'I'm rating …', 'I'll merge …'",
            'relative': r'\b(?:tomorrow|tonight|later today|in (?:about |around |roughly |under |less than )?(?:an?|\d+|a few|a couple of) (?:hours?|minutes?|days?))\b',
            'claim': r'\b\d+(?:\.\d+)?\s*(?:tests?|files?|lines?|calls?)\b|\b(?:fixed|fixes|works|passe[sd]|fail(?:s|ed|ing)?|broke|breaks|reproduced|verified|confirmed|caus(?:es|ed)|returns|regression|bug|done in|because|now that)\b|,\s*since\b',  # a reason is a claim too; "since the last pass" is time
        },
    },
    'hu': {
        'state': ('Állapot', 'piszkozat'),
        'effort': ('alacsony', 'közepes', 'magas', 'nagyon magas', 'maximális', 'ultra'), 'effort_word': 'erőfeszítés',
        'blocks': ('Megközelítés', 'Loop A', 'Loop B', 'Refaktorálás', 'Friss olvasás', 'Ellenőrzések'),
        'note': ('Megjegyzés',),
        'notes': ('Megjegyzés', 'Fajta', 'Blokkolja a beolvasztást', 'Következő'), 'kinds': ('hiba', 'korlát', 'nem regresszió'),
        'imposed': 'szabja meg',
        'decision': 'Döntés', 'picked': ('Az (x) lehetőséget választottam, mert …', r'\([a-z]\)[^\n]*\bválasztottam\b'),
        'see': 'Amit látni fogsz',
        'tracker': ('Követés: ', 'Döntések', ('Folyamat és követelmények', 'Elfogadva', 'Nyitott')),
        'recommend': 'javaslom|javasolnám|választanám|választottam',
        'status': {
            'by': rf'\b({ISO})(?:-ig\b|\s+előtt\b)', 'by_example': '2026-10-28T16:00Z-ig',
            'on_it': ('Rajta vagyok',), 'then': ('Most', 'Majd', 'Aztán', 'Utána', 'Ezután', 'Közben'),
            'act': _HU_ACT, 'act_example': "'Átnézem …', 'Mergelem …'",
            'relative': r'\b(?:holnap\w*|ma este|később)\b|\b(?:egy|fél|pár|néhány|\d+)\s+(?:órá?|perc|nap)\w*\s+(?:múlva|belül)\b',
            'claim': r'\b\d+(?:\.\d+)?\s*(?:teszt|fájl|sor|hívás)\w*|\b(?:javíto?tt\w*|javítva|működ\w*|átm(?:ent|egy)\w*|elbuk\w*|hib\w*|reprodukált\w*|ellenőriz(?:tem|tük|ve)|megerősített\w*|okoz(?:za|ta)|regresszió\w*|mert|mivel)\b',
        },
    },
}

def language(repo):
    """The language code of a repo (owner/repo, or gitlab.com/<namespace>/<project>)."""
    p = os.path.expanduser(f"~/.mergeworthy/projects/{re.sub(r'^gitlab[.]com/', '', repo or '')}.md")
    try: m = re.search(r'^\s*(?:[-*]\s+)?Language:\s*(\w+)', open(p).read(), re.M) if repo else None
    except OSError: m = None
    return m[1] if m and m[1] in WORDS else 'en'

def words(repo):
    return WORDS[language(repo)]

def status_words(repo):
    """What post-lint's status checks look for: the repo's language's words and English's, which a status post may use in any repo;
    the examples its findings quote are the repo's language's."""
    ws = [WORDS[language(repo)]['status'], WORDS['en']['status']]
    any_of = lambda k: '|'.join(dict.fromkeys(f'(?:{w[k]})' for w in ws))
    every = lambda k: alt(dict.fromkeys(x for w in ws for x in w[k]))
    return {**{k: any_of(k) for k in ('by', 'act', 'relative', 'claim')}, 'lead': rf"(?:(?:{every('on_it')})\b[\s:,.!]*)?(?:(?:{every('then')}),?\s+)?",
            'by_example': ws[0]['by_example'], 'act_example': ws[0]['act_example']}

def draft_repo(path):
    """(repo, why not) for a draft linted without --repo: its watch dir's repo (the first folder above the draft holding repos.txt; when
    that lists several, the one threads.txt names), else the git origin of the cwd."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        f = os.path.join(d, 'repos.txt')
        if os.path.isfile(f):
            repos = list(dict.fromkeys(l.split()[0] for l in open(f, errors='replace') if l.strip()))
            if len(repos) > 1:
                t = os.path.join(d, 'threads.txt')
                named = {l.split()[0] for l in open(t, errors='replace') if l.strip()} if os.path.isfile(t) else set()
                repos = [r for r in repos if r in named] or repos
            if len(repos) > 1:
                return None, f"{f} lists {', '.join(repos)} and threads.txt doesn't single one out: pass --repo <owner/repo>, so the checks use its language"
            if repos: return repos[0], None
            break
        if os.path.dirname(d) == d: break
        d = os.path.dirname(d)
    import subprocess
    url = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
    m = re.search(r'(gitlab\.com)[:/](.+?)(?:\.git)?$|github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$', url)
    return (m and ('gitlab.com/' + m[2] if m[1] else m[3])), None

def alt(items):
    """A regex alternation of literal words."""
    return '|'.join(re.escape(w) for w in items)

def state_line(w):
    """The draft State line: **<label>: <word>** (<why>)."""
    return re.compile(rf'^\*\*{re.escape(w["state"][0])}: {re.escape(w["state"][1])}\*\* \(.*\S.*\)$')

def fence_spans(s):
    """(start, end, inner) of each fenced or indented code block in s as CommonMark renders it, read by markdown-it-py: the block's lines,
    its closing fence included, and the code it shows. The one place mergeworthy decides what renders as code."""
    try: from markdown_it import MarkdownIt
    except ImportError as e:  # raised, not sys.exit: failclosed turns it into a hook's block (exit 2), where an exit 1 lets the action through
        raise ImportError("mergeworthy reads Markdown with markdown-it-py: install it (apt install python3-markdown-it, or pip install markdown-it-py)") from e
    lines = [0] + [m.end() for m in re.finditer(r'\r\n?|\n', s)]  # where markdown-it's lines start
    at = lambda n: lines[n] if n < len(lines) else len(s)
    return [(at(t.map[0]), at(t.map[1]), t.content) for t in MarkdownIt('commonmark').parse(s) if t.type in ('fence', 'code_block')]
def uncoded(s, keep=lambda block: ''):  # s with each code block replaced by keep(block)
    out, last = [], 0
    for a, b, _ in fence_spans(s): out += [s[last:a], keep(s[a:b])]; last = b
    return ''.join(out) + s[last:]
