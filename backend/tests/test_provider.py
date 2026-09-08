import json
import httpx
import pytest
from app.providers.duffel import DuffelProvider
from app.providers import ProviderError, get_provider
from app.config import settings
from app.schemas import SearchInput


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setattr(settings,'duffel_access_token','duffel_test_token')


def query():
    return SearchInput(departure_from='2026-09-11',departure_to='2026-09-11',return_from='2026-09-13',return_to='2026-09-13')


def payload(currency='USD'):
    ord={'iata_code':'ORD','time_zone':'America/Chicago'}
    lax={'iata_code':'LAX','time_zone':'America/Los_Angeles'}
    def segment(a,b,departure,arrival,number):
        return dict(origin=a,destination=b,departing_at=departure,arriving_at=arrival,operating_carrier={'name':'United Airlines'},marketing_carrier={'iata_code':'UA'},marketing_carrier_flight_number=number,stops=[])
    return {'data':{'offers':[{'id':'off_test','live_mode':False,'total_amount':'299.50','total_currency':currency,'slices':[
        {'segments':[segment(ord,lax,'2026-09-11T17:00:00','2026-09-11T19:00:00','123')]},
        {'segments':[segment(lax,ord,'2026-09-13T15:00:00','2026-09-13T21:00:00','124')]}
    ]}]}}


def test_duffel_request_and_offer_mapping(credentials):
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.url.path=='/air/offer_requests' and request.method=='POST'
        assert request.headers['Authorization']=='Bearer duffel_test_token'
        assert request.headers['Duffel-Version']=='v2'
        body=json.loads(request.content)['data']
        assert body['slices'][1]['departure_date']=='2026-09-13'
        assert body['passengers']==[{'type':'adult'}] and body['cabin_class']=='economy'
        return httpx.Response(201,json=payload())
    flights=DuffelProvider(httpx.MockTransport(handler)).search(query())
    assert len(calls)==1 and len(flights)==1
    assert flights[0].airfare==299.50 and flights[0].provider=='duffel-test'
    assert flights[0].outbound[0].departure.utcoffset().total_seconds()==-18000
    assert flights[0].outbound[0].airline=='United Airlines'


@pytest.mark.parametrize('status',[401,429,500])
def test_duffel_errors_never_fallback(credentials,status):
    with pytest.raises(ProviderError,match=f'HTTP {status}'):
        DuffelProvider(httpx.MockTransport(lambda r:httpx.Response(status,json={}))).search(query())


def test_currency_mismatch_is_not_mislabeled_usd(credentials):
    with pytest.raises(ProviderError,match='non-USD'):
        DuffelProvider(httpx.MockTransport(lambda r:httpx.Response(201,json=payload('GBP')))).search(query())


def test_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings,'flight_provider','invalid')
    with pytest.raises(ProviderError,match='Unknown'):
        get_provider()


def test_missing_timezone_is_explicit_error():
    with pytest.raises(ProviderError,match='omitted the timezone'):
        DuffelProvider.timestamp('2026-09-11T14:00:00',{'iata_code':'XXX'})
