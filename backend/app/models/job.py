from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False, default="staging")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    terraform_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    kubernetes_manifest: Mapped[str | None] = mapped_column(Text, nullable=True)
