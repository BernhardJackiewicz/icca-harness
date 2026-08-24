#!/usr/bin/env bash
# Installs the red-proof skill, gate CLI and PreToolUse hooks for Claude Code.
# Idempotent: safe to run again after pulling a new version.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANG_CHOICE="${SKILL_LANG:-en}"
while [ $# -gt 0 ]; do
  case "$1" in
    --lang) LANG_CHOICE="$2"; shift 2 ;;
    --lang=*) LANG_CHOICE="${1#*=}"; shift ;;
    -h|--help)
      echo "usage: ./install.sh [--lang en|de]"
      echo "  en (default)  install the English skill body"
      echo "  de            install the German original"
      exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done
case "$LANG_CHOICE" in
  en) SKILL_SRC="$SRC/skills/icca-harness/SKILL.md" ;;
  de) SKILL_SRC="$SRC/skills/icca-harness/SKILL.de.md" ;;
  *)  echo "error: --lang must be en or de (got '$LANG_CHOICE')" >&2; exit 2 ;;
esac
[ -f "$SKILL_SRC" ] || { echo "error: missing $SKILL_SRC" >&2; exit 1; }
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_DIR/skills/icca-harness"
GATE_DIR="$CLAUDE_DIR/red-proof"
SETTINGS="$CLAUDE_DIR/settings.json"

command -v python3 >/dev/null || { echo "error: python3 not found" >&2; exit 1; }
command -v git >/dev/null || { echo "error: git not found" >&2; exit 1; }

mkdir -p "$SKILL_DIR" "$GATE_DIR" "$CLAUDE_DIR/skills"
cp "$SKILL_SRC" "$SKILL_DIR/SKILL.md"
cp "$SRC/bin/red_proof.py" "$GATE_DIR/red_proof.py"
chmod +x "$GATE_DIR/red_proof.py"
echo "installed skill:    $SKILL_DIR/SKILL.md  (language: $LANG_CHOICE)"
echo "installed gate CLI: $GATE_DIR/red_proof.py"

if [ ! -f "$SETTINGS" ]; then
  printf '{}\n' > "$SETTINGS"
  echo "created:            $SETTINGS"
fi

GATE_CMD="python3 $GATE_DIR/red_proof.py hook"
python3 - "$SETTINGS" "$GATE_CMD" <<'PY'
import json, shutil, sys

settings_path, gate_cmd = sys.argv[1], sys.argv[2]
with open(settings_path) as f:
    text = f.read().strip() or "{}"
try:
    settings = json.loads(text)
except ValueError as e:
    sys.exit("error: %s is not valid JSON (%s). Merge the hooks manually "
             "from examples/settings-hooks.json." % (settings_path, e))

wanted = [
    ("Edit|Write", gate_cmd + " edit", "red-proof gate: edit check"),
    ("Bash", gate_cmd + " bash", "red-proof gate: commit check"),
]

hooks = settings.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])
if not isinstance(pre, list):
    sys.exit("error: hooks.PreToolUse in %s is not a list" % settings_path)

added = 0
for matcher, command, status in wanted:
    group = next((g for g in pre if isinstance(g, dict)
                  and g.get("matcher") == matcher), None)
    if group is None:
        group = {"matcher": matcher, "hooks": []}
        pre.append(group)
    entries = group.setdefault("hooks", [])
    if any(isinstance(h, dict) and h.get("command") == command for h in entries):
        continue
    entries.append({"type": "command", "command": command,
                    "timeout": 20, "statusMessage": status})
    added += 1

if added:
    shutil.copyfile(settings_path, settings_path + ".red-proof.bak")
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print("merged %d hook(s) into %s (backup: %s.red-proof.bak)"
          % (added, settings_path, settings_path))
else:
    print("hooks already present in %s, unchanged" % settings_path)
PY

cat <<EOF

Remaining manual step: append the block in
  $SRC/examples/CLAUDE.md.snippet
to your global $CLAUDE_DIR/CLAUDE.md, so the skill is loaded before the
first production-code change instead of after it.

Verify in a fresh terminal: /skills lists icca-harness,
/hooks shows both PreToolUse gates.
EOF
