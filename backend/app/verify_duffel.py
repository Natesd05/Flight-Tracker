"""Credential-based search-only smoke check: python -m app.verify_duffel."""
from datetime import date, timedelta
import json
from .config import settings
from .providers import ProviderError
from .providers.duffel import DuffelProvider
from .schemas import SearchInput


def main():
    if not settings.duffel_access_token.startswith('duffel_test_'):
        raise SystemExit('Configure a Duffel test token in DUFFEL_ACCESS_TOKEN; no request was made.')
    settings.duffel_require_test_mode = True
    depart = date.today() + timedelta(days=30)
    back = depart + timedelta(days=3)
    query = SearchInput(departure_from=depart, departure_to=depart,
                        return_from=back, return_to=back, hard_budget=False)
    try:
        offers = DuffelProvider().search(query)
    except ProviderError as exc:
        raise SystemExit(str(exc)) from None
    if not offers:
        raise SystemExit('Duffel responded but returned no offers; mapping verification is incomplete.')
    # Parsing validates USD, coherent segments, route/dates and aware timestamps.
    print(json.dumps({
        'status': 'passed', 'route': 'ORD-LAX', 'departure': str(depart),
        'return': str(back), 'offers_validated': len(offers),
        'providers': sorted({offer.provider for offer in offers}),
        'currencies': sorted({offer.currency for offer in offers}),
        'timezone_names': sorted({str(segment.departure.tzinfo)
                                  for offer in offers for segment in offer.outbound + offer.inbound}),
    }, indent=2))


if __name__ == '__main__':
    main()
