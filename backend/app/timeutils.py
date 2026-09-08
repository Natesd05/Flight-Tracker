from datetime import datetime, timezone, timedelta, date, time
from zoneinfo import ZoneInfo

UTC = timezone.utc


def localize(day: date, clock: time, zone: str, *, end: bool = False) -> datetime:
    """Resolve DST folds conservatively; shift nonexistent wall times forward by the gap.

    Ambiguous starts use the earliest instant, ends the latest. A nonexistent 02:30
    becomes 03:30 for a one-hour spring gap, retaining its position within the gap.
    """
    naive = datetime.combine(day, clock.replace(tzinfo=None))
    tz = ZoneInfo(zone)
    candidates = [naive.replace(tzinfo=tz, fold=fold) for fold in (0, 1)]
    valid = [x for x in candidates if x.astimezone(UTC).astimezone(tz).replace(tzinfo=None) == naive]
    if valid:
        return (max if end else min)(valid, key=lambda x: x.astimezone(UTC))
    shifted = [x.astimezone(UTC).astimezone(tz) for x in candidates]
    return min((x for x in shifted if x.replace(tzinfo=None) > naive), key=lambda x: x.astimezone(UTC))


def elapsed_minutes(start: datetime, end: datetime) -> float:
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 60


def days_between(start: date, end: date):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)
