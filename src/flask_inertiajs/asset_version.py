from hashlib import sha256
from pathlib import Path

from flask import current_app


def current_asset_version() -> str:
    """Hash the root template source and the configured Vite manifest."""
    manifest = current_app.config['INERTIA_VITE_MANIFEST_PATH']
    if not isinstance(manifest, Path):
        raise TypeError('INERTIA_VITE_MANIFEST_PATH must be a Path instance')
    if not manifest.is_absolute():
        raise ValueError('INERTIA_VITE_MANIFEST_PATH must be an absolute path')

    env = current_app.jinja_env
    source, _, _ = env.loader.get_source(env, current_app.config['INERTIA_TEMPLATE'])
    digest = sha256(source.encode('utf-8'))
    digest.update(manifest.read_bytes())
    return digest.hexdigest()
