"""Private secret preparation must not expose or overwrite credentials."""
import importlib.util
from pathlib import Path
import stat
import pytest


@pytest.fixture
def setup_script(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts' / 'prepare-demo-secrets.py'
    spec = importlib.util.spec_from_file_location('prepare_demo', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, '__file__', str(tmp_path / 'scripts' / path.name))
    return module, tmp_path / 'deploy' / 'secrets'


def test_secret_setup_permissions_and_no_overwrite(setup_script, monkeypatch, capsys):
    module, target = setup_script
    # Syntactically valid fixture; no actual authentication uses this hash.
    hash_value = '$2a$14$' + 'A' * 53
    answers = iter([hash_value])
    monkeypatch.setattr(module, 'getpass', lambda _: next(answers))
    module.main()
    password = (target / 'database_password').read_text()
    assert len(password) == 64
    assert (target / 'database_url').read_text() == f'postgresql+psycopg://planner:{password}@db:5432/flightplanner'
    assert (target / 'demo_auth').read_text() == f'demo {hash_value}\n'
    assert not (target / 'duffel_access_token').exists()
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(file.stat().st_mode) == 0o600 for file in target.iterdir())
    output = capsys.readouterr().out
    assert password not in output and hash_value not in output
    with pytest.raises(SystemExit, match='refusing to overwrite'):
        module.main()
    assert (target / 'database_password').read_text() == password


@pytest.mark.parametrize('answers', [
    ['plaintext-password'],
])
def test_invalid_credentials_create_no_secret_files(setup_script, monkeypatch, answers):
    module, target = setup_script
    responses = iter(answers)
    monkeypatch.setattr(module, 'getpass', lambda _: next(responses))
    with pytest.raises(SystemExit):
        module.main()
    assert not target.exists()
