# Review and verification

The implementation received a fresh, read-only whole-branch review of
757bfc7..782991f. The reviewer used local fixtures, a real Chromium DOM, temporary
state, and a controlled crontab executable. It did not inspect private secrets
or send messages.

The review found a critical wait for a hidden JSON-LD script to become visible.
An actual browser regression reproduced the timeout before the fix. The
collector now waits for the script to attach to the DOM.

The fix pass also addressed:

- Alert starvation after five previously delivered offers. Deduplication now
  happens before the cap, and categories share delivery slots.
- Incomplete product observations. Missing offers are source errors. Missing
  price, RAM, seller, condition, and stock evidence remain visible as incomplete.
- Region setup. The collector sets ZIP 92154 through the store locator and
  verifies the nearby Otay Ranch store. Specific-price pickup evidence is
  supported, alongside condition-specific ZIP shipping evidence.
- Crontab read errors. The installer aborts unless a failed read specifically
  reports that no crontab exists. It preserves unrelated jobs.
- Discovery budget bias. This was regraded as important because both laptop
  categories are requested. Product identities are deduplicated and queries
  receive slots in turn.

All regressions failed before their fixes. The full suite passed 56 tests on
the local machine and VPS at 8f1eea8. Ruff also passed on both machines. Tests
include a real offline browser; they do not prove live Best Buy access.

## Decisions and limits

- Work is in a new repository and topic branch. No unrelated checkout is
  changed. Cost of this choice: a separate checkout to maintain.
- Public-page Chromium is the first source. Best Buy's international US-store
  selection parameter is used. Cost: browser access can fail or change.
- Live deployment and scheduled execution were verified separately from review.
  A failed data check remains failed even if cron ran. Cost: missing deals when
  the remote site cannot be read.
- The recipient stays outside the repository. Its unique start code, private
  chat, and actual Telegram receipt were verified by the implementer. Cost:
  private runtime configuration is not covered by the code review.
- Hardware targets are analyst judgments, with explicit limitations. No
  historical-low or measured-benchmark claims are made. Cost: the thresholds
  can miss an attractive offer or need adjustment as the market changes.

One minor remains deferred: failed health-notice delivery is not stored in a
separate telemetry field. The failed source status is retained, and the notice
is retried on later runs until delivery succeeds.

## Live acceptance result

Cron executed the revised wrapper at 2026-11-05 02:56:01 UTC. The source check
failed at 02:56:05 UTC. A full non-dry wrapper run then executed from 02:58:17
through 02:59:46 UTC. It attempted the eight configured searches and 24 product
pages. No usable product observations were collected. The failure status was
saved, and Telegram confirmed the rate-limited health notice. The temporary
minute-by-minute smoke cron block was removed. The ordinary two-hour job remains.

Desktop Chrome MCP successfully verified two current excellent open-box offers
with their own shipping options to ZIP 92154: Zenbook S16 SKU 6671012 at
$1,294.99 and ROG Flow Z13 SKU 6619196 at $2,086.99. These are manual browser
observations. They do not prove that the VPS collector is healthy.

Automatic collection remains operationally blocked by VPS browser access. The
PR stays in draft. A stable independent data source or an explicitly selected
desktop Chrome connection is still required. No API key or paid service has
been configured.

## Repeat-alert correction

The owner requested no repeated deal unless the price improves. Investigation
found that the existing stock-return rule could repeat an unchanged or higher
price. The regression failed on that case before the correction. The updated
rule preserves delivery retries and separate product conditions, but permits a
repeat only below the last confirmed delivery price. The regression includes
a restart and a lower-price follow-up. All 56 tests and Ruff passed locally.
Manual Chrome alerts must share the VPS delivery state and lock.

## Private session restore

Revision `0fbf8ad` adds an optional private storage-state file, restored before
the first navigation on every sweep. The two new real-browser regressions
failed before implementation. They check cookie-gated requests across two CLI
runs and invalid JSON without navigation or secret disclosure on either output
stream. All 58 tests and Ruff passed locally and on the VPS. A separate
read-only review found no Critical or Important issues.

The dedicated monitor profile was opened locally in standard Chrome. After
normal Best Buy email verification, a product page loaded. Best Buy-only state
was exported privately. One headed VPS import test returned HTTP 200 with the
correct product data, but access failed again after restart and in later tests.
Loading the file on every run is deployed, but the real cron wrapper's focused
dry run at `2026-11-05T04:38:20Z` still collected zero pages and offers. Standard
Google Chrome 157 on the ARM VPS also returned the HTTP/2 error.

This is not a reliable source-access fix. Automatic collection remains blocked,
and the PR remains in draft. No live-source success is inferred from unit tests
or the one successful import probe. The Best Buy API key is still pending its
separate approval process.
