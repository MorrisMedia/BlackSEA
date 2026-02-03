import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    category = Column(Text)
    url = Column(Text)
    api_type = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    raw_documents = relationship("RawDocument", back_populates="source")


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    content_type = Column(Text)
    content = Column(Text)  # Raw JSON snapshot
    hash = Column(Text)

    source = relationship("Source", back_populates="raw_documents")


class NRHPPoint(Base):
    __tablename__ = "nrhp_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nris_refnum = Column(Text, unique=True, nullable=True)
    resname = Column(Text)
    state = Column(Text)
    county = Column(Text)
    status = Column(Text)
    is_nhl = Column(Text)  # Store raw, normalize later
    nara_url = Column(Text)
    edit_date = Column(Text)
    source = Column(Text)
    lon = Column(Float)
    lat = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Target(Base):
    __tablename__ = "targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text)
    target_type = Column(Text)
    lon = Column(Float)
    lat = Column(Float)
    black_sky_score = Column(Integer, default=0)
    confidence = Column(Float, default=0.5)
    review_status = Column(Text, default="unreviewed")  # unreviewed|pursue|monitor|archive
    review_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    flags = relationship("TargetFlag", back_populates="target", uselist=False)


class TargetFlag(Base):
    __tablename__ = "target_flags"

    target_id = Column(UUID(as_uuid=True), ForeignKey("targets.id"), primary_key=True)
    nrhp_near_count_1km = Column(Integer)
    nrhp_min_distance_m = Column(Float)
    nrhp_has_nhl_nearby_1km = Column(Boolean)
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    target = relationship("Target", back_populates="flags")
