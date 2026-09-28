import pytest

from church_ai_api.config import Settings
from church_ai_api.main import create_app


@pytest.fixture(scope="session")
def app():
    return create_app(Settings(app_env="development", log_level="WARNING"))


@pytest.fixture()
def client(app):
    return app.test_client()
