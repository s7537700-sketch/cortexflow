"""Tests for storage layer."""

import pytest
from datetime import datetime, timedelta


class TestUserRepository:
    def test_password_hashing(self):
        from storage.repositories import UserRepository
        hashed = UserRepository.hash_password("secret123")
        assert UserRepository.verify_password("secret123", hashed)
        assert not UserRepository.verify_password("wrong", hashed)
        assert "$" in hashed  # salt$hash format

    def test_create_and_authenticate(self):
        from storage.database import Database
        from storage.repositories import UserRepository

        db = Database("sqlite:///:memory:")
        db.connect()
        db.create_all()

        with db.session() as session:
            repo = UserRepository(session)
            user = repo.create("alice", "alice@test.com", "pass123")
            assert user.username == "alice"
            assert user.email == "alice@test.com"

        with db.session() as session:
            repo = UserRepository(session)
            authenticated = repo.authenticate("alice", "pass123")
            assert authenticated is not None
            assert authenticated.username == "alice"
            wrong = repo.authenticate("alice", "badpass")
            assert wrong is None


class TestAPIKeys:
    def test_api_key_lifecycle(self):
        from storage.database import Database
        from storage.repositories import UserRepository

        db = Database("sqlite:///:memory:")
        db.connect()
        db.create_all()

        with db.session() as session:
            repo = UserRepository(session)
            user = repo.create("bob", "bob@test.com", "pass")
            plaintext, key_obj = repo.create_api_key(user.id, "test-key", expires_days=30)
            assert plaintext.startswith("cf_")
            assert key_obj.prefix in plaintext

        with db.session() as session:
            repo = UserRepository(session)
            verified = repo.verify_api_key(plaintext)
            assert verified is not None
            assert verified.username == "bob"


class TestPipelineRepository:
    def test_pipeline_lifecycle(self):
        from storage.database import Database
        from storage.repositories import (
            UserRepository, SessionRepository, PipelineRepository
        )
        from storage.models import JobStatus

        db = Database("sqlite:///:memory:")
        db.connect()
        db.create_all()

        with db.session() as sess:
            users = UserRepository(sess)
            sessions = SessionRepository(sess)
            pipelines = PipelineRepository(sess)

            user = users.create("charlie", "c@test.com", "pwd")
            s = sessions.create("test session", user_id=user.id)
            run = pipelines.create(s.id, "first run")
            assert run.status == JobStatus.QUEUED

            pipelines.update_status(run.id, JobStatus.RUNNING)
            pipelines.update_status(run.id, JobStatus.COMPLETED)
            pipelines.store_result(run.id, {"finding": "test"}, risk_score=7.5)

        with db.session() as sess:
            pipelines = PipelineRepository(sess)
            recent = pipelines.list_recent(limit=10)
            assert len(recent) >= 1
            assert recent[0].risk_score == 7.5


class TestTokenUsage:
    def test_aggregate_by_provider(self):
        from storage.database import Database
        from storage.repositories import (
            UserRepository, SessionRepository, PipelineRepository, TokenUsageRepository
        )

        db = Database("sqlite:///:memory:")
        db.connect()
        db.create_all()

        with db.session() as sess:
            users = UserRepository(sess)
            sessions = SessionRepository(sess)
            pipelines = PipelineRepository(sess)
            tokens = TokenUsageRepository(sess)

            user = users.create("dan", "d@test.com", "pwd")
            s = sessions.create("test", user_id=user.id)
            run = pipelines.create(s.id, "test run")

            tokens.log(run.id, "agent1", "mimo", "mimo-v2.5", 1000, 500, cost=0.001)
            tokens.log(run.id, "agent2", "mimo", "mimo-v2.5", 2000, 1000, cost=0.003)
            tokens.log(run.id, "agent3", "anthropic", "claude-sonnet-4.5", 500, 250, cost=0.005)

        with db.session() as sess:
            tokens = TokenUsageRepository(sess)
            agg = tokens.aggregate_by_provider()
            assert "mimo" in agg
            assert "anthropic" in agg
            assert agg["mimo"]["calls"] == 2
            assert agg["mimo"]["prompt_tokens"] == 3000
