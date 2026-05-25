"""
CortexFlow Repositories - Data access layer for storage models.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from .models import User, APIKey, Session, PipelineRun, TokenUsage, AuditLog, JobStatus, UserRole


class UserRepository:
    """User account management."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${h}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            salt, h = hashed.split("$", 1)
            return hashlib.sha256((salt + password).encode()).hexdigest() == h
        except (ValueError, AttributeError):
            return False

    def create(self, username: str, email: str, password: str, role: UserRole = UserRole.ANALYST) -> User:
        user = User(
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            role=role,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_username(self, username: str) -> Optional[User]:
        return self.session.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)
        if user and user.is_active and self.verify_password(password, user.password_hash):
            user.last_login = datetime.utcnow()
            return user
        return None

    def create_api_key(self, user_id: int, name: str, expires_days: Optional[int] = None) -> tuple:
        """Create an API key. Returns (key_plaintext, APIKey instance)."""
        plaintext = f"cf_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        prefix = plaintext[:12]
        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            expires_at=expires_at,
        )
        self.session.add(api_key)
        self.session.flush()
        return plaintext, api_key

    def verify_api_key(self, plaintext: str) -> Optional[User]:
        key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        api_key = self.session.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()
        if not api_key:
            return None
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        api_key.last_used = datetime.utcnow()
        api_key.use_count += 1
        return api_key.user


class SessionRepository:
    """Analysis session management."""

    def __init__(self, db_session):
        self.session = db_session

    def create(self, name: str, user_id: Optional[int] = None, description: str = "") -> Session:
        s = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
        )
        self.session.add(s)
        self.session.flush()
        return s

    def get(self, session_id: str) -> Optional[Session]:
        return self.session.query(Session).filter(Session.id == session_id).first()

    def list_by_user(self, user_id: int, limit: int = 100) -> List[Session]:
        return (
            self.session.query(Session)
            .filter(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete(self, session_id: str) -> bool:
        s = self.get(session_id)
        if not s:
            return False
        self.session.delete(s)
        return True


class PipelineRepository:
    """Pipeline run history."""

    def __init__(self, db_session):
        self.session = db_session

    def create(self, session_id: str, name: str, pipeline_type: str = "default", config: dict = None) -> PipelineRun:
        run = PipelineRun(
            id=str(uuid.uuid4()),
            session_id=session_id,
            name=name,
            pipeline_type=pipeline_type,
            config_json=config or {},
        )
        self.session.add(run)
        self.session.flush()
        return run

    def update_status(self, run_id: str, status: JobStatus, error: Optional[str] = None):
        run = self.session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run:
            run.status = status
            if status == JobStatus.RUNNING and not run.started_at:
                run.started_at = datetime.utcnow()
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                run.completed_at = datetime.utcnow()
                if run.started_at:
                    run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
            if error:
                run.error = error

    def store_result(self, run_id: str, result: dict, risk_score: Optional[float] = None):
        run = self.session.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if run:
            run.result_json = result
            if risk_score is not None:
                run.risk_score = risk_score

    def list_recent(self, limit: int = 50) -> List[PipelineRun]:
        return (
            self.session.query(PipelineRun)
            .order_by(PipelineRun.started_at.desc().nullslast())
            .limit(limit)
            .all()
        )


class TokenUsageRepository:
    """Token usage history and aggregation."""

    def __init__(self, db_session):
        self.session = db_session

    def log(self, run_id: str, agent: str, provider: str, model: str,
            prompt: int, completion: int, cost: float = 0.0, **kwargs):
        usage = TokenUsage(
            pipeline_run_id=run_id,
            agent_name=agent,
            provider=provider,
            model=model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            cached_tokens=kwargs.get("cached_tokens", 0),
            reasoning_tokens=kwargs.get("reasoning_tokens", 0),
            cost_usd=cost,
        )
        self.session.add(usage)
        self.session.flush()
        return usage

    def aggregate_by_provider(self, start: Optional[datetime] = None) -> dict:
        from sqlalchemy import func
        q = self.session.query(
            TokenUsage.provider,
            func.sum(TokenUsage.prompt_tokens).label("prompt"),
            func.sum(TokenUsage.completion_tokens).label("completion"),
            func.sum(TokenUsage.cost_usd).label("cost"),
            func.count(TokenUsage.id).label("calls"),
        )
        if start:
            q = q.filter(TokenUsage.timestamp >= start)
        return {
            row.provider: {
                "prompt_tokens": int(row.prompt or 0),
                "completion_tokens": int(row.completion or 0),
                "total_cost_usd": float(row.cost or 0),
                "calls": int(row.calls or 0),
            }
            for row in q.group_by(TokenUsage.provider).all()
        }

    def aggregate_by_agent(self) -> dict:
        from sqlalchemy import func
        rows = (
            self.session.query(
                TokenUsage.agent_name,
                func.sum(TokenUsage.prompt_tokens + TokenUsage.completion_tokens).label("total"),
                func.count(TokenUsage.id).label("calls"),
            )
            .group_by(TokenUsage.agent_name)
            .all()
        )
        return {
            row.agent_name: {
                "total_tokens": int(row.total or 0),
                "calls": int(row.calls or 0),
            }
            for row in rows
        }
