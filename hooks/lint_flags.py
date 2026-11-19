"""The post-lint flags a draft last passed with, saved in <draft>.lint for gate-pass to re-run and the hooks to read its --kind.
`lint_flags.py <draft>` prints them NUL-separated, for gate-pass."""
import json, sys


def save(draft, flags):
    with open(draft + '.lint', 'w') as f: json.dump(flags, f)


def load(draft):
    """The saved flags: a JSON array, or a record from before them (it starts with `--`) split on whitespace. None without a record."""
    try: saved = open(draft + '.lint').read()
    except OSError: return None
    return json.loads(saved) if saved.lstrip().startswith('[') else saved.split()


if __name__ == '__main__':
    if (flags := load(sys.argv[1])) is None: sys.exit(f"can't read {sys.argv[1]}.lint")
    sys.stdout.write(''.join(f + '\0' for f in flags))
