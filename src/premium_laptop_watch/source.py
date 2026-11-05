"""Public-page observations. Missing evidence always fails closed."""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import Error as BrowserError
from playwright.sync_api import sync_playwright

from .core import Model, Offer


class SourceError(RuntimeError):
    pass


@dataclass
class Collection:
    offers: list[Offer]
    models: dict[str, Model]
    errors: list[str]
    pages_checked: int
    discoveries: list[dict] = field(default_factory=list)


def _products(documents: list) -> list[dict]:
    result = []
    for document in documents:
        if isinstance(document, list):
            result.extend(_products(document))
        elif isinstance(document, dict):
            if document.get("@type") == "Product":
                result.append(document)
            if "@graph" in document:
                result.extend(_products(document["@graph"]))
    return result


def _price(value, currency: str) -> int | None:
    if currency != "USD":
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            return None
        return int(amount * 100)
    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_products(
    documents: list, fulfillment: dict[str, str], observed_at: str
) -> list[Offer]:
    products = _products(documents)
    if not products:
        raise SourceError(
            "no Product structured data; source may be blocked or changed"
        )
    result = []
    for product in products:
        props = {
            p.get("name"): p.get("value", "")
            for p in product.get("additionalProperty", [])
            if isinstance(p, dict)
        }
        ram_match = re.search(
            r"^(\d+)\s*(?:gigabytes|GB)\b",
            str(props.get("System Memory (RAM)", "")),
            re.IGNORECASE,
        )
        ram = int(ram_match[1]) if ram_match else None
        offers = product.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]
        for raw in offers:
            if raw.get("@type") == "AggregateOffer" or "price" not in raw:
                continue
            sku = str(product.get("sku", ""))
            if raw.get("sku") and str(raw["sku"]) != sku:
                continue
            description = str(raw.get("description", "")).strip().lower()
            schema_condition = str(raw.get("itemCondition", "")).rsplit("/", 1)[-1]
            condition = "unknown"
            if description == "new" and schema_condition == "NewCondition":
                condition = "new"
            elif schema_condition == "UsedCondition":
                condition = {
                    "open-box excellent": "excellent",
                    "open-box good": "good",
                    "open-box fair": "fair",
                }.get(description, "unknown")
            seller = raw.get("seller", {})
            seller = seller.get("name", "") if isinstance(seller, dict) else ""
            result.append(
                Offer(
                    sku=sku,
                    title=str(product.get("name", "")),
                    url=str(product.get("url", "")),
                    price_cents=_price(raw.get("price"), raw.get("priceCurrency", "")),
                    ram_gb=ram,
                    condition=condition,
                    seller=seller,
                    available=str(raw.get("availability", "")).rsplit("/", 1)[-1]
                    == "InStock",
                    local_verified=bool(fulfillment.get(condition)),
                    fulfillment=fulfillment.get(
                        condition, "ZIP-specific shipping/pickup is unverified"
                    ),
                    observed_at=observed_at,
                )
            )
    return result


def model_for_product(product: dict, models: dict[str, Model]) -> Model | None:
    sku = str(product.get("sku", ""))
    if sku in models:
        return models[sku]
    title = product.get("name", "")
    if not sku or re.search(
        r"upgraded|desktop|refurbished|renewed", title, re.IGNORECASE
    ):
        return None
    if not re.search(r"laptop|notebook|macbook", title, re.IGNORECASE):
        return None
    if not re.search(r"OLED|mini.?LED|Liquid Retina XDR", title, re.IGNORECASE):
        return None
    cpu = re.search(
        r"(?:Ryzen (?:AI|[79])|Core Ultra [579]|M[45] (?:Pro|Max))",
        title,
        re.IGNORECASE,
    )
    if not cpu:
        return None
    category = "portable"
    tokens = [cpu[0]]
    if re.search(
        r"Legion|Zephyrus|Razer.*Blade|ROG.*(?:Strix|Flow)|OMEN MAX",
        title,
        re.IGNORECASE,
    ):
        gpu = re.search(
            r"RTX\s*(5090|5080|5070\s*Ti|5070|5060|4090|4080)\b", title, re.IGNORECASE
        )
        if not gpu:
            return None
        tier = re.sub(r"\s", "", gpu[1]).lower()
        targets = {
            "5090": (300000, 270000),
            "5080": (240000, 220000),
            "5070ti": (190000, 170000),
            "5070": (150000, 135000),
            "5060": (115000, 100000),
            "4090": (220000, 190000),
            "4080": (170000, 150000),
        }
        new, excellent = targets[tier]
        category = "gaming"
        tokens.append(gpu[0])
    elif re.search(
        r"Zenbook|Yoga.*(?:Pro|9i)|XPS|Galaxy Book.*Ultra|Surface Laptop|OmniBook Ultra|Spectre|MacBook Pro",
        title,
        re.IGNORECASE,
    ):
        new, excellent = (140000, 130000)
        if re.search(r"MacBook Pro", title, re.IGNORECASE):
            new, excellent = (240000, 210000)
        elif re.search(r"Yoga Pro 9|Galaxy Book.*Ultra", title, re.IGNORECASE):
            new, excellent = (170000, 150000)
    else:
        return None
    return Model(
        sku,
        category,
        new,
        excellent,
        tuple(tokens),
        title,
        "Automated hardware candidate. Verify GPU power, graphics memory, cooling, battery runtime, construction, ports, and RAM upgradeability. Analyst target is not a historical low.",
        product.get("url", ""),
    )


def load_catalog(path: Path) -> tuple[dict, dict[str, Model]]:
    config = json.loads(path.read_text())
    models = {}
    for row in config["models"]:
        row = dict(row)
        row["required_tokens"] = tuple(row["required_tokens"])
        models[row["sku"]] = Model(**row)
    return config, models


def us_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.bestbuy.com":
        raise SourceError("product URL must use https://www.bestbuy.com")
    params = dict(parse_qsl(parsed.query))
    params["intl"] = "nosplash"
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(params), "")
    )


SCHEMA_JS = """ss => ss.map(s => { try { return JSON.parse(s.textContent) } catch { return null } }).filter(Boolean)"""


def fulfillment_from_options(
    text: str, zip_code: str, prices: dict[str, int]
) -> dict[str, str]:
    """Require the selected condition's price and a shipping line for the ZIP."""
    result = {}
    sections = re.split(
        r"(?m)^(New|Open Box - Excellent|Open Box - Good|Open Box - Fair)\s*$", text
    )
    names = {
        "New": "new",
        "Open Box - Excellent": "excellent",
        "Open Box - Good": "good",
        "Open Box - Fair": "fair",
    }
    for i in range(1, len(sections) - 1, 2):
        condition, block = names[sections[i]], sections[i + 1]
        price = re.search(r"\$([\d,]+\.\d{2})", block)
        if not price or _price(price[1].replace(",", ""), "USD") != prices.get(
            condition
        ):
            continue
        shipping = re.search(
            r"(?m)^Get it[^\n]*\bto\s+" + re.escape(zip_code) + r"\b[^\n]*", block
        )
        if shipping:
            result[condition] = shipping[0] + "; confirm at checkout"
    return result


def collect(
    catalog_path: Path,
    browser_dir: Path,
    executable: str | None = None,
    max_products: int = 24,
    search_limit: int | None = None,
    headed: bool = False,
) -> Collection:
    config, models = load_catalog(catalog_path)
    errors, offers, discoveries = [], [], []
    pages = 0
    urls = {m.url: m.sku for m in models.values() if m.url}
    browser_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    zip_code = config["zip_code"]
    observed = datetime.now(UTC).isoformat()
    with sync_playwright() as p:
        options = {
            "headless": not headed,
            "locale": "en-US",
            "viewport": {"width": 1365, "height": 900},
        }
        if executable:
            options["executable_path"] = executable
        context = p.chromium.launch_persistent_context(str(browser_dir), **options)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(8000)

        def visit(url):
            for attempt in range(2):
                try:
                    response = page.goto(
                        us_url(url), wait_until="domcontentloaded", timeout=30000
                    )
                    if response and response.status >= 400:
                        raise SourceError(f"HTTP {response.status}")
                    return
                except BrowserError:
                    if attempt:
                        raise SourceError(
                            "browser navigation failed after two attempts"
                        ) from None
                    page.wait_for_timeout(1500)

        try:
            for query in config.get("searches", [])[:search_limit]:
                try:
                    visit(
                        "https://www.bestbuy.com/site/searchpage.jsp?"
                        + urlencode({"st": query})
                    )
                    page.locator("a.product-list-item-link").first.wait_for(
                        timeout=15000
                    )
                    page.wait_for_timeout(2500)
                    links = page.locator("a.product-list-item-link").evaluate_all(
                        "xs => xs.map(a=>({title:a.innerText,url:a.href}))"
                    )
                    if not links:
                        raise SourceError("no search product links")
                    for item in links:
                        title = item["title"]
                        if (
                            not re.search(
                                r"(?:32|36|48|64|96|128)\s*GB", title, re.IGNORECASE
                            )
                            or "upgraded" in title.lower()
                        ):
                            continue
                        url = item["url"].split("?")[0].split("#")[0]
                        if urlsplit(url).hostname == "www.bestbuy.com":
                            urls.setdefault(url, "")
                    discoveries.append({"query": query, "links_found": len(links)})
                except (SourceError, BrowserError):
                    errors.append(f"search {query}: page unavailable or changed")
            for url, expected_sku in list(urls.items())[:max_products]:
                try:
                    visit(url)
                    page.locator('script[type="application/ld+json"]').first.wait_for(
                        timeout=10000
                    )
                    documents = page.locator(
                        'script[type="application/ld+json"]'
                    ).evaluate_all(SCHEMA_JS)
                    products = _products(documents)
                    if not products:
                        raise SourceError("no product data")
                    product = next(
                        (
                            x
                            for x in products
                            if not expected_sku or str(x.get("sku")) == expected_sku
                        ),
                        None,
                    )
                    if not product:
                        raise SourceError("unexpected product identity")
                    # Delivery evidence is specific to this selected product and condition.
                    # Never infer excellent open-box availability from new-item shipping.
                    parsed = parse_products([product], {}, observed)
                    prices = {
                        o.condition: o.price_cents
                        for o in parsed
                        if o.seller == "Best Buy" and o.price_cents
                    }
                    try:
                        page.get_by_text("Open-Box", exact=True).first.click(
                            timeout=5000
                        )
                        page.wait_for_timeout(2500)
                    except BrowserError:
                        pass
                    text = page.locator("body").inner_text()
                    main = text.split("Key Accessories:")[0].split("Related Item")[0]
                    fulfillment = fulfillment_from_options(main, zip_code, prices)
                    model = model_for_product(product, models)
                    if model:
                        models[model.sku] = model
                        product_offers = parse_products(
                            [product], fulfillment, observed
                        )
                        offers.extend(product_offers)
                        if any(
                            o.available
                            and o.seller == "Best Buy"
                            and o.condition in {"new", "excellent"}
                            and o.price_cents
                            and o.price_cents <= model.target(o.condition)
                            and not o.local_verified
                            for o in product_offers
                        ):
                            errors.append(
                                f"product {model.sku}: target price found but fulfillment to {zip_code} is unverified"
                            )
                    pages += 1
                except (SourceError, BrowserError, ValueError, TypeError):
                    errors.append(
                        f"product {expected_sku or url.rsplit('/', 1)[-1]}: page unavailable, incomplete, or changed"
                    )
        finally:
            context.close()
    return Collection(offers, models, errors, pages, discoveries)
