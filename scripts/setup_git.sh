#!/usr/bin/env sh
# Usage: sh scripts/setup_git.sh https://github.com/<you>/resourceleak.git
set -e
[ -d .git ] || git init -b main
git add -A && git commit -m "feat: ResourceLeak AI working demo" 2>/dev/null || true
[ -n "$1" ] && { git remote add origin "$1" 2>/dev/null || git remote set-url origin "$1"; git push -u origin main; }
