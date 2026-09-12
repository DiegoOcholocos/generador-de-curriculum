import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import themes


def test_resolve_theme_known_id():
    cfg = themes.resolve_theme('bosque')
    assert cfg['acc'] == '#74c69d'


def test_resolve_theme_legacy_name_maps_forward():
    cfg = themes.resolve_theme('moderna')
    assert cfg['id'] == 'moderna_roja'


def test_resolve_theme_unknown_falls_back_to_default():
    cfg = themes.resolve_theme('does-not-exist')
    assert cfg['id'] == themes.DEFAULT_THEME


def test_level_label_normalizes_common_inputs():
    assert themes.level_label('c1') == 'C1'
    assert themes.level_label('Nativo') == 'Nativo'
    assert themes.level_label('') == 'B2'
    assert themes.level_label('3') == 'B2'


def test_storage_rejects_invalid_profile_ids(monkeypatch, tmp_path):
    import storage
    monkeypatch.setattr(storage, 'DB_PATH', str(tmp_path / 't.db'))
    monkeypatch.setattr(storage, 'LEGACY_PROFILES_DIR', str(tmp_path / 'none'))
    storage.init_db()

    assert storage.get_profile('../../etc/passwd') is None
    assert storage.get_profile('a' * 200) is None
    storage.delete_profile('../../etc/passwd')  # must not raise, must not touch fs

    pid, name = storage.save_profile({'personal': {'name': 'X'}}, profile_name='Perfil')
    assert storage.valid_profile_id(pid)
    assert storage.get_profile(pid)['personal']['name'] == 'X'
