from playwright.sync_api import sync_playwright

from premium_laptop_watch.source import configure_location, fulfillment_from_options


def test_zip_is_set_and_otay_ranch_selection_is_verified():
    html = """<html><body><h1>Stores Near 55423</h1>
    <input aria-label="Enter city and state or zip code" value="55423">
    <button onclick="document.querySelector('h1').textContent='Stores Near '+document.querySelector('input').value">Update</button>
    <div class="shop-location-card"><h2>Otay Ranch</h2>
    <button onclick="document.querySelector('#status').textContent='Otay Ranch has been marked as your store'">Make This Your Store</button></div>
    <p id="status"></p></body></html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200, content_type="text/html", body=html
            ),
        )
        assert configure_location(page, "92154") == "Otay Ranch"
        assert page.get_by_role("heading", name="Stores Near 92154").is_visible()
        browser.close()


def test_pickup_only_requires_verified_store_and_correct_condition_price():
    text = "Open Box - Excellent\n$1,294.99\nShipping unavailable\nPick up today at Otay Ranch\n"
    assert not fulfillment_from_options(text, "92154", {"excellent": 129499})
    found = fulfillment_from_options(
        text, "92154", {"excellent": 129499}, pickup_store="Otay Ranch"
    )
    assert "excellent" in found
    assert not fulfillment_from_options(
        text, "92154", {"excellent": 129499}, pickup_store="Chula Vista"
    )
