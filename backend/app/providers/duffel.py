"""Duffel v2 offer search only. No orders, bookings, or payment endpoints."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from ..config import settings
from ..schemas import SearchInput, Segment, Itinerary
from ..timeutils import days_between, localize
from . import ProviderError


class DuffelProvider:
    def __init__(self, transport=None):
        self.transport = transport

    @staticmethod
    def timestamp(value, airport):
        stamp = datetime.fromisoformat(value)
        zone = airport.get('time_zone')
        if not zone:
            raise ProviderError(f"Duffel omitted the timezone for {airport.get('iata_code', 'an airport')}.")
        try:
            tz = ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ProviderError('Duffel returned an unsupported airport timezone.') from exc
        if stamp.tzinfo:
            return stamp.astimezone(tz)
        return localize(stamp.date(), stamp.time(), zone)

    def search(self, query: SearchInput):
        if not settings.duffel_access_token:
            raise ProviderError('Duffel requires DUFFEL_ACCESS_TOKEN. Set a test token or select FLIGHT_PROVIDER=mock.')
        if settings.duffel_require_test_mode and not settings.duffel_access_token.startswith('duffel_test_'):
            raise ProviderError('This demo requires a Duffel test token.')
        try:
            with httpx.Client(base_url='https://api.duffel.com', timeout=25, transport=self.transport,
                              headers={'Authorization': f'Bearer {settings.duffel_access_token}',
                                       'Duffel-Version': 'v2', 'Accept': 'application/json'}) as client:
                options = {}
                for depart in days_between(query.departure_from, query.departure_to):
                    for back in days_between(query.return_from, query.return_to):
                        if back < depart:
                            continue
                        response = client.post('/air/offer_requests', params={'return_offers': 'true', 'supplier_timeout': 10000},
                            json={'data': {'slices': [
                                {'origin': query.origin, 'destination': query.destination, 'departure_date': depart.isoformat()},
                                {'origin': query.destination, 'destination': query.origin, 'departure_date': back.isoformat()}],
                                'passengers': [{'type': 'adult'}], 'cabin_class': 'economy', 'max_connections': 2}})
                        response.raise_for_status()
                        payload = response.json()['data']
                        for offer in payload['offers']:
                            if type(offer['live_mode']) is not bool:
                                raise ProviderError('Duffel returned an invalid test/live mode flag.')
                            if settings.duffel_require_test_mode and offer['live_mode']:
                                raise ProviderError('This demo cannot display live Duffel offers.')
                            if len(offer['slices']) != 2:
                                raise ProviderError('Duffel returned an unsupported itinerary. Only round trips are supported.')
                            if offer['total_currency'] != 'USD':
                                raise ProviderError('Duffel returned a non-USD fare. Configure your Duffel organisation for USD; this MVP does not convert currencies.')
                            legs = []
                            for leg in offer['slices']:
                                segments = []
                                for item in leg['segments']:
                                    if item.get('stops'):
                                        raise ProviderError('Duffel returned a flight with an intermediate technical stop, which this MVP cannot score. Try another route.')
                                    a, b = item['origin'], item['destination']
                                    segments.append(Segment(origin=a['iata_code'], destination=b['iata_code'],
                                        departure=self.timestamp(item['departing_at'], a), arrival=self.timestamp(item['arriving_at'], b),
                                        airline=item['operating_carrier']['name'],
                                        flight_number=(item['marketing_carrier'].get('iata_code') or '') + item['marketing_carrier_flight_number']))
                                legs.append(segments)
                            key = 'duffel-' + offer['id']
                            mode = 'live' if offer['live_mode'] else 'test'
                            itinerary = Itinerary(id=key, provider=f'duffel-{mode}',
                                airfare=float(offer['total_amount']), outbound=legs[0], inbound=legs[1])
                            if (itinerary.outbound[0].origin != query.origin or
                                    itinerary.outbound[-1].destination != query.destination or
                                    itinerary.outbound[0].departure.date() != depart or
                                    itinerary.inbound[0].departure.date() != back):
                                raise ProviderError('Duffel returned an itinerary that does not match the requested route or dates.')
                            options[key] = itinerary
                return list(options.values())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            advice = 'Check DUFFEL_ACCESS_TOKEN.' if status in (401, 403) else 'Check your route, dates, account access and API quota; retry later.'
            raise ProviderError(f'Duffel returned HTTP {status}. {advice}') from exc
        except httpx.RequestError as exc:
            raise ProviderError('Unable to reach Duffel. Check your network and try again.') from exc
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderError('Duffel returned an invalid offer. Try another route or contact the app maintainer.') from exc
