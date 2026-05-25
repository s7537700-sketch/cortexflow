"""Tests for plugin system and authentication."""

import pytest


class TestPluginManager:
    def test_discovery(self):
        from core.plugin_manager import PluginManager
        from pathlib import Path

        manager = PluginManager(plugins_dir=str(Path(__file__).parent.parent / "plugins"))
        manifests = manager.discover()
        assert len(manifests) >= 1
        names = [m["name"] for m in manifests]
        assert "example_plugin" in names

    def test_load_example_plugin(self):
        from core.plugin_manager import PluginManager
        from pathlib import Path

        manager = PluginManager(plugins_dir=str(Path(__file__).parent.parent / "plugins"))
        count = manager.load_all()
        assert count >= 1
        listed = manager.list_loaded()
        plugin_names = [p["name"] for p in listed]
        assert "example_plugin" in plugin_names

    def test_aggregate_agents(self):
        from core.plugin_manager import PluginManager
        from pathlib import Path

        manager = PluginManager(plugins_dir=str(Path(__file__).parent.parent / "plugins"))
        manager.load_all()
        agents = manager.get_all_agents()
        assert "example_hello" in agents


class TestAuth:
    def test_token_round_trip(self):
        from api.auth import AuthService

        auth = AuthService(secret_key="test-secret-key")
        token = auth.create_token(user_id=42, role="analyst")
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["role"] == "analyst"

    def test_token_tampering_rejected(self):
        from api.auth import AuthService

        auth = AuthService(secret_key="test-secret-key")
        token = auth.create_token(user_id=42, role="analyst")
        # Tamper with payload
        tampered = "AAAA." + token.split(".", 1)[1]
        assert auth.verify_token(tampered) is None


class TestRBAC:
    def test_admin_has_all_permissions(self):
        from api.auth import RBACService
        rbac = RBACService()
        assert rbac.has_permission("admin", "users.create")
        assert rbac.has_permission("admin", "audit.read")

    def test_viewer_limited(self):
        from api.auth import RBACService
        rbac = RBACService()
        assert rbac.has_permission("viewer", "pipelines.read")
        assert not rbac.has_permission("viewer", "pipelines.run")
        assert not rbac.has_permission("viewer", "users.create")

    def test_require_permission_raises(self):
        from api.auth import RBACService, AuthError
        rbac = RBACService()
        with pytest.raises(AuthError):
            rbac.require_permission("viewer", "pipelines.run")
