from flask import Flask
import pytest

from flask_inertiajs import Inertia
from flask_inertiajs.testing import InertiaClient, InertiaResponse


# Tests depend on this being function-scoped. Don't make it session-scoped without noting the
# ramifications.
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-secret')
    app.test_client_class = InertiaClient
    app.response_class = InertiaResponse
    Inertia(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()
