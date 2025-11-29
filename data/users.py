from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(length=100), nullable=False)
    password = Column(String(length=100), nullable=False)
    native_lang = Column(String(length=100), nullable=False)
    email = Column(String(length=40), nullable=False)
    russian_level = Column(String(length=2), nullable=False)
    registration_date = Column(String(length=60), nullable=False)
