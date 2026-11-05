# Premium Laptop Watch

Monitor premium laptop deals at Best Buy. Send Telegram alerts based on hardware
quality and price. Cover gaming and portable laptops, new and excellent open-box,
with at least 32 GB RAM and a maximum price of $3,000 before tax.

The intended deployment is a two-hour cron job on the owner's VPS. California
shipping and pickup near ZIP 92154 are in scope. Telegram credentials and the
verified personal recipient stay outside this public repository.

## Development

Use Python 3.12 or later and `uv`.

```sh
uv sync --locked
uv run playwright install chromium
uv run pytest
uv run ruff check .
```

## Run

```sh
uv run premium-laptop-watch sweep --dry-run
uv run premium-laptop-watch status
```

The VPS uses a normal Chromium window under Xvfb. `bash scripts/cron.sh` runs
the same locked command used by cron. See [the deployment runbook](docs/deployment.md).

The saved schedule is `17 */2 * * *` in the server's existing time zone. Data
access can fail independently of the scheduler. Check `status.json` and
`last-attempt.txt` before treating a run as healthy. A manual Chrome MCP check
and Telegram receipt do not establish that automatic collection is healthy.

## Value rules and coverage

[catalog.json](catalog.json) contains exact-model targets and eight discovery
queries. New products must pass conservative premium-family, modern CPU, and
display checks. Gaming targets also depend on the GPU tier. These are analyst
targets, not observed historical lows or independent performance measurements.
An unknown SKU cannot qualify on a list-price discount alone.

The collector checks a bounded selection of product pages per run. It allocates
discovery slots across queries and deduplicates product identities. It does not
claim exhaustive catalog coverage. Both gaming and portable offers receive alert
slots. Previously delivered offers do not consume those slots.

Each product, condition, and seller combination is alerted once. It can repeat
only at a lower price. Returning to stock at the same or a higher price does
not trigger another alert, even on a later day. Delivery state survives restarts
and deployments. Failed sends remain eligible for retry.

An alert needs actual RAM, a specific USD price, a Best Buy seller, an allowed
condition, stock evidence, and matching-price shipping to the selected ZIP or
pickup at the verified nearby store. Open-box offers cannot inherit new-item
delivery evidence. The owner still completes checkout and inspects the unit.

No Best Buy API key or paid data service is configured. Browser observations
provide the data. A different data source needs separate live verification.
