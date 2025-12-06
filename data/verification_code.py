from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime, timedelta

from data.db_session import SqlAlchemyBase

class VerificationCode(SqlAlchemyBase):
    __tablename__ = 'verification_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __init__(self, user_id, code, expiry_minutes=2):
        self.user_id = user_id
        self.code = code
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=expiry_minutes)

    def is_expired(self):
        return datetime.now() > self.expires_at