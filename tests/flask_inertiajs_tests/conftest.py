from flask import Flask
import pytest

from flask_inertiajs.testing import InertiaClient, InertiaResponse


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-secret')
    app.test_client_class = InertiaClient
    app.response_class = InertiaResponse
    return app


@pytest.fixture
def client(app):
    return app.test_client()
