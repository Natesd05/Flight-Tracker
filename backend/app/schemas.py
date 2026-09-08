from datetime import date, time, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, AwareDatetime
from .airports import AIRPORTS


class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid', from_attributes=True, allow_inf_nan=False)

    @field_validator('*')
    @classmethod
    def local_clock_without_offset(cls, value):
        if isinstance(value, time) and value.tzinfo is not None:
            raise ValueError('Use a local clock time without a timezone offset.')
        return value


class Weights(Schema):
    cost: float = Field(default=35, ge=0, le=100)
    conflicts: float = Field(default=30, ge=0, le=100)
    layovers: float = Field(default=10, ge=0, le=100)
    windows: float = Field(default=10, ge=0, le=100)
    travel: float = Field(default=15, ge=0, le=100)

    @model_validator(mode='after')
    def positive_sum(self):
        if sum(self.model_dump().values()) == 0:
            raise ValueError('At least one ranking weight must be positive.')
        return self


class Preferences(Schema):
    name: str = Field(default='Alex Morgan', min_length=1, max_length=80)
    timezone: str = 'America/Chicago'
    home_airport: str = 'ORD'
    transit_minutes: int = Field(default=45, ge=0, le=360)
    buffer_minutes: int = Field(default=90, ge=0, le=360)
    budget: float = Field(default=500, gt=0, le=50000, allow_inf_nan=False)
    baggage_estimate: float = Field(default=40, ge=0, le=2000, allow_inf_nan=False)
    ground_estimate: float = Field(default=50, ge=0, le=2000, allow_inf_nan=False)
    departure_start: time = time(8)
    departure_end: time = time(21)
    arrival_start: time = time(7)
    arrival_end: time = time(23)
    weights: Weights = Field(default_factory=Weights)

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Use a valid IANA timezone, such as America/Chicago.')
        return value

    @field_validator('home_airport')
    @classmethod
    def valid_airport(cls, value):
        if value not in AIRPORTS:
            raise ValueError('Choose an airport from the supported catalog.')
        return value


class ClassInput(Schema):
    title: str = Field(min_length=1, max_length=100)
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode='after')
    def valid_interval(self):
        if self.start_time == self.end_time:
            raise ValueError('Class start and end times must differ. Earlier end times mean next day.')
        if self.start_time.tzinfo or self.end_time.tzinfo:
            raise ValueError('Class times must be local times without an offset.')
        return self


class ClassOut(ClassInput):
    id: int


class ExceptionInput(Schema):
    date: date
    kind: Literal['cancel', 'add']
    class_id: int | None = None
    title: str = Field(default='Extra class', min_length=1, max_length=100)
    start_time: time | None = None
    end_time: time | None = None

    @model_validator(mode='after')
    def valid_exception(self):
        if self.kind == 'cancel' and self.class_id is None:
            raise ValueError('A cancellation needs a class.')
        if self.kind == 'add':
            if self.class_id is not None:
                raise ValueError('Extra classes must not reference a recurring class.')
            if self.start_time is None or self.end_time is None or self.start_time == self.end_time:
                raise ValueError('An extra class needs distinct start and end times.')
        return self


class ExceptionOut(ExceptionInput):
    id: int


class Schedule(Schema):
    classes: list[ClassOut]
    exceptions: list[ExceptionOut]


class SearchInput(Schema):
    origin: str = 'ORD'
    destination: str = 'LAX'
    departure_from: date
    departure_to: date
    return_from: date
    return_to: date
    min_trip_days: float = Field(default=1, ge=0, le=30)
    max_trip_days: float = Field(default=7, gt=0, le=30)
    hard_budget: bool = True
    hard_conflicts: bool = False
    hard_windows: bool = False
    max_stops: int | None = Field(default=None, ge=0, le=2)
    weights: Weights | None = None
    departure_start: time | None = None
    departure_end: time | None = None
    arrival_start: time | None = None
    arrival_end: time | None = None

    @field_validator('origin', 'destination')
    @classmethod
    def known_airport(cls, value):
        if value not in AIRPORTS:
            raise ValueError('Choose an airport from the supported catalog.')
        return value

    @model_validator(mode='after')
    def dates_valid(self):
        if self.origin == self.destination:
            raise ValueError('Origin and destination must differ.')
        if self.departure_to < self.departure_from or self.return_to < self.return_from:
            raise ValueError('Each date range must end on or after its start.')
        if self.return_from < self.departure_from or (self.return_to - self.departure_from).days > 31:
            raise ValueError('Return dates must follow departure start and the search must span at most 31 days.')
        if (self.departure_to-self.departure_from).days > 3 or (self.return_to-self.return_from).days > 3:
            raise ValueError('Each flexible date range supports at most four days (16 date pairs).')
        if self.min_trip_days > self.max_trip_days:
            raise ValueError('Minimum trip duration cannot exceed maximum.')
        return self


class Segment(Schema):
    origin: str
    destination: str
    departure: AwareDatetime
    arrival: AwareDatetime
    airline: str
    flight_number: str

    @model_validator(mode='after')
    def chronological(self):
        if self.arrival.astimezone(timezone.utc) <= self.departure.astimezone(timezone.utc):
            raise ValueError('Flight arrival must follow departure.')
        return self


class Itinerary(Schema):
    id: str
    provider: str
    airfare: float = Field(ge=0, allow_inf_nan=False)
    currency: Literal['USD'] = 'USD'
    outbound: list[Segment] = Field(min_length=1)
    inbound: list[Segment] = Field(min_length=1)

    @model_validator(mode='after')
    def coherent(self):
        for leg in (self.outbound, self.inbound):
            for first, second in zip(leg, leg[1:]):
                if first.destination != second.origin or first.arrival.astimezone(timezone.utc) >= second.departure.astimezone(timezone.utc):
                    raise ValueError('Invalid connection.')
        if self.outbound[-1].arrival.astimezone(timezone.utc) >= self.inbound[0].departure.astimezone(timezone.utc):
            raise ValueError('Return departs before arrival at destination.')
        if self.outbound[0].origin != self.inbound[-1].destination or self.outbound[-1].destination != self.inbound[0].origin:
            raise ValueError('Itinerary must be a round trip.')
        return self


class Conflict(Schema):
    title: str
    start: datetime
    end: datetime
    overlap_minutes: float


class Cost(Schema):
    airfare: float
    baggage_estimate: float
    ground_estimate: float
    total: float


class Evaluation(Schema):
    itinerary: Itinerary
    cost: Cost
    score: float
    penalties: dict[str, float]
    weights: Weights
    conflicts: list[Conflict]
    conflict_minutes: float
    travel_minutes: float
    trip_days: float
    stops: int
    window_violations: int
    away_start: datetime
    away_end: datetime
    explanations: list[str]


class SearchResult(Schema):
    id: int
    provider: str
    evaluated_count: int
    rejected: dict[str, int]
    suggestions: list[str]
    results: list[Evaluation]
    created_at: datetime


class SavedInput(Schema):
    search_id: int
    itinerary_id: str


class SavedOut(Schema):
    id: int
    search_id: int
    itinerary_id: str
    evaluation: Evaluation
    created_at: datetime
