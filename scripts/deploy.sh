#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
if [[ -n "$(git status --porcelain)" ]]; then
    printf 'Commit and push all project changes before deployment.\n' >&2
    exit 1
fi
revision="$(git rev-parse HEAD)"
git fetch origin feat/deal-monitor
if ! git merge-base --is-ancestor "$revision" origin/feat/deal-monitor; then
    printf 'The deployment revision is not pushed.\n' >&2
    exit 1
fi
ssh -o BatchMode=yes -o ConnectTimeout=15 my-vps bash -s -- "$revision" <<'REMOTE'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
target="$HOME/premium-laptop-watch"
if [[ ! -d "$target/.git" ]]; then
    git clone --branch feat/deal-monitor --single-branch https://github.com/musel25/premium-laptop-watch.git "$target"
fi
if [[ -n "$(git -C "$target" status --porcelain)" ]]; then
    printf 'Deployment checkout has uncommitted changes.\n' >&2
    exit 1
fi
git -C "$target" fetch origin feat/deal-monitor
git -C "$target" switch --detach "$1"
cd "$target"
uv sync --locked
uv run playwright install chromium
uv run pytest -q
uv run ruff check .
bash scripts/install-cron.sh
git rev-parse HEAD
REMOTE
