"""
CortexFlow Plugin System - Dynamic agent and tool extensions.

Plugins can register:
    - New agents (extending BaseAgent)
    - New providers (extending BaseLLMProvider)
    - New workflow stages
    - Custom output formatters
    - Pipeline middleware (pre/post hooks)

Plugin discovery:
    - plugins/ directory at project root
    - Each subdirectory must contain manifest.yaml + plugin.py
"""

import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Type, Any
import yaml

logger = logging.getLogger("cortexflow.plugins")


class PluginError(Exception):
    pass


class Plugin:
    """Base plugin interface. All CortexFlow plugins must subclass this."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""

    def __init__(self, manifest: dict):
        self.manifest = manifest

    def initialize(self, engine: Any):
        """Called when the plugin is loaded into the engine."""
        pass

    def teardown(self):
        """Called when the plugin is being unloaded."""
        pass

    def get_agents(self) -> Dict[str, Type]:
        """Return dict of {name: agent_class} this plugin provides."""
        return {}

    def get_providers(self) -> Dict[str, Type]:
        """Return dict of {name: provider_class} this plugin provides."""
        return {}

    def get_workflow_stages(self) -> Dict[str, Any]:
        """Return additional workflow stage handlers."""
        return {}


class PluginManager:
    """Discovers, loads, and manages CortexFlow plugins."""

    def __init__(self, plugins_dir: str = "./plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.loaded: Dict[str, Plugin] = {}
        self.disabled: List[str] = []

    def discover(self) -> List[dict]:
        """Discover all plugins in the plugins directory."""
        if not self.plugins_dir.exists():
            logger.info(f"No plugins directory at {self.plugins_dir}")
            return []

        discovered = []
        for entry in self.plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.yaml"
            plugin_file = entry / "plugin.py"
            if not manifest_path.exists() or not plugin_file.exists():
                continue
            try:
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                manifest["_path"] = str(entry)
                discovered.append(manifest)
            except Exception as e:
                logger.warning(f"Failed to read manifest for {entry.name}: {e}")
        return discovered

    def load(self, manifest: dict) -> Plugin:
        """Load a single plugin by manifest."""
        name = manifest.get("name")
        if not name:
            raise PluginError("Plugin manifest missing 'name'")
        if name in self.disabled:
            logger.info(f"Plugin {name} is disabled")
            return None
        if name in self.loaded:
            return self.loaded[name]

        plugin_path = Path(manifest["_path"]) / "plugin.py"
        spec = importlib.util.spec_from_file_location(f"cortexflow_plugin_{name}", plugin_path)
        if not spec or not spec.loader:
            raise PluginError(f"Failed to load plugin spec: {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Plugin subclass in module
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                plugin_class = attr
                break

        if not plugin_class:
            raise PluginError(f"No Plugin subclass found in {name}")

        plugin = plugin_class(manifest)
        self.loaded[name] = plugin
        logger.info(f"Loaded plugin: {name} v{plugin.version}")
        return plugin

    def load_all(self) -> int:
        """Discover and load all available plugins. Returns count."""
        manifests = self.discover()
        count = 0
        for m in manifests:
            try:
                if self.load(m):
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load {m.get('name')}: {e}")
        return count

    def initialize_all(self, engine: Any):
        """Initialize all loaded plugins with engine reference."""
        for plugin in self.loaded.values():
            try:
                plugin.initialize(engine)
            except Exception as e:
                logger.error(f"Failed to initialize {plugin.name}: {e}")

    def get_all_agents(self) -> Dict[str, Type]:
        """Aggregate agents from all plugins."""
        agents = {}
        for plugin in self.loaded.values():
            agents.update(plugin.get_agents())
        return agents

    def get_all_providers(self) -> Dict[str, Type]:
        """Aggregate providers from all plugins."""
        providers = {}
        for plugin in self.loaded.values():
            providers.update(plugin.get_providers())
        return providers

    def disable(self, name: str):
        """Disable a plugin by name."""
        if name not in self.disabled:
            self.disabled.append(name)
        if name in self.loaded:
            try:
                self.loaded[name].teardown()
            except Exception:
                pass
            del self.loaded[name]

    def list_loaded(self) -> List[dict]:
        """Return info about all loaded plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "agents": list(p.get_agents().keys()),
                "providers": list(p.get_providers().keys()),
            }
            for p in self.loaded.values()
        ]
