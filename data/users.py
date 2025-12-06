from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(length=100), nullable=False, unique=True)
    password = Column(String(length=100), nullable=False)
    native_lang = Column(String(length=100), nullable=False)
    email = Column(String(length=320), nullable=False, unique=True)
    russian_level = Column(String(length=2), nullable=False)
    status = Column(String(length=15), nullable=False, default='unverified')
    registration_date = Column(DateTime, default=datetime.now, nullable=False)
    verified_at = Column(DateTime, nullable=True)
