import json
from dataclasses import replace

import httpx
import pytest

from premium_laptop_watch.core import Model, Offer
from premium_laptop_watch.notify import DeliveryError, Telegram
from premium_laptop_watch.runner import run_sweep
from premium_laptop_watch.source import Collection


def sample():
    model = Model(
        "sku1",
        "portable",
        140000,
        130000,
        ("OLED",),
        "32 GB; OLED",
        "Check RAM upgrades",
    )
    offer = Offer(
        "sku1",
        "Premium 32GB OLED laptop",
        "https://www.bestbuy.com/product/test/TEST",
        129999,
        32,
        "new",
        "Best Buy",
        True,
        True,
        "Shipping to 92154",
        "now",
    )
    return model, offer


def test_telegram_uses_one_verified_private_recipient(tmp_path):
    recipient = tmp_path / "recipient.json"
    recipient.write_text(
        json.dumps(
            {
                "chat_id": 42,
                "bot_username": "gusviado_bot",
                "verification_code": "premium_laptop_test_a4e9",
                "test_message_id": 1,
            }
        )
    )
    secrets = tmp_path / "secrets.env"
    secrets.write_text(
        "TGVMAX_TELEGRAM_TOKEN=private-token\nTGVMAX_TELEGRAM_CHAT_IDS=42,99,101\n"
    )
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"message_id": 5, "chat": {"id": 42, "type": "private"}},
            },
        )

    bot = Telegram(recipient, secrets, transport=httpx.MockTransport(handler))
    assert bot.send("Test") == 5
    assert requests == [
        {"chat_id": 42, "text": "Test", "link_preview_options": {"is_disabled": True}}
    ]


def test_telegram_timeout_is_safe_and_not_successful(tmp_path):
    recipient = tmp_path / "recipient.json"
    recipient.write_text(
        json.dumps(
            {
                "chat_id": 42,
                "verification_code": "premium_laptop_test_a4e9",
                "test_message_id": 1,
            }
        )
    )
    secrets = tmp_path / "secrets.env"
    secrets.write_text("TGVMAX_TELEGRAM_TOKEN=secret-test-token\n")

    def handler(request):
        raise httpx.ReadTimeout(str(request.url))

    bot = Telegram(recipient, secrets, transport=httpx.MockTransport(handler))
    with pytest.raises(DeliveryError) as exc:
        bot.send("Test")
    assert "secret-test-token" not in str(exc.value)


def test_failed_alert_is_retried_then_deduplicated(tmp_path):
    model, offer = sample()
    result = Collection([offer], {model.sku: model}, [], 1, [])
    calls = []

    def fail(text):
        calls.append(text)
        raise DeliveryError("test failure")

    first = run_sweep(result, tmp_path, fail)
    assert first["status"] == "degraded"
    assert first["alerts_sent"] == 0
    second = run_sweep(result, tmp_path, lambda text: 10)
    assert second["alerts_sent"] == 1
    assert (
        run_sweep(result, tmp_path, lambda text: pytest.fail("duplicate alert"))[
            "alerts_sent"
        ]
        == 0
    )


def test_partial_source_failure_is_degraded_and_saved(tmp_path):
    model, offer = sample()
    result = Collection(
        [offer], {model.sku: model}, ["sku2: source unavailable"], 1, []
    )
    status = run_sweep(result, tmp_path, lambda text: 10)
    assert status["status"] == "degraded"
    assert json.loads((tmp_path / "status.json").read_text())["source_errors"] == [
        "sku2: source unavailable"
    ]


def test_empty_collection_is_never_healthy(tmp_path):
    result = Collection([], {}, [], 0, [])
    assert run_sweep(result, tmp_path, lambda text: 10)["status"] == "failed"


def test_dry_run_does_not_change_delivery_state(tmp_path):
    model, offer = sample()
    result = Collection([offer], {model.sku: model}, [], 1, [])
    assert run_sweep(result, tmp_path, None, dry_run=True)["alerts_sent"] == 0
    assert not (tmp_path / "alerts.json").exists()
    assert run_sweep(result, tmp_path, lambda text: 10)["alerts_sent"] == 1


def test_unverified_regional_stock_is_reported_but_not_alerted(tmp_path):
    model, offer = sample()
    result = Collection(
        [replace(offer, local_verified=False)], {model.sku: model}, [], 1, []
    )
    assert (
        run_sweep(result, tmp_path, lambda text: pytest.fail("unverified deal"))[
            "qualified_offers"
        ]
        == 0
    )
