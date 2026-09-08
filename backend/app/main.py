import logging
import time
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, Profile, ClassRow, ExceptionRow, SearchRow, SavedRow
from .schemas import (Preferences, ClassInput, ClassOut, ExceptionInput, ExceptionOut, Schedule, SearchInput,
                      SearchResult, SavedInput, SavedOut)
from .airports import AIRPORTS
from .providers import get_provider, ProviderError
from .engine import rank
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('flightplanner')
app = FastAPI(title='Student Flight Planner', version='0.1.0', description='Single demo student. No authentication. USD, one adult, round trips.')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(','), allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])


@app.middleware('http')
async def request_log(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    log.info('%s %s %s %.0fms', request.method, request.url.path, response.status_code, (time.monotonic()-started)*1000)
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'error': {'message': str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    details = [{'field': '.'.join(map(str, e['loc'][1:])), 'message': e['msg']} for e in exc.errors()]
    return JSONResponse(status_code=422, content={'error': {'message': '; '.join(f"{e['field']}: {e['message']}" for e in details), 'details': details}})


@app.exception_handler(ProviderError)
async def provider_error(request, exc):
    return JSONResponse(status_code=502, content={'error': {'message': str(exc)}})


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    log.error('Database request failed: %s', type(exc).__name__)
    return JSONResponse(status_code=503, content={'error': {'message': 'Database unavailable. Start PostgreSQL and run migrations and the demo seed.'}})


@app.get('/api/health')
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'postgresql', 'provider': settings.flight_provider}


@app.get('/api/airports')
def airports() -> list[dict[str, str]]:
    return [dict(code=code, name=name, timezone=zone) for code, (name, zone) in AIRPORTS.items()]


def profile(db):
    row = db.get(Profile, 1)
    if not row:
        raise HTTPException(503, 'Demo profile missing. Run python -m app.seed.')
    return row


@app.get('/api/preferences', response_model=Preferences)
def preferences(db: Session = Depends(get_db)):
    return profile(db).preferences


@app.put('/api/preferences', response_model=Preferences)
def update_preferences(data: Preferences, db: Session = Depends(get_db)):
    profile(db).preferences = data.model_dump(mode='json')
    db.commit()
    return data


@app.get('/api/schedule', response_model=Schedule)
def schedule(db: Session = Depends(get_db)):
    classes = db.scalars(select(ClassRow).where(ClassRow.profile_id == 1).order_by(ClassRow.id)).all()
    exceptions = db.scalars(select(ExceptionRow).where(ExceptionRow.profile_id == 1).order_by(ExceptionRow.id)).all()
    return Schedule(classes=[ClassOut(id=r.id, **r.data) for r in classes], exceptions=[ExceptionOut(id=r.id, **r.data) for r in exceptions])


@app.post('/api/classes', response_model=ClassOut, status_code=201)
def create_class(data: ClassInput, db: Session = Depends(get_db)):
    profile(db)
    row = ClassRow(profile_id=1, data=data.model_dump(mode='json'))
    db.add(row)
    db.commit()
    db.refresh(row)
    return ClassOut(id=row.id, **row.data)


def owned(db, model, row_id):
    row = db.get(model, row_id)
    if not row or row.profile_id != 1:
        raise HTTPException(404, 'Record not found.')
    return row


@app.put('/api/classes/{class_id}', response_model=ClassOut)
def update_class(class_id: int, data: ClassInput, db: Session = Depends(get_db)):
    row = owned(db, ClassRow, class_id)
    row.data = data.model_dump(mode='json')
    db.commit()
    return ClassOut(id=row.id, **row.data)


@app.delete('/api/classes/{class_id}', status_code=204)
def delete_class(class_id: int, db: Session = Depends(get_db)):
    db.delete(owned(db, ClassRow, class_id))
    db.commit()
    return Response(status_code=204)


@app.post('/api/exceptions', response_model=ExceptionOut, status_code=201)
def create_exception(data: ExceptionInput, db: Session = Depends(get_db)):
    profile(db)
    if data.class_id is not None:
        c = owned(db, ClassRow, data.class_id)
        if data.date.weekday() != c.data['weekday']:
            raise HTTPException(422, 'Cancellation date must match the class weekday.')
    row = ExceptionRow(profile_id=1, class_id=data.class_id, data=data.model_dump(mode='json'))
    db.add(row)
    db.commit()
    db.refresh(row)
    return ExceptionOut(id=row.id, **row.data)


@app.delete('/api/exceptions/{exception_id}', status_code=204)
def delete_exception(exception_id: int, db: Session = Depends(get_db)):
    db.delete(owned(db, ExceptionRow, exception_id))
    db.commit()
    return Response(status_code=204)


@app.post('/api/searches', response_model=SearchResult, status_code=201)
def search(data: SearchInput, db: Session = Depends(get_db)):
    prefs = Preferences.model_validate(profile(db).preferences)
    classes = schedule(db)
    flights = get_provider().search(data)
    results, rejected, suggestions = rank(flights, prefs, data, classes)
    provider = flights[0].provider if flights else settings.flight_provider
    payload = dict(provider=provider, evaluated_count=len(flights), rejected=rejected, suggestions=suggestions,
                   results=[r.model_dump(mode='json') for r in results])
    row = SearchRow(profile_id=1, request=data.model_dump(mode='json'), context=dict(preferences=prefs.model_dump(mode='json'), schedule=classes.model_dump(mode='json')), response=payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SearchResult(id=row.id, created_at=row.created_at, **payload)


@app.get('/api/searches', response_model=list[SearchResult])
def recent_searches(db: Session = Depends(get_db)):
    rows = db.scalars(select(SearchRow).where(SearchRow.profile_id == 1).order_by(SearchRow.id.desc()).limit(10)).all()
    return [SearchResult(id=r.id, created_at=r.created_at, **r.response) for r in rows]


@app.get('/api/searches/{search_id}', response_model=SearchResult)
def get_search(search_id: int, db: Session = Depends(get_db)):
    row = owned(db, SearchRow, search_id)
    return SearchResult(id=row.id, created_at=row.created_at, **row.response)


@app.post('/api/saved', response_model=SavedOut, status_code=201)
def save_option(data: SavedInput, db: Session = Depends(get_db)):
    search_row = owned(db, SearchRow, data.search_id)
    evaluation = next((x for x in search_row.response['results'] if x['itinerary']['id'] == data.itinerary_id), None)
    if evaluation is None:
        raise HTTPException(404, 'This itinerary does not belong to the search results.')
    stmt = insert(SavedRow).values(profile_id=1, search_id=data.search_id, itinerary_id=data.itinerary_id, evaluation=evaluation)
    db.execute(stmt.on_conflict_do_nothing(constraint='uq_saved_option'))
    db.commit()
    return db.scalar(select(SavedRow).where(SavedRow.profile_id == 1, SavedRow.search_id == data.search_id, SavedRow.itinerary_id == data.itinerary_id))


@app.get('/api/saved', response_model=list[SavedOut])
def saved(db: Session = Depends(get_db)):
    return db.scalars(select(SavedRow).where(SavedRow.profile_id == 1).order_by(SavedRow.id.desc())).all()


@app.delete('/api/saved/{saved_id}', status_code=204)
def delete_saved(saved_id: int, db: Session = Depends(get_db)):
    db.delete(owned(db, SavedRow, saved_id))
    db.commit()
    return Response(status_code=204)
