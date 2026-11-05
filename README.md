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
uv run pytest
uv run ruff check .
```

Implementation is in progress. A running schedule is verified separately from
unit tests.
