"""Command line entry point for the VPS job."""

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import Error as BrowserError

from .notify import Telegram
from .runner import run_sweep
from .source import Collection, SourceError, collect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sweep", "status"])
    parser.add_argument("--catalog", type=Path, default=Path("catalog.json"))
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path.home() / ".local/state/premium-laptop-watch",
    )
    parser.add_argument(
        "--recipient",
        type=Path,
        default=Path.home() / ".config/premium-laptop-watch/telegram-recipient.json",
    )
    parser.add_argument(
        "--secrets", type=Path, default=Path.home() / ".config/tgvmax-watch/secrets.env"
    )
    parser.add_argument(
        "--browser", default=os.environ.get("LAPTOP_BROWSER_EXECUTABLE")
    )
    parser.add_argument(
        "--storage-state",
        type=Path,
        default=os.environ.get("LAPTOP_BROWSER_STORAGE_STATE"),
        help="Private browser session JSON file; never commit its contents",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--max-products", type=int, default=24)
    parser.add_argument("--search-limit", type=int)
    args = parser.parse_args()
    if args.command == "status":
        path = args.state_dir / "status.json"
        print(path.read_text() if path.exists() else '{"status":"never run"}')
        return 0 if path.exists() else 1
    bot = None if args.dry_run else Telegram(args.recipient, args.secrets)
    try:
        result = collect(
            args.catalog,
            args.state_dir / "browser",
            args.browser,
            args.max_products,
            args.search_limit,
            args.headed,
            args.storage_state,
        )
    except (BrowserError, SourceError, OSError, ValueError) as exc:
        result = Collection([], {}, [f"collector failed: {type(exc).__name__}"], 0, [])
    report = run_sweep(result, args.state_dir, bot.send if bot else None, args.dry_run)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in {"offers", "discoveries"}}
        )
    )
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
