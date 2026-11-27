"""What a post shows its reader, read from markdown-it's parse (code, comments, collapsed and open <details>, quotes, own paragraphs, the
evidence section), and the words a post's checks look for, per language (post-lint, pre-bash-guard). A repo's language is the `Language: <code>` line of
its project file (~/.mergeworthy/projects/<owner>/<repo>.md); without one, or with a code not listed here, it is English."""
import os, re

ISO = r'\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?Z'  # an ISO time in UTC, the date included
_act = r'(?!(?:see|gett|find|notic|observ|hitt)ing\b)\w+'  # not an observation verb: "I'm seeing …" reports a result, not what is being done
# The first-person present forms a Hungarian status sentence opens with (I, we; definite, indefinite), with the verbal prefixes they take
# (Átnézem, Kijavítom, Letöltöm): a closed list, so a sentence opening any other way (Látom, Javítottam, Sikeresek a tesztek) goes through
# the review unless it holds the deadline.
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
        'notes': ('Note', 'Kind', 'Blocks merge', 'Next'), 'kinds': ('bug', 'limitation', 'not a regression'), 'yes': 'yes',  # Blocks merge
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
        'notes': ('Megjegyzés', 'Fajta', 'Blokkolja a beolvasztást', 'Következő'), 'kinds': ('hiba', 'korlát', 'nem regresszió'), 'yes': 'igen',
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

def project_line(repo, key):
    """The rest of the project file's `<key>:` line, bulleted or not, for a repo (owner/repo, or gitlab.com/<namespace>/<project>):
    '' when the file has no such line, None without a project file."""
    p = os.path.expanduser(f"~/.mergeworthy/projects/{re.sub(r'^gitlab[.]com/', '', repo or '')}.md")
    try: text = open(p).read() if repo else None
    except OSError: text = None
    m = text and re.search(rf'^[ \t]*(?:[-*]\s+)?{key}:[ \t]*(.*)', text, re.M)
    return None if text is None else m[1].strip() if m else ''

def language(repo):
    """The language code of a repo."""
    m = re.match(r'\w+', project_line(repo, 'Language') or '')
    return m[0] if m and m[0] in WORDS else 'en'

def template(repo, kind):
    """The headings a body keeps, as the project file's `<kind> template: <path>: `## Why`, `## How`` line quotes them (kind: 'PR' or
    'Issue'): [] with `none` or without a project file, None when the project file has no such line."""
    line = project_line(repo, f'{kind} template')
    return None if line == '' else re.findall(r'`(#{1,6} [^`]+)`', line or '')

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
                import threads_file
                named = {r for r, _ in threads_file.read(os.path.join(d, 'threads.txt'))[0]}
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

def _blocks(s):
    """s's block tokens as CommonMark renders it, read by markdown-it-py, and at(n): where its line n starts in s."""
    try: from markdown_it import MarkdownIt
    except ImportError as e:  # raised, not sys.exit: failclosed turns it into a hook's block (exit 2), where an exit 1 lets the action through
        raise ImportError("mergeworthy reads Markdown with markdown-it-py: install it (apt install python3-markdown-it, or pip install markdown-it-py)") from e
    lines = [0] + [m.end() for m in re.finditer(r'\r\n?|\n', s)]  # where markdown-it's lines start
    return MarkdownIt('commonmark').parse(s), lambda n: lines[n] if n < len(lines) else len(s)

def fence_spans(s):
    """(start, end, inner) of each fenced or indented code block in s as CommonMark renders it: the block's lines, its closing fence
    included, and the code it shows. The one place mergeworthy decides what renders as code."""
    toks, at = _blocks(s)
    return [(at(t.map[0]), at(t.map[1]), t.content) for t in toks if t.type in ('fence', 'code_block')]

def sections(s, pick):
    """(start, end) of each section of s whose heading pick('### <text>') accepts, as CommonMark renders it: from the heading to the next
    heading of the same or a higher level (a '#' line in code is no heading)."""
    toks, at = _blocks(s)
    heads = [(int(t.tag[1]), at(t.map[0]), f"{'#' * int(t.tag[1])} {toks[i + 1].content.strip()}") for i, t in enumerate(toks) if t.type == 'heading_open']
    return [(a, next((b for m, b, _ in heads[i + 1:] if m <= n), len(s))) for i, (n, a, h) in enumerate(heads) if pick(h)]

def _html_tags(s, tag):
    """(start, end) of each match of the regex tag in s that renders as an HTML tag: one in inline code, a fence or behind a backslash is
    text, and one in an HTML comment the parse reads is hidden. markdown-it-py gives inline tokens no offsets, so each match
    is marked with a processing instruction that its parse keeps next to it (a comment marker would end an enclosing comment early)."""
    found = list(re.finditer(tag, s))
    if not found: return []
    marked = ''.join(s[m0.end() if m0 else 0:m.end()] + f'<?mw-tag-{n}?>' for n, (m0, m) in enumerate(zip([None] + found, found)))
    marked += s[found[-1].end():]
    real = set()
    for t in _blocks(marked)[0]:
        if t.type == 'html_block':  # less its comments, to their --> (one unclosed to its end): a tag after a --> on that line still renders
            real |= {int(n) for n in re.findall(rf'(?:{tag})<\?mw-tag-(\d+)\?>', re.sub(r'(?s)<!--(?:.*?-->|.*)', '', t.content))}
        for a, b in zip(t.children or [], (t.children or [])[1:]):
            if a.type == b.type == 'html_inline' and re.fullmatch(tag, a.content) and (n := re.fullmatch(r'<\?mw-tag-(\d+)\?>', b.content)):
                real.add(int(n[1]))
    return [m.span() for n, m in enumerate(found) if n in real]

def _sections(s, title, heads=()):
    """The block tokens of s's section under its first top-level h3 (not in a blockquote or a list) whose plain text tokens, joined and
    stripped, equal `title` (emphasis markers, inline HTML and inline code are no text tokens, so a title written in code doesn't match),
    up to the next top-level h3 or higher heading, as a list of one; [] when no heading matches. With heads (a template's headings,
    '## <text>'), each section under that h3 or a top-level heading shown as one of heads, up to the next top-level heading."""
    tokens, _ = _blocks(s)
    heading = lambda t: t.type == 'heading_open' and t.level == 0
    shown = lambda inline: ''.join(c.content for c in inline.children if c.type == 'text').strip()
    out = []
    for i, t in enumerate(tokens):
        if heading(t) and (t.tag == 'h3' and shown(tokens[i + 1]) == title or f"{'#' * int(t.tag[1])} {shown(tokens[i + 1])}" in heads):
            end = next((j for j in range(i + 3, len(tokens)) if heading(tokens[j]) and (heads or tokens[j].tag <= 'h3')), len(tokens))
            out.append(tokens[i + 3:end])
    return out if heads else out[:1]

def without_details(s, hides=lambda tag: True):
    """s without the <details> blocks whose opening tag hides() picks (every one unless it says), each from that tag (its attributes or
    spaces included) to its own close, the blocks nested in it with it; a block it doesn't pick stays, those it picks inside it still go.
    Only tags that render as HTML count: one written as an example, in code, is text."""
    out, opened, start = [], [], 0  # opened: for each block not yet closed, whether it is hidden
    for a, b in _html_tags(s, r'<details\b(?:[^>"\']|"[^"]*"|\'[^\']*\')*>|</details\s*>'):  # a quoted value may hold a >
        if s[a + 1] != '/':
            hidden = bool(hides(s[a:b]))
            if hidden and not any(opened): out.append(s[start:a]); start = a
            opened.append(hidden)
        elif opened:
            if opened.pop() and not any(opened): start = b
    return ''.join(out) + s[start:]  # an unclosed hidden block stays in the text, from its <details> on, so it is linted and counted

def uncollapsed(s):
    """s without its collapsed <details> blocks: a <details open> block shows expanded, so only the collapsed ones are hidden from a reader."""
    return without_details(s, lambda tag: not re.search(r'\sopen(?=[\s=/>])', re.sub(r'"[^"]*"|\'[^\']*\'', '', tag)))

def _breaks(c):
    """Whether inline token c renders as a line break: a soft or hard break, or an HTML <br> (<br/>, <br />, in any case)."""
    return c.type in ('softbreak', 'hardbreak') or c.type == 'html_inline' and re.fullmatch(r'<br\s*/?>', c.content, re.I) is not None

def shows_evidence(s, title, heads=()):
    """Whether one of s's sections under the top-level h3 `title` or a template's heads (_sections), read after removing each paired
    <details> block, open or collapsed (an unclosed one stays, as without_details leaves it), holds a top-level paragraph with a line
    starting with a bold `1.`, and an output anywhere in it: a fence or code block, a Markdown image, or an HTML token that isn't a comment
    with `<img` anywhere in it (an attribute value too). A fence's contents, inline code and an HTML comment are none of these tokens."""
    def lines(inline):  # a paragraph's rendered lines, split at its line breaks, without empty text tokens or a line's leading spaces and tabs, unrendered
        line = []
        for c in inline.children:
            if _breaks(c): yield line; line = []
            elif c.type != 'text' or c.content.strip(' \t') or line and c.content: line.append((c.type, c.content))
        yield line
    img = lambda t: t.type in ('html_block', 'html_inline') and not t.content.lstrip().startswith('<!--') and re.search(r'<img\b', t.content, re.I)
    def shows(see):
        item = any(p.type == 'paragraph_open' and p.level == 0 and any(l[:3] == [('strong_open', ''), ('text', '1.'), ('strong_close', '')] for l in lines(t))
                   for p, t in zip(see, see[1:]))
        output = any(t.type in ('fence', 'code_block') or img(t) or t.type == 'inline' and any(c.type == 'image' or img(c) for c in t.children)
                     for t in see)
        return item and output
    return any(shows(see) for see in _sections(without_details(s), title, heads))

def own_blocks(s):
    """The displayed text of each paragraph and heading of s (`List **all**` reads "List all"), one string a block, outside any blockquote
    (one in a list item and a quote's lazy continuation lines are blockquote too): the words s's own author wrote."""
    shown = lambda c: '\n' if _breaks(c) else c.content if c.type in ('text', 'code_inline') else ''
    (tokens, _), quoted, out = _blocks(s), 0, []
    for prev, t in zip([None] + tokens, tokens):
        quoted += {'blockquote_open': 1, 'blockquote_close': -1}.get(t.type, 0)
        if t.type == 'inline' and not quoted and prev.type in ('paragraph_open', 'heading_open'):
            out.append(''.join(shown(c) for c in t.children))
    return out
def uncoded(s, keep=lambda block: ''):  # s with each code block replaced by keep(block)
    out, last = [], 0
    for a, b, _ in fence_spans(s): out += [s[last:a], keep(s[a:b])]; last = b
    return ''.join(out) + s[last:]
