#!/usr/bin/env python3
"""filter.py key=value… < text: prints the settings header, then the text with each
<!-- if KEY=VALUE -->…<!-- else -->…<!-- end --> block resolved (KEY!=VALUE negates). A marker alone on its line takes the line with it.
Keys and values are those of profiles/defaults.env."""
import os, re, sys

DEFAULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profiles', 'defaults.env')
SCHEMA = {k: [v, *[x.strip() for x in vals.split('|') if x.strip() != v]]  # key: values, default first
          for k, v, vals in re.findall(r'^(\w+)=(\S+)\s*# (.*)$', open(DEFAULTS).read(), re.M)}
MARKER = re.compile(r'(?P<line>^[ \t]*)?<!-- (?:if (?P<key>\w+)(?P<op>!?=)(?P<val>[\w-]+)|(?P<kw>else|end)) -->(?(line)[ \t]*\n|)', re.M)

def check(key, val, where):
    if key not in SCHEMA: sys.exit(f'{where}: unknown setting {key!r}')
    if val not in SCHEMA[key]: sys.exit(f'{where}: {key}={val!r} is not one of {"|".join(SCHEMA[key])}')

def render(text, settings, where='input'):
    out, stack, pos = [], [], 0  # stack: [condition, in else] per open block
    for m in MARKER.finditer(text):
        if all(c != e for c, e in stack): out.append(text[pos:m.start()])
        pos = m.end()
        if m['key']:
            check(m['key'], m['val'], where)
            stack.append([(settings[m['key']] == m['val']) != (m['op'] == '!='), False])
        elif not stack or (m['kw'] == 'else' and stack[-1][1]):
            sys.exit(f'{where}: stray <!-- {m["kw"]} --> at offset {m.start()}')
        elif m['kw'] == 'else': stack[-1][1] = True
        else: stack.pop()
    if stack: sys.exit(f'{where}: unclosed <!-- if --> block')
    return ''.join(out) + text[pos:]

if __name__ == '__main__':
    settings = {k: v[0] for k, v in SCHEMA.items()}
    for kv in sys.argv[1:]:
        k, _, v = kv.partition('=')
        check(k, v, 'settings'); settings[k] = v
    sys.stdout.write(f'<!-- settings: {" ".join(f"{k}={v}" for k, v in settings.items())} -->\n')
    sys.stdout.write(render(sys.stdin.read(), settings))
