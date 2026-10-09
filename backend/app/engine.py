from collections import Counter
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from .schemas import Preferences, SearchInput, Schedule, Itinerary, Evaluation, Conflict, Cost
from .timeutils import UTC, localize, elapsed_minutes, days_between


def money(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def in_window(value, start, end):
    value = value.replace(tzinfo=None)
    if start == end:
        return True  # Equal endpoints represent a full day.
    return start <= value <= end if start < end else value >= start or value <= end


def class_conflicts(away_start, away_end, schedule: Schedule, zone: str):
    tz = ZoneInfo(zone)
    start_day = away_start.astimezone(tz).date() - timedelta(days=1)
    end_day = away_end.astimezone(tz).date()
    cancelled = {(e.class_id, e.date) for e in schedule.exceptions if e.kind == 'cancel'}
    intervals = []
    for day in days_between(start_day, end_day):
        for c in schedule.classes:
            if not c.optional and day.weekday() == c.weekday and (c.id, day) not in cancelled:
                intervals.append((c.title, day, c.start_time, c.end_time))
    intervals.extend((e.title, e.date, e.start_time, e.end_time) for e in schedule.exceptions
                     if e.kind == 'add' and start_day <= e.date <= end_day)
    conflicts = []
    overlaps = []
    for title, day, start, end in intervals:
        class_start = localize(day, start, zone)
        class_end = localize(day + timedelta(days=end < start), end, zone, end=True)
        low = max(away_start.astimezone(UTC), class_start.astimezone(UTC))
        high = min(away_end.astimezone(UTC), class_end.astimezone(UTC))
        if low < high:
            conflicts.append(Conflict(title=title, start=class_start, end=class_end,
                                      overlap_minutes=elapsed_minutes(low, high)))
            overlaps.append((low, high))
    # Union the overlaps: concurrent classes must not double-count missed time.
    total = 0
    merged = []
    for low, high in sorted(overlaps):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    total = sum(elapsed_minutes(a, b) for a, b in merged)
    return sorted(conflicts, key=lambda c: c.start.astimezone(UTC)), total


def evaluate(flight: Itinerary, prefs: Preferences, query: SearchInput, schedule: Schedule):
    out, back = flight.outbound, flight.inbound
    away_start = out[0].departure.astimezone(UTC) - timedelta(minutes=prefs.transit_minutes + prefs.buffer_minutes)
    away_end = back[-1].arrival.astimezone(UTC) + timedelta(minutes=prefs.transit_minutes)
    conflicts, missed = class_conflicts(away_start, away_end, schedule, prefs.timezone)
    trip_days = elapsed_minutes(away_start, away_end) / 1440
    travel = sum(elapsed_minutes(leg[0].departure, leg[-1].arrival) for leg in (out, back))
    # Home transit on each end; check-in/security buffer for both departures.
    travel += 2 * (prefs.transit_minutes + prefs.buffer_minutes)
    stops = len(out) + len(back) - 2
    departure_start = query.departure_start or prefs.departure_start
    departure_end = query.departure_end or prefs.departure_end
    arrival_start = query.arrival_start or prefs.arrival_start
    arrival_end = query.arrival_end or prefs.arrival_end
    violations = sum(not in_window(leg[0].departure.timetz(), departure_start, departure_end) for leg in (out, back))
    violations += sum(not in_window(leg[-1].arrival.timetz(), arrival_start, arrival_end) for leg in (out, back))
    total = money(Decimal(str(flight.airfare)) + Decimal(str(prefs.baggage_estimate)) + Decimal(str(prefs.ground_estimate)))
    reasons = []
    if query.hard_budget and total > prefs.budget:
        reasons.append('budget')
    if query.hard_conflicts and conflicts:
        reasons.append('classes')
    if query.hard_windows and violations:
        reasons.append('travel windows')
    if query.max_stops is not None and max(len(out), len(back)) - 1 > query.max_stops:
        reasons.append('stops')
    if not query.min_trip_days <= trip_days <= query.max_trip_days:
        reasons.append('trip duration')
    if reasons:
        return None, reasons
    penalties = dict(cost=min(total / prefs.budget, 1), conflicts=min(missed / 180, 1),
                     layovers=min(stops / 4, 1), windows=violations / 4, travel=min(travel / 1440, 1))
    weights = query.weights or prefs.weights
    values = weights.model_dump()
    score = round(100 * (1 - sum(penalties[k] * values[k] for k in values) / sum(values.values())), 2)
    explanations = [f'${total:.2f} estimated total · ' + (f'${prefs.budget-total:.2f} below budget.' if total <= prefs.budget else f'${total-prefs.budget:.2f} over budget.'),
                    f'{len(conflicts)} class conflict(s), {missed:.0f} minutes missed.' if conflicts else 'No class conflicts during your entire time away.',
                    f'{stops} total connection(s); {travel/60:.1f} hours of travel including home transit and airport buffers.',
                    f'{violations} of 4 departure/arrival times fall outside your preferred local windows.' if violations else 'Both journeys fit your preferred local travel windows.']
    return Evaluation(itinerary=flight, cost=Cost(airfare=money(flight.airfare), baggage_estimate=prefs.baggage_estimate,
                      ground_estimate=prefs.ground_estimate, total=total), score=score,
                      penalties=penalties, weights=weights, conflicts=conflicts, conflict_minutes=missed,
                      travel_minutes=travel, trip_days=round(trip_days, 3), stops=stops, window_violations=violations,
                      away_start=away_start, away_end=away_end, explanations=explanations), []


def rank(flights: list[Itinerary], prefs: Preferences, query: SearchInput, schedule: Schedule):
    results = []
    rejected = Counter()
    for flight in flights:
        evaluated, reasons = evaluate(flight, prefs, query, schedule)
        if evaluated:
            results.append(evaluated)
        rejected.update(reasons)
    results.sort(key=lambda e: (-e.score, e.cost.total, e.travel_minutes, e.itinerary.id))
    tips = {'budget': 'Raise the budget or reduce estimated extras.', 'classes': 'Try different dates or allow class conflicts.',
            'travel windows': 'Widen your travel windows or make them a preference.', 'stops': 'Allow more stops.',
            'trip duration': 'Widen the allowed door-to-door trip duration.'}
    suggestions = [tips[k] for k in rejected] if not results else []
    if not flights:
        suggestions = ['No provider offers for these dates. Try a different route or date range.']
    return results, dict(rejected), suggestions
