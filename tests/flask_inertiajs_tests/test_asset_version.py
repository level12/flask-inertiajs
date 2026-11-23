from pathlib import Path

from jinja2 import FileSystemLoader
import pytest

from flask_inertiajs.asset_version import current_asset_version


class TestCurrentAssetVersion:
    @pytest.fixture(autouse=True)
    def template(self, app, tmp_path):
        template = tmp_path / 'bridge.html'
        template.write_text('<title>USS Enterprise — {{ captain }}</title>', encoding='utf-8')
        app.jinja_loader = FileSystemLoader(tmp_path)
        app.config['INERTIA_TEMPLATE'] = 'bridge.html'
        return template

    @pytest.mark.parametrize('manifest_setting', [None, '', 'enterprise-manifest.json'])
    def test_manifest_requires_path(self, app, manifest_setting):
        app.config['INERTIA_VITE_MANIFEST_PATH'] = manifest_setting

        with app.app_context(), pytest.raises(TypeError, match='INERTIA_VITE_MANIFEST_PATH'):
            current_asset_version()

    def test_manifest_requires_absolute_path(self, app):
        app.config['INERTIA_VITE_MANIFEST_PATH'] = Path('enterprise-manifest.json')

        with app.app_context(), pytest.raises(ValueError, match='absolute'):
            current_asset_version()

    def test_template_and_manifest(self, app, tmp_path, template):
        manifest_bytes = b'{"bridge.ts": {"file": "assets/enterprise.js"}}\n'
        manifest = tmp_path / 'manifest.json'
        manifest.write_bytes(manifest_bytes)
        app.config['INERTIA_VITE_MANIFEST_PATH'] = manifest

        with app.app_context():
            original = current_asset_version()
            assert current_asset_version() == original

            manifest.write_bytes(b'{"bridge.ts": {"file": "assets/stargazer.js"}}\n')
            changed = current_asset_version()
            assert changed != original
            assert current_asset_version() == changed
            manifest.write_bytes(manifest_bytes)
            assert current_asset_version() == original

            source = template.read_bytes()
            template.write_text('<title>USS Stargazer</title>')
            changed = current_asset_version()
            assert changed != original
            assert current_asset_version() == changed
            template.write_bytes(source)
            assert current_asset_version() == original
