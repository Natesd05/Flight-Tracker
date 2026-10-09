"""Database-backed personal accounts; only hashes of session tokens are stored."""
import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from .db import get_db, Account, LoginSession, Profile
from .schemas import Schema, Preferences
from .seed import seed_classes

router = APIRouter(prefix='/api/auth')
COOKIE = 'flightplanner_session'


class Credentials(Schema):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**17, r=8, p=1, maxmem=256*1024*1024).hex()
    return salt + ':' + digest


def same_origin(request):
    origin = request.headers.get('origin')
    # Vite proxies local requests, so compare the original Host header.
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and urlsplit(origin).netloc != request.headers.get('host')):
        raise HTTPException(403, 'Cross-origin writes are not allowed.')


def token_hash(request):
    return hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest()


def current_account(request: Request, db=Depends(get_db)):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        same_origin(request)
    login = db.get(LoginSession, token_hash(request))
    if not login or login.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, 'Please log in to your account.')
    account = db.get(Account, login.account_id)
    if not account:
        raise HTTPException(401, 'Please log in to your account.')
    return account


def authorized_db(account=Depends(current_account), db=Depends(get_db)):
    db.info['profile_id'] = account.profile_id
    return db


def start_session(request, response, db, account):
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= datetime.now(timezone.utc)))
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request)))
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), account_id=account.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=30*86400, httponly=True, samesite='lax',
        secure=request.url.scheme == 'https' or request.headers.get('x-forwarded-proto') == 'https', path='/')
    response.headers['Cache-Control'] = 'no-store'
    return {'email': account.email}


@router.post('/signup', status_code=201)
def signup(data: Credentials, request: Request, response: Response, db=Depends(get_db)):
    same_origin(request)
    encoded = password_hash(data.password)
    profile = Profile(preferences=Preferences(name=data.email.split('@')[0][:80]).model_dump(mode='json'))
    db.add(profile)
    db.flush()
    account = Account(email=data.email, password_hash=encoded, profile_id=profile.id)
    db.add(account)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account already exists for this email. Log in instead.')
    seed_classes(db, profile.id)
    return start_session(request, response, db, account)


@router.post('/login')
def login(data: Credentials, request: Request, response: Response, db=Depends(get_db)):
    same_origin(request)
    account = db.scalar(select(Account).where(Account.email == data.email))
    salt = account.password_hash.split(':')[0] if account else '00'*16
    encoded = password_hash(data.password, salt)
    if not account or not secrets.compare_digest(encoded, account.password_hash):
        raise HTTPException(401, 'Email or password is incorrect.')
    return start_session(request, response, db, account)


@router.get('/me')
def me(response: Response, account=Depends(current_account)):
    response.headers['Cache-Control'] = 'no-store'
    return {'email': account.email}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, db=Depends(get_db)):
    same_origin(request)
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(request)))
    db.commit()
    response.delete_cookie(COOKIE, path='/')
