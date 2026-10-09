"""Runs migrations against a dedicated *_test database; never touches the app DB."""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from app.main import app
from app.db import get_db
from app.config import settings
from app.seed import seed

pytestmark = pytest.mark.integration


@pytest.fixture(scope='module')
def test_engine():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test.')
    parsed = make_url(url)
    if not parsed.drivername.startswith('postgresql') or not (parsed.database or '').endswith('_test'):
        pytest.fail('Refusing to run integration tests: database must be PostgreSQL and end in _test.')
    previous = settings.database_url
    settings.database_url=url
    try:
        command.upgrade(Config('alembic.ini'),'head')
    finally:
        settings.database_url=previous
    engine=create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def client(test_engine):
    # Roll back every test, including application commits, using a savepoint.
    connection=test_engine.connect()
    transaction=connection.begin()
    session=Session(bind=connection,join_transaction_mode='create_savepoint')
    seed(session)
    app.dependency_overrides[get_db]=lambda: session
    previous=settings.flight_provider
    settings.flight_provider='mock'
    with TestClient(app) as c:
        assert c.post("/api/auth/signup", json={"email": "test@example.com", "password": "a-test-password-123"}).status_code == 201
        yield c
    settings.flight_provider=previous
    app.dependency_overrides.clear()
    session.close(); transaction.rollback(); connection.close()


def search_body():
    return dict(origin='ORD',destination='LAX',departure_from='2026-09-11',departure_to='2026-09-11',return_from='2026-09-13',return_to='2026-09-13')


def test_full_persistence_flow(client):
    assert client.get('/api/health').json()['database']=='postgresql'
    initial=client.get('/api/schedule').json()
    c=client.post('/api/classes',json=dict(title='Test seminar',weekday=5,start_time='12:00',end_time='13:00'))
    assert c.status_code==201
    cid=c.json()['id']
    assert client.put(f'/api/classes/{cid}',json=dict(title='Updated seminar',weekday=5,start_time='12:00',end_time='14:00')).status_code==200
    prefs=client.get('/api/preferences').json()
    prefs['budget']=700
    assert client.put('/api/preferences',json=prefs).status_code==200
    assert client.get('/api/preferences').json()['budget']==700
    result=client.post('/api/searches',json=search_body())
    assert result.status_code==201, result.text
    data=result.json()
    assert data['results'] and data['results'][0]['explanations']
    assert any(c['title']=='Updated seminar' for c in data['results'][0]['conflicts'])
    assert client.get(f"/api/searches/{data['id']}").json()==data
    assert client.get('/api/searches').json()[0]['id']==data['id']
    ids=[]
    for e in data['results'][:2]:
        body=dict(search_id=data['id'],itinerary_id=e['itinerary']['id'])
        saved=client.post('/api/saved',json=body)
        assert saved.status_code==201
        assert client.post('/api/saved',json=body).json()['id']==saved.json()['id']
        ids.append(saved.json()['id'])
    assert len(client.get('/api/saved').json())==2
    # Snapshots retain the original estimate after preferences change.
    prefs['ground_estimate']=999
    client.put('/api/preferences',json=prefs)
    assert client.get('/api/saved').json()[0]['evaluation']['cost']['ground_estimate']==50
    assert client.delete(f'/api/saved/{ids[0]}').status_code==204
    assert len(client.get('/api/saved').json())==1
    assert client.delete(f'/api/classes/{cid}').status_code==204
    assert len(client.get('/api/schedule').json()['classes'])==len(initial['classes'])


def test_exception_foreign_keys_and_cascade(client):
    c=client.post('/api/classes',json=dict(title='Lab',weekday=4,start_time='10:00',end_time='11:00')).json()
    response=client.post('/api/exceptions',json=dict(kind='cancel',date='2026-09-11',class_id=c['id']))
    assert response.status_code==201
    assert client.post('/api/exceptions',json=dict(kind='cancel',date='2026-09-12',class_id=c['id'])).status_code==422
    assert client.post('/api/exceptions',json=dict(kind='cancel',date='2026-09-11',class_id=9999999)).status_code==404
    client.delete(f"/api/classes/{c['id']}")
    assert not client.get('/api/schedule').json()['exceptions']
    extra=client.post('/api/exceptions',json=dict(kind='add',date='2026-09-12',title='Exam',start_time='10:00',end_time='12:00')).json()
    assert client.delete(f"/api/exceptions/{extra['id']}").status_code==204


def test_validation_errors_and_unknown_records(client):
    response=client.post('/api/classes',json=dict(title='',weekday=7,start_time='10:00',end_time='11:00'))
    assert response.status_code==422 and 'error' in response.json()
    assert client.get('/api/searches/999999').status_code==404
    result=client.post('/api/searches',json=search_body()).json()
    assert client.post('/api/saved',json=dict(search_id=result['id'],itinerary_id='invented')).status_code==404
    settings.flight_provider='duffel'
    old=settings.duffel_access_token
    settings.duffel_access_token=''
    try:
        response=client.post('/api/searches',json=search_body())
        assert response.status_code==502 and 'DUFFEL_ACCESS_TOKEN' in response.json()['error']['message']
    finally:
        settings.duffel_access_token=old
        settings.flight_provider='mock'


def test_seed_is_idempotent(client):
    before=client.get('/api/schedule').json()
    db=app.dependency_overrides[get_db]()
    seed(db);seed(db)
    assert client.get('/api/schedule').json()==before


def test_migration_matches_orm(test_engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.db import Base
    with test_engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection),Base.metadata)==[]


def test_accounts_isolate_records_and_survive_login(client):
    from app.db import Account, LoginSession
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    prefs = client.get('/api/preferences').json()
    prefs['budget'] = 777
    assert client.put('/api/preferences', json=prefs).status_code == 200
    classes = client.get('/api/schedule').json()['classes']
    assert [c['weekday'] for c in classes] == [0, 1, 2, 3]
    original = classes[0]
    optional = {k: v for k, v in original.items() if k != 'id'}
    optional['optional'] = True
    assert client.put(f"/api/classes/{original['id']}", json=optional).json()['optional'] is True
    result = client.post('/api/searches', json=search_body()).json()
    saved = client.post('/api/saved', json={'search_id': result['id'], 'itinerary_id': result['results'][0]['itinerary']['id']}).json()
    exception = client.post('/api/exceptions', json={'kind': 'add', 'date': '2026-09-12', 'title': 'Exam', 'start_time': '10:00', 'end_time': '11:00'}).json()
    cookie = client.cookies.get('flightplanner_session')
    assert client.post('/api/auth/logout').status_code == 204
    assert client.get('/api/preferences').status_code == 401
    client.cookies.set('flightplanner_session', cookie)
    assert client.get('/api/preferences').status_code == 401
    client.cookies.clear()
    response = client.post('/api/auth/signup', json={'email': 'other@example.com', 'password': 'another-password-123'})
    assert response.status_code == 201
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']
    assert client.get('/api/preferences').json()['budget'] == 500
    assert client.get('/api/saved').json() == []
    assert client.get('/api/searches').json() == []
    assert client.put(f"/api/classes/{original['id']}", json=optional).status_code == 404
    assert client.delete(f"/api/classes/{original['id']}").status_code == 404
    assert client.get(f"/api/searches/{result['id']}").status_code == 404
    assert client.post('/api/saved', json={'search_id': result['id'], 'itinerary_id': result['results'][0]['itinerary']['id']}).status_code == 404
    assert client.delete(f"/api/saved/{saved['id']}").status_code == 404
    assert client.delete(f"/api/exceptions/{exception['id']}").status_code == 404
    assert client.post('/api/auth/login', json={'email': 'test@example.com', 'password': 'incorrect-password'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'TEST@example.com', 'password': 'a-test-password-123'}).status_code == 200
    assert client.get('/api/preferences').json()['budget'] == 777
    assert client.get('/api/schedule').json()['classes'][0]['optional'] is True
    assert len(client.get('/api/saved').json()) == 1
    assert client.post('/api/auth/signup', json={'email': 'TEST@example.com', 'password': 'a-test-password-123'}).status_code == 409
    db = app.dependency_overrides[get_db]()
    assert all(a.password_hash != 'a-test-password-123' for a in db.scalars(select(Account)))
    for row in db.scalars(select(LoginSession)):
        assert row.token_hash != client.cookies.get('flightplanner_session')
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.get('/api/auth/me').status_code == 401


def test_auth_cross_origin_and_validation(client):
    for path in ('signup', 'login', 'logout'):
        assert client.post('/api/auth/' + path, headers={'Origin': 'https://evil.example'}, json={'email': 'test@example.com', 'password': 'a-test-password-123'}).status_code == 403
    prefs = client.get('/api/preferences').json()
    assert client.put('/api/preferences', headers={'Origin': 'https://evil.example'}, json=prefs).status_code == 403
    assert client.post('/api/auth/signup', json={'email': 'bad', 'password': 'short'}).status_code == 422


def test_optional_class_does_not_affect_ranking(client):
    from app.engine import class_conflicts
    from app.schemas import Schedule
    from datetime import datetime, timezone
    data = {'title': 'Friday', 'weekday': 4, 'start_time': '09:00', 'end_time': '10:00', 'optional': False}
    row = client.post('/api/classes', json=data).json()
    start = datetime(2026, 9, 11, tzinfo=timezone.utc)
    end = datetime(2026, 9, 12, tzinfo=timezone.utc)
    schedule = Schedule.model_validate(client.get('/api/schedule').json())
    assert class_conflicts(start, end, schedule, 'America/Chicago')[1] == 60
    data['optional'] = True
    client.put(f"/api/classes/{row['id']}", json=data)
    schedule = Schedule.model_validate(client.get('/api/schedule').json())
    assert class_conflicts(start, end, schedule, 'America/Chicago')[1] == 0
