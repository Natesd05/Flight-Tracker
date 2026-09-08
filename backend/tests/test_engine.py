from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from pydantic import ValidationError
from app.schemas import Preferences, SearchInput, Schedule, ClassOut, ExceptionOut, Weights, Itinerary, Segment
from app.providers.mock import MockProvider
from app.engine import evaluate, rank, class_conflicts, in_window
from app.timeutils import localize, elapsed_minutes, UTC


def query(**changes):
    return SearchInput(**dict(departure_from='2026-09-11', departure_to='2026-09-11', return_from='2026-09-13', return_to='2026-09-13', **changes))


def empty():
    return Schedule(classes=[], exceptions=[])


def occurrence(id=1, title='Lecture', weekday=4, start='10:00', end='12:00'):
    return ClassOut(id=id, title=title, weekday=weekday, start_time=start, end_time=end)


def test_mock_is_deterministic_and_has_variety():
    flights = MockProvider().search(query())
    assert flights == MockProvider().search(query())
    assert len(flights) == 6
    assert len({f.airfare for f in flights}) > 3
    assert any(len(f.outbound) > 1 for f in flights)
    assert any(f.inbound[0].departure.date() != f.inbound[-1].arrival.date() for f in flights)
    assert flights[0].outbound[0].departure.utcoffset() != flights[0].outbound[-1].arrival.utcoffset()


def test_cost_and_travel_are_counted_once():
    prefs = Preferences(baggage_estimate=35.15, ground_estimate=50.22, budget=1000)
    flight = MockProvider().search(query())[0]
    e, reasons = evaluate(flight, prefs, query(), empty())
    assert not reasons
    assert e.cost.total == 282.37  # 169 + Friday surcharge 28 + 35.15 + 50.22
    assert e.travel_minutes == 2 * 210 + 2 * (45 + 90)
    assert e.away_start == flight.outbound[0].departure.astimezone(UTC) - timedelta(minutes=135)
    assert e.away_end == flight.inbound[-1].arrival.astimezone(UTC) + timedelta(minutes=45)


def test_destination_stay_counts_as_conflict_and_cancellation_removes_it():
    flight = MockProvider().search(query())[2]
    classes = Schedule(classes=[occurrence(weekday=5)], exceptions=[])
    e, _ = evaluate(flight, Preferences(), query(), classes)
    assert e.conflict_minutes == 120
    classes.exceptions.append(ExceptionOut(id=1, kind='cancel', date='2026-09-12', class_id=1))
    e, _ = evaluate(flight, Preferences(), query(), classes)
    assert not e.conflicts


def test_transit_buffer_overlap_partial_and_boundary():
    start = datetime(2026,9,11,11,30,tzinfo=ZoneInfo('America/Chicago'))
    end = start + timedelta(hours=5)
    conflicts, minutes = class_conflicts(start,end,Schedule(classes=[occurrence()], exceptions=[]),'America/Chicago')
    assert len(conflicts) == 1 and minutes == 30
    assert class_conflicts(start.replace(hour=12,minute=0), end, Schedule(classes=[occurrence()],exceptions=[]), 'America/Chicago')[1] == 0


def test_overlapping_classes_union_missed_minutes():
    schedule = Schedule(classes=[occurrence(), occurrence(id=2,start='11:00',end='13:00')], exceptions=[])
    start = datetime(2026,9,11,8,tzinfo=ZoneInfo('America/Chicago'))
    conflicts, minutes = class_conflicts(start,start+timedelta(hours=8),schedule,'America/Chicago')
    assert len(conflicts) == 2 and minutes == 180


def test_overnight_class_starting_previous_day_and_extra_class():
    schedule = Schedule(classes=[occurrence(weekday=3,start='23:00',end='01:00')], exceptions=[ExceptionOut(id=1,kind='add',date='2026-09-11',title='Exam',start_time='02:00',end_time='03:00')])
    start = datetime(2026,9,11,0,30,tzinfo=ZoneInfo('America/Chicago'))
    conflicts, minutes = class_conflicts(start,start+timedelta(hours=4),schedule,'America/Chicago')
    assert minutes == 90 and [c.title for c in conflicts] == ['Lecture','Exam']


def test_dst_spring_gap_shift_and_elapsed():
    stamp = localize(date(2026,3,8),time(2,30),'America/Chicago')
    assert stamp.hour == 3 and stamp.minute == 30
    a = localize(date(2026,3,8),time(1,30),'America/Chicago')
    assert elapsed_minutes(a,stamp) == 60


def test_dst_fall_fold_uses_conservative_endpoints():
    a = localize(date(2026,11,1),time(1,15),'America/Chicago')
    b = localize(date(2026,11,1),time(1,45),'America/Chicago',end=True)
    assert elapsed_minutes(a,b) == 90
    schedule = Schedule(classes=[occurrence(weekday=6,start='01:15',end='01:45')],exceptions=[])
    assert class_conflicts(a,b,schedule,'America/Chicago')[1] == 90


def test_class_timezone_independent_from_airport_timezone():
    flight = MockProvider().search(query())[0]
    e, _ = evaluate(flight,Preferences(timezone='Asia/Tokyo'),query(),Schedule(classes=[occurrence(start='23:00',end='23:30')],exceptions=[]))
    assert e.conflict_minutes == 30
    assert str(e.conflicts[0].start.tzinfo) == 'Asia/Tokyo'


@pytest.mark.parametrize('changes, prefs, reason', [
    ({}, Preferences(budget=100), 'budget'),
    ({'hard_conflicts':True}, Preferences(), 'classes'),
    ({'hard_windows':True}, Preferences(), 'travel windows'),
    ({'max_trip_days':1}, Preferences(), 'trip duration'),
])
def test_hard_constraints_reject_before_scoring(changes,prefs,reason):
    flight = MockProvider().search(query())[0]
    result,reasons=evaluate(flight,prefs,query(**changes),Schedule(classes=[occurrence()],exceptions=[]))
    assert result is None and reason in reasons


def test_stops_constraint_is_per_direction():
    flight = MockProvider().search(query())[1]
    assert 'stops' in evaluate(flight,Preferences(),query(max_stops=0),empty())[1]
    assert evaluate(flight,Preferences(),query(max_stops=1),empty())[0].stops == 2


def test_weighted_score_and_stable_tie_breaking():
    flights = MockProvider().search(query())
    prefs = Preferences()
    q = query(weights=Weights(cost=100,conflicts=0,layovers=0,windows=0,travel=0))
    results,_,_=rank(flights,prefs,q,empty())
    assert results[0].cost.total == min(e.cost.total for e in results)
    assert results[0].score == round(100*(1-results[0].cost.total/prefs.budget),2)
    assert [e.itinerary.id for e in results] == [e.itinerary.id for e in rank(list(reversed(flights)),prefs,q,empty())[0]]
    clone = flights[0].model_copy(update={'id':'aaa'})
    tied,_,_=rank([flights[0],clone],prefs,q,empty())
    assert tied[0].itinerary.id == 'aaa'


def test_no_results_explains_constraints_and_never_relaxes():
    results,rejected,tips=rank(MockProvider().search(query()),Preferences(budget=20),query(),empty())
    assert not results and rejected['budget'] == 6 and 'budget' in tips[0]
    assert rank([],Preferences(),query(),empty())[2]


def test_windows_cross_midnight_and_equal_is_full_day():
    assert in_window(time(23),time(21),time(6))
    assert in_window(time(4),time(21),time(6))
    assert not in_window(time(12),time(21),time(6))
    assert in_window(time(12),time(0),time(0))


def test_invalid_inputs_rejected():
    with pytest.raises(ValidationError): Preferences(timezone='Not/AZone')
    with pytest.raises(ValidationError): Weights(cost=0,conflicts=0,layovers=0,windows=0,travel=0)
    with pytest.raises(ValidationError): query(origin='XXX')
    with pytest.raises(ValidationError): query(min_trip_days=6,max_trip_days=2)
    with pytest.raises(ValidationError): SearchInput(departure_from='2026-09-11',departure_to='2026-09-18',return_from='2026-09-20',return_to='2026-09-20')
    with pytest.raises(ValidationError): Preferences(budget=float('nan'))
    with pytest.raises(ValidationError): occurrence(start='09:00',end='09:00')


def test_flexible_range_covers_all_date_pairs():
    q=SearchInput(departure_from='2026-09-10',departure_to='2026-09-11',return_from='2026-09-13',return_to='2026-09-14')
    flights=MockProvider().search(q)
    assert len(flights)==24
    assert len({(f.outbound[0].departure.date(),f.inbound[0].departure.date()) for f in flights})==4


def test_offset_clock_inputs_are_rejected():
    with pytest.raises(ValidationError): Preferences(departure_start='09:00+02:00')
    with pytest.raises(ValidationError): query(arrival_end='22:00Z')
    with pytest.raises(ValidationError): ExceptionOut(id=1,kind='add',date='2026-09-12',start_time='10:00Z',end_time='11:00Z')


def test_segment_chronology_across_fall_fold():
    start=localize(date(2026,11,1),time(1,45),'America/Chicago')
    end=localize(date(2026,11,1),time(1,30),'America/Chicago',end=True)
    segment=Segment(origin='ORD',destination='MDW',departure=start,arrival=end,airline='Demo',flight_number='DE1')
    assert elapsed_minutes(segment.departure,segment.arrival)==45
