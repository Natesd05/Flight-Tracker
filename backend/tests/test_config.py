from app.config import Settings


def test_mounted_secrets_load_without_environment_values(tmp_path, monkeypatch):
    for key in ('DATABASE_URL', 'DUFFEL_ACCESS_TOKEN'):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / 'database_url').write_text('postgresql+psycopg://demo:example@db/demo')
    (tmp_path / 'duffel_access_token').write_text('duffel_test_example\n')
    config = Settings(_env_file=None, _secrets_dir=tmp_path)
    assert config.database_url == 'postgresql+psycopg://demo:example@db/demo'
    assert config.duffel_access_token == 'duffel_test_example'
