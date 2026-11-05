# VPS operation

The owner authorized deployment and live Telegram tests on November 4, 2026.
Deploy a committed, pushed branch with `bash scripts/deploy.sh`. This creates
only the dedicated checkout and its labeled cron block. It does not merge the PR.

Requirements: `uv`, Python 3.12+, Chromium system libraries, Xvfb, `flock`,
`timeout`, git, and cron. The existing VPS already has these system tools.
The deployment downloads the browser version matching the locked Playwright.
It runs Python tests and Ruff on the VPS before installing the schedule.

## Private settings

The recipient lives at
`~/.config/premium-laptop-watch/telegram-recipient.json`, mode 0600. It was
verified by a unique `/start` message and a successful personal test. Do not
replace it with the train project's recipient list.

The token is read from `~/.config/tgvmax-watch/secrets.env` and is never printed.
The optional `~/.config/premium-laptop-watch/runtime.env` can set
`LAPTOP_BROWSER_EXECUTABLE`. It must not be committed.

Browser storage, reports, message receipts, cron logs, and state stay under
`~/.local/state/premium-laptop-watch/`. Keep this directory private. Never
commit browser cookies or state. Only the latest report is retained; this
project does not collect an API price-history database.

## Schedule and checks

The saved cron entry is `17 */2 * * *`. The existing VPS system time zone is
Europe/Paris. The frequency is every two hours; the installer does not change
the server time zone. The wrapper uses an exclusive lock and a 30-minute
timeout. It bounds the log to approximately 1 MB between runs.

```sh
ssh my-vps 'cd ~/premium-laptop-watch && bash scripts/cron.sh'
ssh my-vps 'cd ~/premium-laptop-watch && ~/.local/bin/uv run --locked premium-laptop-watch status'
ssh my-vps 'cat ~/.local/state/premium-laptop-watch/last-attempt.txt'
ssh my-vps 'tail -n 10 ~/.local/state/premium-laptop-watch/cron.log'
```

Status `ok` means the recorded source checks completed. It does not mean every
laptop at Best Buy was searched or that a purchase has been completed. `degraded`
means at least one source or delivery failed. `failed` means no usable offers
were collected. Browser blocks can recur. The service sends at most one
successful health notice per day and never calls missing evidence a deal.

Price targets are analyst judgments. The alert does not establish a historical
low or measured performance. Unknown GPU power, battery runtime, upgradeability,
condition, seller, and regional availability must remain explicit.

## Manual Chrome MCP checks

Desktop Chrome MCP works for interactive checks while the owner's browser and
this agent session are available. It is not connected to the VPS cron job.
A successful desktop search does not prove that scheduled collection works.

Manual deal alerts must use the same private `alerts.json` as the VPS job.
Acquire its `sweep.lock` before reading or changing delivery state. Qualify the
exact offer, then call `AlertState.should_send` before sending. Call
`mark_delivered` only after Telegram confirms delivery. Do not reset state or
send a deal directly through the bot without this check.

The identity is product SKU, condition, and seller. Equal or higher prices
never repeat. A lower price may trigger another alert. A return to stock alone
does not qualify for a repeat. This rule applies across days and restarts.

## Disable and restore

Remove only the block between `# BEGIN premium-laptop-watch` and
`# END premium-laptop-watch` from the owner's crontab. Preserve other jobs.
Stop only this project's running process if necessary. Preserve its private
recipient and delivery state when deploying an older pushed revision. Do not
restore an entire old crontab over newer unrelated jobs.
