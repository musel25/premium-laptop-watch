# Premium Laptop Watch

## Intent and authorized scope

Find substantial hardware value in premium gaming or portable laptops at Best
Buy US. The owner authorized implementation, VPS deployment, a two-hour cron
job, and live tests on November 4, 2026. Repository name and implementation
choices were delegated to the implementer. Create a reviewable PR; deployment
is authorized, merging is not required.

## Requirements

- Maximum $3,000 before tax. Default minimum RAM: 32 GB (stated as a provisional
  default in chat). New and excellent open-box offers qualify.
- Pickup near ZIP 92154 or shipping to California. Do not store a street address.
- Rank gaming and portable offers separately. Use the actual configuration,
  screen, construction, CPU/GPU, upgrade limitations, and price targets. Never
  call a large list-price reduction proof of value.
- Prefer verified Best Buy offers; exclude Marketplace upgrades and unknown
  sellers. A generic "more options from" price is not an excellent open-box
  quote. Missing stock, condition, or current price cannot produce a deal alert.
- Send only to the verified private chat in the existing VPS recipient file.
  Never use the train project's multi-recipient list. No tokens, chat IDs, phone
  numbers, browser cookies, or real personal configs in this public repository.
- Persist deduplication, delivery failures, run status, and the cron job on VPS.
  An offer is sent once and may repeat only at a lower price. A return to stock
  at the same or a higher price does not trigger a repeat. A failed send
  must not mark an offer delivered. A failed data source must not look like a
  healthy run with no offers. Bound runtime and prevent overlapping runs.
- Current price targets are conservative analyst choices, not observed
  historical lows. Report that distinction. Do not promise the absolute best
  future price. Missing hardware details remain marked as unverified.

## Design

Python 3.12+, uv, Playwright Chromium for public product pages, httpx for
Telegram. No public UI. Search discovery plus a curated exact-model watchlist
provides transparent, editable price targets and hardware notes. A browser
must run on VPS independently of the owner's desktop. Use Best Buy's normal
international-store selection flow when necessary. No CAPTCHA bypass.

A private session file from the dedicated monitor account may be restored before
the first browser navigation on each run. This is needed because the tested
session loaded a product after import but did not survive a browser restart on
its own. Treat the file as a credential. Keep it outside Git and refresh it
through normal interactive sign-in when needed.

An API source can be added only with a valid owner-provided developer key.
Do not collect permanent Best Buy API price history; the API has retention
restrictions. The first release uses public page observations and keeps only
the latest report and delivery state, not a permanent price-history service.

## Deployment

Install under /home/ubuntu/premium-laptop-watch. Private state is under
~/.local/state/premium-laptop-watch. Telegram secrets remain in the existing
private file. A dedicated private config points to the verified recipient.
Use flock, a runtime timeout, bounded logs, and a managed cron block that
preserves existing jobs. Record current commit, last run, source failures,
products checked, and messages confirmed. An unavailable source sends a
rate-limited health alert, not fabricated offers.

## Acceptance evidence

Real parser fixtures; rejection of 16 GB, oversize budgets, unsupported
conditions, unknown sellers, and vague open-box minima; delivery retry and
deduplication tests; full pytest and Ruff checks; a live VPS collection;
confirmed personal Telegram delivery; a saved cron entry; a scheduled-run
equivalent using the same wrapper and environment; clean PR.
