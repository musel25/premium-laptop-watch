from dataclasses import replace

import pytest

from premium_laptop_watch.core import AlertState, Model, Offer, qualify, rank


@pytest.fixture
def model():
    return Model(
        sku="6671012",
        category="portable",
        target_new_cents=150000,
        target_open_box_cents=130000,
        required_tokens=("465", "OLED"),
        strengths="3K OLED, 32 GB RAM, 1 TB SSD, thin construction",
        caveats="Integrated graphics; RAM upgradeability must be checked",
    )


@pytest.fixture
def offer():
    return Offer(
        sku="6671012",
        title="Zenbook S16 Ryzen AI 9 465 32GB OLED",
        url="https://www.bestbuy.com/product/test/TEST/sku/6671012",
        price_cents=149999,
        ram_gb=32,
        condition="new",
        seller="Best Buy",
        available=True,
        local_verified=True,
        fulfillment="Shipping shown for ZIP 92154",
        observed_at="2026-11-04T20:00:00Z",
    )


def test_real_hardware_and_price_target_qualify_without_list_discount(model, offer):
    assert qualify(offer, model) == []
    assert qualify(replace(offer, price_cents=150001), model) == [
        "above analyst target"
    ]


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"ram_gb": 16}, "less than 32 GB RAM"),
        ({"ram_gb": None}, "RAM is unknown"),
        ({"price_cents": 300001}, "over $3,000 budget"),
        ({"price_cents": None}, "price is unknown or invalid"),
        ({"price_cents": 0}, "price is unknown or invalid"),
        ({"seller": "PC Heaven"}, "seller is not Best Buy"),
        ({"seller": ""}, "seller is not Best Buy"),
        ({"condition": "good"}, "condition is not new or excellent open-box"),
        ({"condition": "unknown"}, "condition is not new or excellent open-box"),
        ({"available": False}, "offer is not in stock"),
        ({"local_verified": False}, "California fulfillment is unverified"),
        (
            {"title": "Zenbook S16 Ryzen 7 16GB IPS"},
            "configuration does not match catalog",
        ),
        ({"sku": "wrong"}, "SKU does not match catalog"),
    ],
)
def test_rejects_ineligible_or_unverified_offers(model, offer, changes, reason):
    assert reason in qualify(replace(offer, **changes), model)


def test_excellent_open_box_uses_separate_price_target(model, offer):
    assert (
        qualify(replace(offer, condition="excellent", price_cents=129999), model) == []
    )
    assert "above analyst target" in qualify(
        replace(offer, condition="excellent"), model
    )


def test_ranking_keeps_categories_separate_and_rewards_target_headroom(model, offer):
    cheaper = replace(offer, price_cents=120000)
    results = rank([offer, cheaper], {model.sku: model})
    assert [o.price_cents for o in results] == [120000, 149999]


def test_confirmed_delivery_is_deduplicated_across_restart(tmp_path, offer):
    path = tmp_path / "alerts.json"
    state = AlertState(path)
    state.observe(offer)
    assert state.should_send(offer)
    state.mark_delivered(offer, 99)
    loaded = AlertState(path)
    loaded.observe(offer)
    assert not loaded.should_send(offer)
    assert loaded.should_send(replace(offer, price_cents=140000))
    assert not loaded.should_send(replace(offer, price_cents=155000))


def test_failed_delivery_remains_eligible_after_restart(tmp_path, offer):
    path = tmp_path / "alerts.json"
    state = AlertState(path)
    state.observe(offer)
    state.save()
    assert AlertState(path).should_send(offer)


def test_stock_loss_and_return_does_not_repeat_same_or_higher_price(tmp_path, offer):
    state = AlertState(tmp_path / "alerts.json")
    state.observe(offer)
    state.mark_delivered(offer, 99)
    state.observe(replace(offer, available=False))
    assert not state.should_send(replace(offer, available=False))
    state.observe(offer)
    state.save()
    state = AlertState(tmp_path / "alerts.json")
    assert not state.should_send(offer)
    assert not state.should_send(replace(offer, price_cents=155000))
    improved = replace(offer, price_cents=140000)
    assert state.should_send(improved)
    state.mark_delivered(improved, 100)
    state.observe(improved)
    assert not state.should_send(improved)


def test_conditions_have_independent_delivery_state(tmp_path, offer):
    state = AlertState(tmp_path / "alerts.json")
    state.observe(offer)
    state.mark_delivered(offer, 1)
    excellent = replace(offer, condition="excellent", price_cents=120000)
    state.observe(excellent)
    assert state.should_send(excellent)
