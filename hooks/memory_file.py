#!/usr/bin/env python3
"""The memory file (mergeworthy:task step 8): <work folder>/memory.md fills what the built-in compaction summary loses. Its Standing part
(rulings in force, ruled out, superseded, still intended) is carried forward until replaced; its Recent part covers the
last 24 hours. One Haiku notes what new log lines hold (`memory-prep`), merge() folds the notes in, and it records the last
log line they covered in `<!-- covered-until: <log timestamp> -->`. A root is listed in ~/.mergeworthy/memory-roots.txt and has memory.source
(`memory-prep init`): the main session's cwd, T3 thread id, session id and session-log dir."""
import datetime as dt, fcntl, glob, hashlib, json, os, re, shutil, time

COVERED = re.compile(r'<!-- covered-until: (\S+) -->')
MERGED = re.compile(r'<!-- notes-merged: (\d+) (\w+) -->')
READ = re.compile(r'read-through: (\S+)')
TS = re.compile(rb'"timestamp":"([0-9T:.\-]+Z)"')
STANDING = ('Rulings in force', 'Ruled out', 'Superseded', 'Still intended')
LIVE = ('Rulings in force', 'Ruled out', 'Still intended')  # where an item's lead names one item; Superseded keeps every replaced one
NOTE = re.compile(r'- \**(' + '|'.join(STANDING) + r'|Recent)\**(?: *\(([^)]*)\))?:\**\s*(.+?)(?: \[(replaces|done) (.+)\])?$', re.I)
DATE = re.compile(r'(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?')
KEEP = 48_000  # Standing characters memory.md keeps; older items move to the archive of their month
AIM, CAP = 6000, 7500  # digest characters: with the refresh order, under Claude Code's 10,000-character hook output limit
REG = os.path.expanduser('~/.mergeworthy/memory-roots.txt')

def roots():
    dirs = [l.strip() for l in open(REG)] if os.path.exists(REG) else []
    return [r for r in dict.fromkeys(dirs) if r and os.path.isfile(os.path.join(r, 'memory.source'))]

def source(root):
    return json.load(open(os.path.join(root, 'memory.source')))

def for_cwd(cwd, sid):
    """The work folder whose main session works in cwd: under T3 Code, when the hook's thread is the program's; else when
    session sid is one memory.source lists."""
    tid = os.environ.get('T3CODE_THREAD_ID')
    for r in roots():
        src = source(r)
        if cwd and (cwd == src['cwd'] or cwd.startswith(src['cwd'].rstrip('/') + '/')) and (
                tid == src['thread'] if tid else sid in src.get('sessions', ())):
            return r
    return None

def path(root):
    return os.path.join(root, 'memory.md')

def notes_path(root):
    return os.path.join(root, 'memory-notes.txt')

def covered(root):
    """What memory.md covers once merge() folds the notes in: the last chunk the refresh noted as read (delegate/memory-refresh.md),
    else its covered-until."""
    n = READ.findall(open(notes_path(root), errors='replace').read()) if os.path.isfile(notes_path(root)) else []
    m = COVERED.findall(open(path(root), errors='replace').read()) if os.path.isfile(path(root)) else []
    return (n or m or [''])[-1]

def stamp(ts):
    return dt.datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()

def prompt(o):
    """A user turn's prompt as the log records it: typed by the user or sent through the SDK (T3 Code), never a skill body,
    hook feedback, task notification or the built-in compaction summary."""
    return (o.get('type') == 'user' and o.get('promptSource') in ('typed', 'sdk') and not o.get('isMeta')
            and not o.get('isCompactSummary'))

def texts(o):
    c = (o.get('message') or {}).get('content')
    return [c] if isinstance(c, str) else [b.get('text', '') for b in c or [] if b.get('type') == 'text']

HANDOFF = 'Context handoff ('  # how T3 Code opens the session it hands a thread to

def orchestrator(line, tid, cwd=None):
    """A log line that marks a later session of the orchestrator: a prompt naming its thread (T3 Code's context handoff).
    A child session's log names the thread only in tool output. In the other provider's folder (cwd, the checkout memory.source
    names) only T3's handoff itself counts, in an entry of that checkout: a prompt there that only mentions the thread is
    another session's, and Antigravity's folder holds every checkout's conversations."""
    if tid not in line:
        return False
    try: o = json.loads(line)
    except ValueError: return False
    if not prompt(o): return False
    if cwd is None: return any(tid in t for t in texts(o))
    at = o.get('cwd') or ''
    return (at == cwd or at.startswith(cwd.rstrip('/') + '/')) and any(t.startswith(HANDOFF) and tid in t for t in texts(o))

def claude_logdir(cwd):
    """Where Claude Code keeps a checkout's session logs: ~/.claude/projects/<its path, every other character a dash>."""
    return os.path.expanduser('~/.claude/projects/' + re.sub(r'[^A-Za-z0-9]', '-', cwd))

def thread_logs(root, since=0.0):
    """The orchestrator's session logs modified since `since`: the session init ran in, and later ones its thread was handed
    to, under either provider T3 Code can switch the thread to (Claude Code's logs of the checkout, and hooks/agy.py's of
    Antigravity's conversations). Each file's checked position is cached, so a log is read once and a growing one only from
    where it was checked."""
    import agy
    src = source(root); cache_f = os.path.join(root, '.memory-orchestrator-logs.json')
    cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
    out, tid = [], src['thread']
    own = src['logdir']  # its provider's folder: missing, it fails, as memory is set up from it
    others = [d for d in dict.fromkeys((claude_logdir(src['cwd']), agy.DIR)) if d != own and os.path.isdir(d)]
    for p, other in [(os.path.join(d, f), d != own) for d in (own, *others) for f in os.listdir(d)]:
        f = os.path.basename(p)
        try:
            if not f.endswith('.jsonl') or os.path.getmtime(p) < since:
                continue
            pos, hit = cache.get(p, (0, f[:-len('.jsonl')] in src.get('sessions', ())))
            if not hit and os.path.getsize(p) > pos:
                with open(p, 'rb') as fh:
                    fh.seek(pos)
                    for l in fh:
                        if not l.endswith(b'\n'):
                            break
                        pos += len(l)
                        if orchestrator(l.decode(errors='replace'), tid, src['cwd'] if other else None):
                            hit = True; break
                cache[p] = (pos, hit)
        except FileNotFoundError:  # deleted since the listing: in the other provider's folder, a log its prune took (agy.py's SessionStart)
            if not other: raise
            continue
        if hit:
            out.append(p)
    json.dump(cache, open(cache_f, 'w'))
    return out

def last_ts(p):
    """A log's latest timestamp, read from its end."""
    with open(p, 'rb') as f:
        f.seek(0, 2); end = f.tell(); n = 1 << 16
        while True:
            f.seek(max(0, end - n)); found = TS.findall(f.read())
            if found or n >= end: return found[-1].decode() if found else ''
            n *= 4

def behind(root):
    """True when the orchestrator's log has lines after what memory.md covers."""
    cov = covered(root)
    since = stamp(cov) - 60 if cov else time.time() - 86400  # the first run covers the last 24 hours
    return any(last_ts(p) > cov for p in thread_logs(root, since))

def order(root, live=False):
    """The order to refresh memory.md: at session start it waits, since the context was just summarized; repeated by stop-lint
    in a live session, whose context is whole, it runs beside the work."""
    wait = ("wait for its completion without starting other work and without reading its report; then run "
            f"`memory-prep digest {root}`, read it, and resume.")
    side = (f"keep working meanwhile (your context is intact), without reading its report; when it completes, run "
            f"`memory-prep digest {root}` and read it.")
    return (f"IMPORTANT: {path(root)} is behind your session log. If you are a delegated sub-agent, ignore this. "
            + ("" if live else "Before resuming: ")
            + f"run `memory-prep prep {root}`; start ONE Haiku at high effort on the brief file it names (T3 Code: delegate_task, role research, mode async, task `Follow the brief at <its path> exactly.`); "
            + (side if live else wait))

def section(text, heading):
    m = re.search(r'^#+ *' + re.escape(heading) + r'[^\n]*\n(.*?)(?=^#+ |\Z)', text, re.M | re.S | re.I)
    return m.group(1).strip() if m else ''

def lead(line):
    """An item's identity: its bold lead, else its first 60 characters, lowercased, with punctuation as spaces."""
    m = re.match(r'[-*] \*\*(.+?)\*\*', line) or re.match(r'(?:[-*] )?(.{0,60})', line)
    return re.sub(r'\W+', ' ', m.group(1)).strip().lower()

def when(line):
    """An item's first date and time, '' when it names none."""
    m = DATE.search(line)
    return f'{m.group(1)} {m.group(2) or "00:00"}' if m else ''

def newest_first(lines):
    return sorted([l for l in lines if when(l)], key=when, reverse=True) + [l for l in lines if not when(l)]

def parse(p):
    """A memory file's lines by section; a line under any other heading counts as Recent."""
    secs, cur = {s: [] for s in STANDING + ('Recent',)}, 'Recent'
    for l in open(p, errors='replace').read().splitlines() if os.path.isfile(p) else ():
        h = re.match(r'#+ *(.*)', l)
        if h:
            cur = next((s for s in secs if h.group(1).lower().startswith(s.lower())), 'Recent')
        elif l.strip() and not COVERED.search(l) and not MERGED.search(l):
            secs[cur].append(l.rstrip())
    return secs

def render(secs, title, cov=None, merged=''):
    return (f'# {title}\n## Standing\n' + ''.join(f'### {s}\n' + ''.join(l + '\n' for l in secs[s]) for s in STANDING)
            + '## Recent\n' + ''.join(l + '\n' for l in secs['Recent']) + (f'<!-- covered-until: {cov} -->\n' if cov else '') + merged)

def write(p, text):
    if os.path.isfile(p) and open(p, errors='replace').read() == text:
        return
    with open(p + '.tmp', 'w') as f:
        f.write(text)
    os.replace(p + '.tmp', p)

def apply(mem, main, notes):
    """Applies note lines to the parsed files: a note with the lead of a live item, or tagged `[replaces <lead>]`, replaces it,
    the old one going under Superseded, in whichever file holds it; `[done <lead>]` takes a Still intended item out; a line
    already there is skipped."""
    for l in notes:
        m = NOTE.match(l.strip())
        if not m:
            if l.startswith('- '):  # a section the brief doesn't name: kept, under Recent
                m = NOTE.match('- Recent: ' + l[2:].strip())
            else:
                continue
        sec = next(s for s in STANDING + ('Recent',) if s.lower() == m.group(1).lower())
        line = '- ' + m.group(3).strip() + (f' ({m.group(2)})' if m.group(2) else '')
        op, old = (m.group(4) or '').lower(), m.group(5)
        if any(line in ls for secs in mem.values() for ls in secs.values()):
            continue
        ends = ([(lead('- ' + old), op)] if old else []) + ([(lead(line), 'replaces')] if sec != 'Recent' else [])
        for key, how in ends:
            for secs in mem.values():
                for s in LIVE if how == 'replaces' else ('Still intended',):
                    gone = [x for x in secs[s] if lead(x) == key]
                    secs[s] = [x for x in secs[s] if lead(x) != key]
                    secs['Superseded'] += gone if how == 'replaces' else []
        mem[main][sec].append(line)

def roll(mem, main, root, cov):
    """Moves memory.md's Standing past KEEP characters, oldest first, to memory-archive-<its month>.md."""
    size, month = 0, (cov or time.strftime('%Y-%m', time.gmtime()))[:7]
    for line, s in sorted(((l, s) for s in STANDING for l in mem[main][s]), key=lambda x: when(x[0]), reverse=True):
        size += len(line) + 1
        if size > KEEP:
            mem[main][s].remove(line)
            arch = os.path.join(root, f'memory-archive-{(when(line) or month)[:7]}.md')
            if arch not in mem:
                mem[arch] = parse(arch)
            mem[arch][s].append(line)

def checksum(lines):
    return hashlib.sha1('\n'.join(lines).encode()).hexdigest()[:12]

def merge(root):
    """Folds the read-through notes into memory.md (apply()), each line once: memory.md records how many lines of the notes it
    applied, `<!-- notes-merged: <lines> <their hash> -->`, so merging again changes nothing, also once the notes grew. Standing
    is kept newest first, Recent to the 24 hours up to covered-until, and old Standing items move to their month's archive
    (roll()), written before memory.md: a crash between leaves a line in both, which the next merge keeps once. The notes are
    only read: the refresh may still be appending to them, and prep resets them."""
    main, np = path(root), notes_path(root)
    if not os.path.isfile(main) and not os.path.isfile(np):
        return
    with open(os.path.join(root, '.memory.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mem, seen, archives = {}, set(), sorted(glob.glob(os.path.join(root, 'memory-archive-*.md')))
        for f in [main] + archives:
            mem[f] = parse(f)
            for s in STANDING:
                mem[f][s] = [l for l in dict.fromkeys(mem[f][s]) if l not in seen]
                seen.update(mem[f][s])
        notes = open(np, errors='replace').read().split('\n')[:-1] if os.path.isfile(np) else []  # a last line without its newline is still being written
        was = open(main, errors='replace').read() if os.path.isfile(main) else ''
        k, h = (MERGED.findall(was) or [('0', '')])[-1]
        done = int(k) if checksum(notes[:int(k)]) == h else 0  # the lines an earlier merge applied, while prep hasn't reset the notes
        if notes and COVERED.findall(was)[-1:] == READ.findall('\n'.join(notes))[-1:] and os.path.getmtime(main) > os.path.getmtime(np):
            done = len(notes)  # a refresh that wrote memory.md itself already merged them
        cov = (READ.findall('\n'.join(notes)) or COVERED.findall(was) or [''])[-1]  # covered() from the notes read here, so a line appended since waits for the next merge
        apply(mem, main, notes[done:])
        if cov:
            mem[main]['Recent'] = [l for l in mem[main]['Recent'] if not when(l) or stamp(when(l) + 'Z') >= stamp(cov) - 86400]
        roll(mem, main, root, cov)
        for f, secs in mem.items():
            for s in STANDING:
                secs[s] = newest_first(secs[s])
        text = render(mem[main], 'Memory', cov, f'<!-- notes-merged: {len(notes)} {checksum(notes)} -->\n' if notes else '')
        pre = os.path.join(root, 'memory-premerge.md')
        if was and not archives and not os.path.exists(pre) and text != was:
            shutil.copyfile(main, pre)  # the file as a model wrote it, once, before the first merge rewrites it
        for f in sorted(mem, key=lambda f: f == main):
            write(f, text if f == main else render(mem[f], 'Memory archive'))

def newest(p, heading, chars):
    """A section of memory file p, its first items up to chars: one line each, deduplicated by its lead, then where the rest is."""
    seen, body = set(), ''
    for l in section(open(p, errors='replace').read() if os.path.isfile(p) else '', heading).splitlines():
        l = l.strip()
        if not re.match(r'[-*] ', l):
            continue
        key = lead(l)
        if key in seen:
            continue
        seen.add(key); l = l if len(l) <= 240 else l[:237] + '...'
        if len(body) + len(l) > chars:
            return body + f'- ... more in {p}\n'
        body += l + '\n'
    return body

def digest(root):
    """The Standing part, cut to the cap: one line per item, newest first, deduplicated by its lead. No model call."""
    return '\n'.join(f'### {head}\n' + (newest(path(root), head, AIM // len(STANDING)) or 'none\n') for head in STANDING)[:CAP]

def notes(root):
    """What the guards grep: memory.md and every other .md under the root but drafts, briefs and the pre-merge copy."""
    return sorted(os.path.join(dp, f) for dp, dn, fs in os.walk(root) if os.path.relpath(dp, root).split(os.sep)[0] != 'drafts'
                  for f in fs if f.endswith('.md') and not f.startswith(('memory-brief', 'memory-premerge')))
