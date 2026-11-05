import json
from pathlib import Path

from premium_laptop_watch.source import parse_products


def fixture():
    return json.loads((Path(__file__).parent / "fixtures/zenbook-s16.json").read_text())


def test_missing_price_stays_visible_as_incomplete_instead_of_disappearing():
    documents = fixture()
    del documents[0]["offers"][0]["price"]
    offers = parse_products(documents, {}, "now")
    assert len(offers) == 4
    assert offers[0].price_cents is None


def test_missing_stock_does_not_look_like_verified_out_of_stock():
    documents = fixture()
    del documents[0]["offers"][0]["availability"]
    offer = parse_products(documents, {}, "now")[0]
    assert not offer.available
    assert not offer.stock_known
