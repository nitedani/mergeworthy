#!/usr/bin/env bash
# Tests for bin/review-context. Usage: tests/review-context.sh <repo root>
# Builds a temp git repo with a tiny TS project, changes f and removes g, and checks what review-context prints.
# Prints "case: <got> (want <want>)"; exits 0 only when every case gives what it wants.
set -u
R=$(readlink -f "$1")
TSDIR=/home/nitedani/projects/vike/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript
T=$(mktemp -d); export HOME="$T/home"; mkdir -p "$HOME"
fails=0
check() { # name want got
  echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1))
}
has() { printf '%s\n' "$OUT" | grep -qE -- "$1" && echo yes || echo no; }
section() { printf '%s\n' "$OUT" | sed -n "/^### $1/,/^### /p"; } # the output section of the symbol heading $1
G() { git -c user.name=t -c user.email=t@example.invalid "$@"; }

P="$T/proj"; mkdir -p "$P/test" "$P/node_modules"; cd "$P"
ln -s "$TSDIR" node_modules/typescript
echo node_modules > .gitignore
echo '{"compilerOptions":{"target":"ES2020","module":"ESNext","moduleResolution":"Bundler","strict":true},"include":["*.ts","test/*.ts"]}' > tsconfig.json
cat > a.ts <<'X'
export function f(x: number): number {
  return x + 1
}
export function twice(x: number): number {
  return x * 2
}
X
cat > b.ts <<'X'
import { f } from './a'
export function useF(): number {
  return f(1)
}
X
cat > test/a.test.ts <<'X'
import { f } from '../a'
export const ok = f(2) === 3
X
cat > c.ts <<'X'
export function g(): string {
  return 'g'
}
X
mkdir pkg2 && echo '{"compilerOptions":{"strict":true},"include":["*.ts"]}' > pkg2/tsconfig.json
echo 'export const v = twice(3)' > pkg2/use.ts
G init -q && G add -A && G commit -qm base
BASE=$(git rev-parse HEAD)
cat > a.ts <<'X'
export function f(x: number): number {
  return x + 2
}
export function twice(x: number): number {
  return x * 3
}
X
git rm -q c.ts
echo "// still calls g() somewhere" > c2.ts
G add -A && G commit -qm change

OUT=$("$R/bin/review-context" "$BASE" 2>&1); code=$?
check "exit code" 0 "$code"
check "f is listed" yes "$(has '^### f \(function\) — a\.ts:1')"
check "the caller b.ts is listed" yes "$(has 'b\.ts:3 in `useF`')"
check "the test caller is tagged" yes "$(has '\[test\] test/a\.test\.ts')"
check "g is listed as removed" yes "$(has '^### removed: g$')"
check "g's remaining hit is listed" yes "$(has 'c2\.ts:1')"
check "the header names the base" yes "$(has "^base $BASE")"
check "twice is listed" yes "$(has '^### twice \(function\) — a\.ts:4')"
check "pkg2/use.ts is an other mention of twice" yes "$(section 'twice ' | sed -n '/^\*\*Other mentions/,$p' | grep -qE '^- pkg2/use\.ts:1: `export const v = twice\(3\)`$' && echo yes || echo no)"
check "f (under 4 characters) gets no other mentions" no "$(section 'f (function)' | grep -q 'Other mentions' && echo yes || echo no)"
check "--max-refs 1 caps the callers" yes "$(OUT=$("$R/bin/review-context" "$BASE" --max-refs 1); has '… 1 more')"

rm node_modules/typescript
OUT=$("$R/bin/review-context" "$BASE" 2>&1); code=$?
check "no TypeScript: exit code" 0 "$code"
check "no TypeScript: message" "review-context: no TypeScript found in $(readlink -f "$P"); no context" "$OUT"

cd /; rm -rf "$T"
echo "failures: $fails"; [ "$fails" = 0 ]
