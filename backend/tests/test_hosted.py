import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.hosted import create_hosted_app
from app.config import Settings


@pytest.fixture
def static_dir(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>Demo frontend</h1>')
    return tmp_path


@pytest.fixture
def client(static_dir):
    api = FastAPI()
    @api.get('/api/preferences')
    def preferences():
        return {'test': True}
    @api.post('/api/classes')
    def classes():
        return {'created': True}
    return TestClient(create_hosted_app(api, static_dir, 'local-demo-password', 'https://demo.example'))


def test_pages_and_api_protected_but_liveness_public(client):
    assert client.get('/healthz').text == 'ok'
    for path in ('/', '/api/preferences', '/docs', '/openapi.json', '/unknown'):
        assert client.get(path).status_code == 401
        assert client.get(path, auth=('demo', 'wrong')).status_code == 401
    assert client.get('/', auth=('demo', 'local-demo-password')).text == '<h1>Demo frontend</h1>'
    result = client.get('/api/preferences', auth=('demo', 'local-demo-password'))
    assert result.json() == {'test': True}
    assert result.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('authorization', ['Basic ???', 'Basic ZGVtbw==', 'Bearer secret'])
def test_malformed_auth_is_rejected(client, authorization):
    assert client.get('/', headers={'Authorization': authorization}).status_code == 401


def test_cross_origin_writes_rejected(client):
    for headers in ({'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}, {'Origin': 'null'}):
        assert client.post('/api/classes', auth=('demo', 'local-demo-password'), headers=headers).status_code == 403
    assert client.post('/api/classes', auth=('demo', 'local-demo-password'), headers={'Origin': 'https://demo.example'}).status_code == 200


@pytest.mark.parametrize('password,origin', [('', 'https://demo.example'), ('short', 'https://demo.example'), ('local-demo-password', ''), ('local-demo-password', 'http://public.example')])
def test_bad_hosted_config_fails_closed(static_dir, password, origin):
    with pytest.raises(RuntimeError):
        create_hosted_app(FastAPI(), static_dir, password, origin)


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql', 'postgresql+psycopg'])
def test_neon_url_preserves_ssl_parameters(scheme):
    config = Settings(_env_file=None, database_url=f'{scheme}://demo:example@db.example/app?sslmode=require&channel_binding=require')
    assert config.database_url == 'postgresql+psycopg://demo:example@db.example/app?sslmode=require&channel_binding=require'
