import copy
import json
from pathlib import Path

import pytest

from premium_laptop_watch.source import SourceError, model_for_product, parse_products


@pytest.fixture
def product():
    return json.loads(
        (Path(__file__).parent / "fixtures/zenbook-s16.json").read_text()
    )[0]


def test_real_product_preserves_price_condition_seller_and_actual_ram(product):
    offers = parse_products(
        [product], {"new": "Shipping to 92154", "excellent": "Shipping to 92154"}, "now"
    )
    assert [(o.condition, o.price_cents) for o in offers] == [
        ("new", 149999),
        ("excellent", 129499),
        ("good", 126499),
        ("fair", 121199),
    ]
    assert all(o.ram_gb == 32 for o in offers)
    assert all(o.seller == "Best Buy" for o in offers)


def test_open_box_cannot_inherit_new_item_fulfillment(product):
    offers = parse_products([product], {"new": "Shipping to 92154"}, "now")
    assert offers[0].local_verified
    assert not offers[1].local_verified


def test_unknown_offer_condition_and_seller_are_not_inferred(product):
    product["offers"] = [
        {
            "price": 999.99,
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "description": "More options from",
        }
    ]
    offer = parse_products([product], {}, "now")[0]
    assert offer.condition == "unknown"
    assert offer.seller == ""
    assert not offer.local_verified


def test_aggregate_low_price_is_not_a_specific_offer(product):
    product["offers"] = {"@type": "AggregateOffer", "lowPrice": 999, "highPrice": 1499}
    assert parse_products([product], {}, "now") == []


def test_missing_or_foreign_currency_cannot_be_a_us_price(product):
    product["offers"][0]["priceCurrency"] = "CAD"
    assert parse_products([product], {}, "now")[0].price_cents is None


def test_unavailable_offer_is_explicit_not_silently_dropped(product):
    product["offers"][0]["availability"] = "https://schema.org/OutOfStock"
    assert not parse_products([product], {"new": "Shipping to 92154"}, "now")[
        0
    ].available


def test_marketplace_alternative_sku_does_not_inherit_primary_hardware(product):
    alternative = copy.deepcopy(product["offers"][0])
    alternative.update(sku="other", seller={"name": "PC Heaven"})
    product["offers"].append(alternative)
    assert len(parse_products([product], {}, "now")) == 4


def test_empty_or_challenge_page_is_a_source_failure():
    with pytest.raises(SourceError):
        parse_products([], {}, "now")


def test_discovery_qualifies_hardware_instead_of_discount(product):
    model = model_for_product(product, {})
    assert model.category == "portable"
    assert model.target_new_cents == 140000
    assert model.target_open_box_cents == 130000


@pytest.mark.parametrize(
    "name",
    [
        "Zenbook 14 Intel N150 32GB OLED",
        "Generic laptop Ryzen AI 9 465 32GB OLED",
        "Lenovo Upgraded Legion Pro 7 RTX 5080 32GB OLED",
        "Lenovo Legion desktop RTX 5080 32GB OLED",
    ],
)
def test_discovery_rejects_weak_unknown_or_marketplace_models(product, name):
    product["name"] = name
    assert model_for_product(product, {}) is None


def test_discovery_sets_separate_gpu_tier_price_targets(product):
    product["name"] = (
        "Lenovo Legion Pro 7 16 inch OLED Ryzen 9 9955HX3D RTX 5080 32GB Gaming Laptop"
    )
    model = model_for_product(product, {})
    assert model.category == "gaming"
    assert model.target_new_cents == 240000
    assert model.target_open_box_cents == 220000
