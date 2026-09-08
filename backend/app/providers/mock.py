from datetime import time, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo
from ..airports import AIRPORTS
from ..schemas import SearchInput, Itinerary, Segment
from ..timeutils import UTC, localize, days_between


class MockProvider:
    def search(self, query: SearchInput) -> list[Itinerary]:
        options = []
        longhaul = any(x in ('LHR', 'CDG') for x in (query.origin, query.destination))
        base_minutes = 480 if longhaul else 210
        variants = [(6, 14, 0, 169, 'Frontier'), (10, 10, 1, 205, 'American'),
                    (17, 16, 0, 289, 'United'), (21, 22, 0, 239, 'Delta'),
                    (14, 18, 1, 189, 'Southwest'), (19, 13, 0, 389, 'United')]
        for departure_day in days_between(query.departure_from, query.departure_to):
            for return_day in days_between(query.return_from, query.return_to):
                for variant, (out_hour, return_hour, stops, price, airline) in enumerate(variants):
                    legs = []
                    for day, hour, origin, destination in ((departure_day, out_hour, query.origin, query.destination),
                                                           (return_day, return_hour, query.destination, query.origin)):
                        depart = localize(day, time(hour), AIRPORTS[origin][1]).astimezone(UTC)
                        airports = [origin, destination] if not stops else [origin, next(x for x in ('DFW', 'DEN', 'ATL') if x not in (origin, destination)), destination]
                        segments = []
                        for index, (a, b) in enumerate(zip(airports, airports[1:])):
                            duration = base_minutes if not stops else base_minutes // 2 + 30
                            arrive = depart + timedelta(minutes=duration)
                            segments.append(Segment(origin=a, destination=b, departure=depart.astimezone(ZoneInfo(AIRPORTS[a][1])),
                                arrival=arrive.astimezone(ZoneInfo(AIRPORTS[b][1])), airline=airline,
                                flight_number=f'{airline[:2].upper()}{410 + variant*10 + index}'))
                            depart = arrive + timedelta(minutes=95)
                        legs.append(segments)
                    if legs[0][-1].arrival >= legs[1][0].departure:
                        continue
                    key = f'{query.origin}-{query.destination}-{departure_day}-{return_day}-{variant}'
                    options.append(Itinerary(id='mock-' + sha256(key.encode()).hexdigest()[:16], provider='mock',
                        airfare=price + (departure_day.weekday() * 7) + (80 if longhaul else 0), outbound=legs[0], inbound=legs[1]))
        return options
