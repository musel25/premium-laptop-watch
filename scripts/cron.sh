#!/usr/bin/env bash
set -euo pipefail
umask 077
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
state_dir="${LAPTOP_STATE_DIR:-$HOME/.local/state/premium-laptop-watch}"
mkdir -p "$state_dir"
exec 9>"$state_dir/sweep.lock"
flock -n 9 || exit 0
export PATH="$HOME/.local/bin:$PATH"
runtime_env="$HOME/.config/premium-laptop-watch/runtime.env"
if [[ -f "$runtime_env" ]]; then
    # This private file contains only this service's runtime settings.
    source "$runtime_env"
fi
cd "$project_dir"
log_file="$state_dir/cron.log"
if [[ -f "$log_file" ]] && (( $(wc -c < "$log_file") > 1048576 )); then
    tail -c 524288 "$log_file" > "$log_file.next"
    mv "$log_file.next" "$log_file"
fi
printf 'started_utc=%s\ncommit=%s\n' "$(date -u +%FT%TZ)" "$(git rev-parse HEAD)" > "$state_dir/last-attempt.txt"
trap 'job_exit=$?; printf "finished_utc=%s\nexit=%s\n" "$(date -u +%FT%TZ)" "$job_exit" >> "$state_dir/last-attempt.txt"' EXIT
timeout --signal=TERM --kill-after=30 1800 \
    xvfb-run -a uv run --locked premium-laptop-watch sweep --headed \
    --state-dir "$state_dir" "$@" >> "$log_file" 2>&1
