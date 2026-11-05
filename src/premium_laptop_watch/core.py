"""Conservative offer qualification and confirmed-delivery state."""

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Model:
    sku: str
    category: str
    target_new_cents: int
    target_open_box_cents: int
    required_tokens: tuple[str, ...]
    strengths: str
    caveats: str
    url: str = ""

    def target(self, condition: str) -> int:
        return (
            self.target_new_cents if condition == "new" else self.target_open_box_cents
        )


@dataclass(frozen=True)
class Offer:
    sku: str
    title: str
    url: str
    price_cents: int | None
    ram_gb: int | None
    condition: str
    seller: str
    available: bool
    local_verified: bool
    fulfillment: str
    observed_at: str
    stock_known: bool = True

    @property
    def key(self) -> str:
        return f"{self.sku}:{self.condition}:{self.seller}"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def qualify(offer: Offer, model: Model) -> list[str]:
    reasons = []
    if offer.sku != model.sku:
        reasons.append("SKU does not match catalog")
    if offer.ram_gb is None:
        reasons.append("RAM is unknown")
    elif offer.ram_gb < 32:
        reasons.append("less than 32 GB RAM")
    if offer.price_cents is None or offer.price_cents <= 0:
        reasons.append("price is unknown or invalid")
    elif offer.price_cents > 300000:
        reasons.append("over $3,000 budget")
    elif offer.price_cents > model.target(offer.condition):
        reasons.append("above analyst target")
    if offer.seller.strip().lower() != "best buy":
        reasons.append("seller is not Best Buy")
    if offer.condition not in {"new", "excellent"}:
        reasons.append("condition is not new or excellent open-box")
    if not offer.available:
        reasons.append("offer is not in stock")
    if not offer.local_verified:
        reasons.append("California fulfillment is unverified")
    if not all(
        _normalize(token) in _normalize(offer.title) for token in model.required_tokens
    ):
        reasons.append("configuration does not match catalog")
    return reasons


def rank(offers: list[Offer], models: dict[str, Model]) -> list[Offer]:
    eligible = [o for o in offers if o.sku in models and not qualify(o, models[o.sku])]
    return sorted(
        eligible,
        key=lambda o: (
            models[o.sku].category,
            o.price_cents / models[o.sku].target(o.condition),
            o.price_cents,
        ),
    )


def write_json(path: Path, data: dict) -> None:
    """Atomically replace a private state file without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(data, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class AlertState:
    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {"offers": {}}

    def observe(self, offer: Offer) -> None:
        entry = self.data["offers"].setdefault(offer.key, {"generation": 0})
        if offer.available and entry.get("available") is False:
            entry["generation"] += 1
        entry["available"] = offer.available

    def should_send(self, offer: Offer) -> bool:
        if not offer.available or not offer.price_cents:
            return False
        entry = self.data["offers"].get(offer.key, {})
        return (
            "delivered_price" not in entry
            or offer.price_cents < entry["delivered_price"]
            or entry.get("generation", 0) > entry.get("sent_generation", -1)
        )

    def mark_delivered(self, offer: Offer, message_id: int) -> None:
        entry = self.data["offers"].setdefault(offer.key, {"generation": 0})
        entry.update(
            delivered_price=offer.price_cents,
            sent_generation=entry.get("generation", 0),
            message_id=message_id,
        )
        self.save()

    def save(self) -> None:
        write_json(self.path, self.data)
