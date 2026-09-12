import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by an isolated, throwaway SQLite DB — never
    touches the real profiles.db in the project directory."""
    monkeypatch.setenv('CVWIZARD_DB_PATH', str(tmp_path / 'test_profiles.db'))

    import storage
    monkeypatch.setattr(storage, 'DB_PATH', str(tmp_path / 'test_profiles.db'))
    monkeypatch.setattr(storage, 'LEGACY_PROFILES_DIR', str(tmp_path / 'no_legacy_dir'))
    storage.init_db()

    import app as app_module
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c
