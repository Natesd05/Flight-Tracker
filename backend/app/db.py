from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, String, DateTime, func, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

if not settings.database_url.startswith('postgresql'):
    raise RuntimeError('Student Flight Planner requires PostgreSQL.')
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSONB)


class ClassRow(Base):
    __tablename__ = 'classes'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), index=True)
    data: Mapped[dict] = mapped_column(JSONB)


class ExceptionRow(Base):
    __tablename__ = 'schedule_exceptions'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey('classes.id', ondelete='CASCADE'), index=True)
    data: Mapped[dict] = mapped_column(JSONB)


class SearchRow(Base):
    __tablename__ = 'searches'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), index=True)
    request: Mapped[dict] = mapped_column(JSONB)
    context: Mapped[dict] = mapped_column(JSONB)
    response: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedRow(Base):
    __tablename__ = 'saved_itineraries'
    __table_args__ = (UniqueConstraint('profile_id', 'search_id', 'itinerary_id', name='uq_saved_option'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), index=True)
    search_id: Mapped[int] = mapped_column(ForeignKey('searches.id', ondelete='CASCADE'), index=True)
    itinerary_id: Mapped[str] = mapped_column(String(128))
    evaluation: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

Index('ix_search_profile_created', SearchRow.profile_id, SearchRow.created_at)


def get_db():
    with SessionLocal() as session:
        yield session


class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id', ondelete='CASCADE'), unique=True)


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
