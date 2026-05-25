"""
CortexFlow SQLAlchemy Models - Persistent state schema.

Tables:
    users           User accounts with hashed credentials
    api_keys        API keys for programmatic access
    sessions        Analysis sessions
    pipeline_runs   Per-pipeline execution records
    token_usage     Token consumption history
    audit_log       Compliance audit trail
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.ANALYST)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    prefix = Column(String(16))  # First chars for display: cf_xxxxxx
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)

    user = relationship("User", back_populates="api_keys")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    pipeline_runs = relationship("PipelineRun", back_populates="session", cascade="all, delete-orphan")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    pipeline_type = Column(String(64), default="default")
    config_json = Column(JSON, default=dict)
    result_json = Column(JSON, nullable=True)
    risk_score = Column(Float, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)

    error = Column(Text, nullable=True)

    session = relationship("Session", back_populates="pipeline_runs")
    token_usage = relationship("TokenUsage", back_populates="pipeline_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_pipeline_runs_status_created", "status", "started_at"),
    )


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(String(64), ForeignKey("pipeline_runs.id", ondelete="CASCADE"))
    agent_name = Column(String(64), nullable=False)
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cached_tokens = Column(Integer, default=0)
    reasoning_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    pipeline_run = relationship("PipelineRun", back_populates="token_usage")

    __table_args__ = (
        Index("ix_token_usage_provider_timestamp", "provider", "timestamp"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_log_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_log_action_timestamp", "action", "timestamp"),
    )
