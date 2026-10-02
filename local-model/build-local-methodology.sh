#!/bin/bash
# build-local-methodology.sh <dist file> <out>: the methodology for the local model: the built dist file (settings
# already applied by its build.sh) cut where the scripts' source code starts. The scripts are installed in
# ~/.claude/mechanisms; the agent reads them there. Every rule, incident and reference stays word for word.
set -e
python3 - "$1" "$2" <<'EOF'
import re, sys
dist, out = sys.argv[1], sys.argv[2]
text = open(dist).read()
# the first "### `script`" heading followed by a ```` code fence is where build.sh appends the scripts
m = re.search(r'^### `[^`]+`\n\n````', text, re.M)
body = text[:m.start()].rstrip() if m else text.rstrip()
note = ("\n\nThe scripts' source code is installed in `~/.claude/mechanisms/` (commands linked into `~/.local/bin`); "
        f"read a script there when you need its details. This copy leaves the source out; `install-methodology` needs `{dist}`.\n")
open(out, 'w').write(body + (note if m else '\n'))
EOF
