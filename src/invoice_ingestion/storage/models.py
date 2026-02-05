"""SQLAlchemy ORM models for the invoice-ingestion pipeline."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Extraction(Base):
    __tablename__ = "extractions"

    extraction_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    blob_name: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(50), default="processing")  # processing, pending_review, accepted, rejected
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commodity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    utility_provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Correction(Base):
    __tablename__ = "corrections"

    correction_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    extraction_id: Mapped[UUID] = mapped_column(ForeignKey("extractions.extraction_id"), index=True)
    field_path: Mapped[str] = mapped_column(String(500))
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str] = mapped_column(Text)
    correction_type: Mapped[str] = mapped_column(String(50))  # value_change, missing_field, wrong_classification, split_merge
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrector_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invoice_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # utility, commodity, fingerprint
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FormatFingerprint(Base):
    __tablename__ = "format_fingerprints"

    fingerprint_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    utility: Mapped[str] = mapped_column(String(200), index=True)
    commodity: Mapped[str] = mapped_column(String(50))
    detection_signals_json: Mapped[dict] = mapped_column(JSON)
    known_issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_prompt_additions: Mapped[str | None] = mapped_column(Text, nullable=True)
    accuracy_history: Mapped[dict] = mapped_column(JSON, default=dict)
    invoices_processed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DriftEvent(Base):
    __tablename__ = "drift_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    extraction_id: Mapped[UUID] = mapped_column(ForeignKey("extractions.extraction_id"), index=True)
    previous_extraction_id: Mapped[UUID] = mapped_column(ForeignKey("extractions.extraction_id"))
    drift_fields_json: Mapped[dict] = mapped_column(JSON)
    fatal_drift: Mapped[bool] = mapped_column(Boolean, default=False)
    cause_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    extraction_id: Mapped[UUID] = mapped_column(ForeignKey("extractions.extraction_id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
