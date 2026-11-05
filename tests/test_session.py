import json
from pathlib import Path

from playwright.sync_api import BrowserType

from premium_laptop_watch.cli import main


def test_cron_cli_restores_private_session_before_requests_on_every_run(
    tmp_path, monkeypatch
):
    fixtures = Path(__file__).parent / "fixtures"
    product = json.loads((fixtures / "zenbook-s16.json").read_text())[0]
    config = json.loads(Path("catalog.json").read_text())
    config["models"] = [m for m in config["models"] if m["sku"] == "6671012"]
    config["searches"] = []
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(config))
    session = tmp_path / "session.json"
    session.write_text(
        json.dumps(
            {
                "cookies": [
                    {
                        "name": "plw_session",
                        "value": "fixture-only",
                        "domain": "www.bestbuy.com",
                        "path": "/",
                        "expires": -1,
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax",
                    }
                ],
                "origins": [],
            }
        )
    )
    html = """<html><body><h1>Stores Near 92154</h1>
    <input aria-label="Enter city and state or zip code"><button>Update</button>
    <div class="shop-location-card"><h2>Otay Ranch</h2></div>
    <p>Otay Ranch has been marked as your store</p><button>Open-Box</button>
    <div>New</div><div>$1,499.99</div><div>Get it tomorrow to 92154</div>
    <div>Open Box - Excellent</div><div>$1,294.99</div><div>Get it tomorrow to 92154</div>
    <script type="application/ld+json">""" + json.dumps(product) + "</script></body></html>"
    launch = BrowserType.launch_persistent_context
    requests = []

    def guarded_launch(self, *args, **kwargs):
        context = launch(self, *args, **kwargs)

        def respond(route):
            authenticated = "plw_session=fixture-only" in route.request.headers.get(
                "cookie", ""
            )
            requests.append(authenticated)
            route.fulfill(
                status=200 if authenticated else 403,
                content_type="text/html",
                body=html if authenticated else "Sign in required",
            )

        context.route("**/*", respond)
        return context

    monkeypatch.setattr(BrowserType, "launch_persistent_context", guarded_launch)
    monkeypatch.setenv("LAPTOP_BROWSER_STORAGE_STATE", str(session))
    state = tmp_path / "state"
    monkeypatch.setattr(
        "sys.argv",
        ["watch", "sweep", "--dry-run", "--catalog", str(catalog), "--state-dir", str(state)],
    )
    for _ in range(2):
        assert main() == 0
        report = json.loads((state / "latest.json").read_text())
        assert report["pages_checked"] == 1
        assert report["offers_checked"] > 0
    assert requests and all(requests)


def test_invalid_private_session_fails_before_navigation_without_printing_contents(
    tmp_path, monkeypatch, capsys
):
    session = tmp_path / "session.json"
    session.write_text('{"private-canary":')
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"zip_code":"92154","searches":[],"models":[]}')
    launch = BrowserType.launch_persistent_context
    requests = []

    def offline_launch(self, *args, **kwargs):
        context = launch(self, *args, **kwargs)

        def respond(route):
            requests.append(route.request.url)
            route.fulfill(status=403, body="Sign in required")

        context.route("**/*", respond)
        return context

    monkeypatch.setattr(BrowserType, "launch_persistent_context", offline_launch)
    monkeypatch.setenv("LAPTOP_BROWSER_STORAGE_STATE", str(session))
    monkeypatch.setattr(
        "sys.argv",
        ["watch", "sweep", "--dry-run", "--catalog", str(catalog), "--state-dir", str(tmp_path / "state")],
    )
    assert main() == 2
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "collector failed: JSONDecodeError" in output
    assert "private-canary" not in output
    assert requests == []
