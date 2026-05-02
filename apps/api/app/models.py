from datetime import datetime
import json
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class JsonListMixin:
    @staticmethod
    def encode_list(values: Optional[List[str]]) -> str:
        return json.dumps(values or [], ensure_ascii=False)

    @staticmethod
    def decode_list(value: Optional[str]) -> List[str]:
        if not value:
            return []
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []


class Job(Base, JsonListMixin):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, default=lambda: new_id("up"))
    uploader_id = Column(String(128), nullable=False, default="internal-user")
    original_file_path = Column(String(1024), nullable=False)
    original_hash = Column(String(128), nullable=False, index=True)
    scale = Column(Integer, nullable=False)
    mode = Column(String(32), nullable=False)
    scene = Column(String(32), nullable=False, default="product")
    status = Column(String(32), nullable=False, default="queued", index=True)
    warnings_json = Column("warnings", Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = relationship("Result", back_populates="job", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="job", cascade="all, delete-orphan")

    @property
    def warnings(self) -> List[str]:
        return self.decode_list(self.warnings_json)

    @warnings.setter
    def warnings(self, values: List[str]) -> None:
        self.warnings_json = self.encode_list(values)


class Result(Base):
    __tablename__ = "results"

    id = Column(String(64), primary_key=True, default=lambda: new_id("res"))
    job_id = Column(String(64), ForeignKey("jobs.id"), nullable=False, index=True)
    result_type = Column(String(32), nullable=False)
    file_path = Column(String(1024), nullable=False)
    thumbnail_path = Column(String(1024), nullable=False)
    model_name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=False)
    quality_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(32), nullable=False, default="low")

    job = relationship("Job", back_populates="results")
    feedback = relationship("Feedback", back_populates="selected_result")


class Feedback(Base, JsonListMixin):
    __tablename__ = "feedback"

    id = Column(String(64), primary_key=True, default=lambda: new_id("fb"))
    job_id = Column(String(64), ForeignKey("jobs.id"), nullable=False, index=True)
    selected_result_id = Column(String(64), ForeignKey("results.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    usable = Column(Boolean, nullable=False)
    issues_json = Column("issues", Text, nullable=False, default="[]")
    comment = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    job = relationship("Job", back_populates="feedback")
    selected_result = relationship("Result", back_populates="feedback")

    @property
    def issues(self) -> List[str]:
        return self.decode_list(self.issues_json)

    @issues.setter
    def issues(self, values: List[str]) -> None:
        self.issues_json = self.encode_list(values)
