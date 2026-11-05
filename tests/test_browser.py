import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from premium_laptop_watch.source import read_product_documents


def test_hidden_product_jsonld_is_read_without_waiting_for_visibility():
    documents = json.loads(
        (Path(__file__).parent / "fixtures/zenbook-s16.json").read_text()
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(300)
        page.set_content(
            '<html><body><h1>Product</h1><script type="application/ld+json">'
            + json.dumps(documents[0])
            + "</script></body></html>"
        )
        assert not page.locator('script[type="application/ld+json"]').is_visible()
        assert read_product_documents(page)[0]["sku"] == "6671012"
        browser.close()
