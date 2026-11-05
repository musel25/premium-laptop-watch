from premium_laptop_watch.source import select_product_urls


def test_discovery_budget_is_shared_between_searches_and_duplicate_urls():
    catalog = {"https://www.bestbuy.com/product/known/JJKNOWN/sku/123": "123"}
    games = [f"https://www.bestbuy.com/product/game{i}/JJGAME{i}" for i in range(10)]
    portable = ["https://www.bestbuy.com/product/portable/JJPORTABLE"]
    duplicate = ["https://www.bestbuy.com/product/other-name/JJKNOWN"]
    selected = select_product_urls(catalog, [games, portable, duplicate], 4)
    assert selected == [
        ("https://www.bestbuy.com/product/known/JJKNOWN/sku/123", "123"),
        (games[0], ""),
        (portable[0], ""),
        (games[1], ""),
    ]
