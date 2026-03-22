"""ORM models for normalized ship entities."""

from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Ship(Base):
    __tablename__ = "ships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    canonical_name = Column(Text)
    ship_type = Column(Text)
    ship_class = Column(Text)
    subtype = Column(Text)
    operator = Column(Text)
    country = Column(Text)
    flag = Column(Text)
    imo = Column(Text, index=True)
    mmsi = Column(Text, index=True)
    year_built = Column(Integer)
    description = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    aliases = relationship("ShipAlias", back_populates="ship", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="ship")


class ShipAlias(Base):
    __tablename__ = "ship_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ship_id = Column(Integer, nullable=False, index=True)
    alias_name = Column(Text, nullable=False)
    source = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    ship = relationship("Ship", back_populates="aliases")

    __table_args__ = (
        # ForeignKey defined via ForeignKeyConstraint to avoid circular issues
    )


# Add foreign key after table definition
from sqlalchemy import ForeignKeyConstraint
ShipAlias.__table__.append_constraint(
    ForeignKeyConstraint(["ship_id"], ["ships.id"])
)
