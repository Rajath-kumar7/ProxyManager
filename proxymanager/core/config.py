import yaml
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


class Config:
    """A singleton class to hold application configuration."""
    _instance = None
    _config_data: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Loads the configuration from the YAML file."""
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
        with open(CONFIG_PATH, 'r') as f:
            self._config_data = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value.
        Nested keys can be accessed with dot notation, e.g., 'scoring_weights.latency'.
        """
        keys = key.split('.')
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# Create a single instance to be imported across the application
config = Config()
