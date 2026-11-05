#!/usr/bin/env bash
set -euo pipefail
umask 077
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
state_dir="${LAPTOP_STATE_DIR:-$HOME/.local/state/premium-laptop-watch}"
mkdir -p "$state_dir"
old_table="$(mktemp)"
new_table="$(mktemp)"
error_file="$(mktemp)"
trap 'rm -f "$old_table" "$new_table" "$error_file"' EXIT
if ! LC_ALL=C crontab -l > "$old_table" 2>"$error_file"; then
    if LC_ALL=C grep -qi '^no crontab for ' "$error_file"; then
        : > "$old_table"
    else
        printf 'Could not read existing crontab; no installation was attempted.\n' >&2
        exit 1
    fi
fi
awk '
    $0 == "# BEGIN premium-laptop-watch" { if (inside) exit 2; inside=1; next }
    $0 == "# END premium-laptop-watch" { if (!inside) exit 2; inside=0; next }
    !inside { print }
    END { if (inside) exit 2 }
' "$old_table" > "$new_table"
cp "$old_table" "$state_dir/crontab-before-install.txt"
printf '\n# BEGIN premium-laptop-watch\n17 */2 * * * /bin/bash %q\n# END premium-laptop-watch\n' \
    "$project_dir/scripts/cron.sh" >> "$new_table"
crontab "$new_table"
printf 'Installed premium-laptop-watch: minute 17, every two hours in the existing server time zone.\n'
