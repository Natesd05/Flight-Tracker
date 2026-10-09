from sqlalchemy.dialects.postgresql import insert
from .db import SessionLocal, Profile, ClassRow
from .schemas import Preferences


def seed_classes(session, profile_id):
    for title, weekday, start, end in [('Data Structures', 0, '09:00', '10:15'),
            ('Economics', 1, '13:00', '14:15'), ('Data Structures', 2, '09:00', '10:15'),
            ('Statistics', 3, '10:00', '11:15')]:
        session.add(ClassRow(profile_id=profile_id, data=dict(title=title, weekday=weekday,
            start_time=start, end_time=end, optional=False)))


def seed(session):
    inserted = session.execute(insert(Profile).values(id=1, preferences=Preferences().model_dump(mode='json'))
                               .on_conflict_do_nothing().returning(Profile.id)).scalar_one_or_none()
    if inserted:
        seed_classes(session, 1)
    session.commit()


if __name__ == '__main__':
    with SessionLocal() as session:
        seed(session)
    print('Demo profile ready. Existing data preserved.')
