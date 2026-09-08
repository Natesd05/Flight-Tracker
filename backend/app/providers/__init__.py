from typing import Protocol
from ..schemas import SearchInput, Itinerary
from ..config import settings


class ProviderError(Exception):
    pass


class FlightProvider(Protocol):
    def search(self, query: SearchInput) -> list[Itinerary]: ...


def get_provider() -> FlightProvider:
    if settings.flight_provider == 'mock':
        from .mock import MockProvider
        return MockProvider()
    if settings.flight_provider == 'duffel':
        from .duffel import DuffelProvider
        return DuffelProvider()
    raise ProviderError(f'Unknown FLIGHT_PROVIDER: {settings.flight_provider}. Use mock or duffel.')
