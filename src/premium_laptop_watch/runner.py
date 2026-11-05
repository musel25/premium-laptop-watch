"""One sweep, private reports, confirmed delivery, and bounded health alerts."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .core import AlertState, qualify, rank, write_json
from .notify import DeliveryError
from .source import Collection


def alert_text(offer, model) -> str:
    condition = "New" if offer.condition == "new" else "Open-box excellent"
    return (
        f"Premium laptop target reached | {model.category}\n\n{offer.title}\n"
        f"${offer.price_cents / 100:,.2f} before tax | {condition} | Best Buy\n\n"
        f"Hardware: {model.strengths}\n"
        f"Why flagged: at or below ${model.target(offer.condition) / 100:,.0f} analyst target for this configuration. This is not a verified historical low.\n"
        f"Limits: {model.caveats}\n"
        f"Availability: {offer.fulfillment}\nChecked: {offer.observed_at}\n\n{offer.url}"
    )


def run_sweep(result: Collection, state_dir: Path, send, dry_run: bool = False) -> dict:
    state = AlertState(state_dir / "alerts.json")
    for offer in result.offers:
        state.observe(offer)
    qualified = rank(result.offers, result.models)
    delivery_errors = []
    sent = 0
    if not dry_run:
        for offer in qualified[:5]:
            if not state.should_send(offer):
                continue
            try:
                receipt = send(alert_text(offer, result.models[offer.sku]))
                state.mark_delivered(offer, receipt)
                sent += 1
            except DeliveryError:
                delivery_errors.append(f"{offer.sku}: Telegram delivery unconfirmed")
        state.save()
    status = "ok"
    if result.errors or delivery_errors:
        status = "degraded"
    if not result.pages_checked or not result.offers:
        status = "failed"
    now = datetime.now(UTC)
    report = {
        "checked_at": now.isoformat(),
        "status": status,
        "dry_run": dry_run,
        "pages_checked": result.pages_checked,
        "offers_checked": len(result.offers),
        "qualified_offers": len(qualified),
        "alerts_sent": sent,
        "source_errors": result.errors,
        "delivery_errors": delivery_errors,
        "discoveries": result.discoveries,
        "offers": [
            dict(asdict(o), rejections=qualify(o, result.models[o.sku]))
            for o in result.offers
            if o.sku in result.models
        ],
    }
    write_json(state_dir / "latest.json", report)
    write_json(
        state_dir / "status.json",
        {k: v for k, v in report.items() if k not in {"offers", "discoveries"}},
    )
    # Health alerts have their own receipt and daily limit. Never confuse them
    # with deal messages, and never broadcast to the train project's contacts.
    if not dry_run and status != "ok":
        health_path = state_dir / "health.json"
        health = json.loads(health_path.read_text()) if health_path.exists() else {}
        if now.timestamp() - health.get("last_sent", 0) >= 86400:
            try:
                receipt = send(
                    f"Premium Laptop Watch health: {status}.\nChecked {result.pages_checked} product pages and {len(result.offers)} offers.\nSome checks could not be completed. No unverified offer was sent as a deal.\nSource errors: {len(result.errors)}. Delivery errors: {len(delivery_errors)}.\nThe two-hour job will retry. This is a health notice, not a laptop deal."
                )
                write_json(
                    health_path, {"last_sent": now.timestamp(), "message_id": receipt}
                )
            except DeliveryError:
                pass
    return report
