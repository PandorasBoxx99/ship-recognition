"""ORM model for VPN logs."""

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, func

from backend.database import Base


class VPNLog(Base):
    __tablename__ = "vpn_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(Text, nullable=False)
    country = Column(Text)
    ip_address = Column(Text)
    timestamp = Column(DateTime, server_default=func.now())
    success = Column(Boolean, default=True)
