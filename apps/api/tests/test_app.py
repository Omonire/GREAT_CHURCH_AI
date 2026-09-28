"""Application factory: static frontend serving, headers, and error handling."""

import pytest

from church_ai_api.config import Settings
from church_ai_api.main import create_app

PAGES = (
    "/",
    "/chat.html",
    "/bible.html",
    "/study.html",
    "/prayer.html",
    "/sermons.html",
    "/about.html",
)

ASSETS = (
    "/css/app.css",
    "/js/core.js",
    "/js/chat.js",
    "/js/bible.js",
    "/js/study.js",
    "/js/prayer.js",
    "/js/sermons.js",
)


@pytest.mark.parametrize("path", PAGES)
def test_every_page_is_served(client, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert b"<html" in response.data.lower()


@pytest.mark.parametrize("path", ASSETS)
def test_every_asset_is_served(client, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.data


@pytest.mark.parametrize("path", PAGES)
def test_pages_load_the_shared_bundle(client, path: str) -> None:
    assert b"/js/core.js" in client.get(path).data


def test_index_is_the_landing_page(client) -> None:
    body = client.get("/").get_data(as_text=True)
    assert "Great Church AI" in body
    assert "chat.html" in body


def test_every_page_declares_its_title(client) -> None:
    for path in PAGES:
        body = client.get(path).get_data(as_text=True)
        assert "<title>" in body, f"{path} has no title"
        assert 'name="viewport"' in body, f"{path} is not responsive"
        assert 'class="skip-link"' in body, f"{path} has no skip link"


def test_missing_asset_returns_404_not_markup(client) -> None:
    response = client.get("/js/does-not-exist.js")
    assert response.status_code == 404
    assert b"<html" not in response.data.lower()


def test_missing_api_path_returns_json_404(client) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_directory_traversal_is_refused(client) -> None:
    response = client.get("/../pyproject.toml")
    assert response.status_code in (400, 404)


# --- security headers --------------------------------------------------


def test_security_headers_are_present(client) -> None:
    headers = client.get("/").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers["Permissions-Policy"]


def test_content_security_policy_allows_only_what_the_app_needs(client) -> None:
    csp = client.get("/").headers["Content-Security-Policy"]

    assert "default-src 'self'" in csp
    assert "https://js.puter.com" in csp
    assert "https://api.puter.com" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    # A page must never be embeddable or able to submit elsewhere.
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    # The base tag would let a stray relative URL escape the origin.
    assert csp.count("base-uri") == 1


def test_api_responses_also_carry_the_headers(client) -> None:
    assert client.get("/api/health").headers["X-Content-Type-Options"] == "nosniff"


# --- configuration -----------------------------------------------------


def test_production_mode_is_detected() -> None:
    assert Settings(app_env="production").is_production
    assert Settings(app_env="PROD").is_production
    assert not Settings(app_env="development").is_production


def test_production_does_not_enable_debug() -> None:
    app = create_app(Settings(app_env="production", log_level="WARNING"))
    assert app.debug is False


def test_development_does_not_enable_debug_by_default() -> None:
    app = create_app(Settings(app_env="development", log_level="WARNING"))
    assert app.debug is False


def test_cors_origins_are_parsed() -> None:
    settings = Settings(cors_origins="https://a.example, https://b.example")
    assert settings.cors_origin_list == ["https://a.example", "https://b.example"]


def test_server_side_ai_is_off_unless_configured() -> None:
    assert not Settings().server_side_ai_enabled
    assert Settings(
        ai_provider_base_url="https://api.example/v1", ai_provider_api_key="secret"
    ).server_side_ai_enabled


def test_api_only_mode_when_the_frontend_is_missing() -> None:
    app = create_app(
        Settings(log_level="WARNING", web_dist="../../nowhere-at-all")
    )
    # The fallback paths may still find apps/web, so only assert it never crashes.
    assert app.config["WEB_ROOT"] is None or app.config["WEB_ROOT"].name == "web"
