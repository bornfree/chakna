"""
Minimal configuration loader for Chakna project.
Automatically adapts to any YAML structure without code changes.
"""

import os
import yaml
from pathlib import Path


class ConfigLoader:
    """Minimal configuration loader that auto-adapts to YAML structure."""
    
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key_path, default=None):
        """
        Get a config value using dot notation (e.g., 'redis.host').
        Supports environment variable overrides using uppercase path.
        """
        # Check for environment variable override first
        env_var = key_path.upper().replace('.', '_')
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Auto-convert types
            if env_value.isdigit():
                return int(env_value)
            try:
                return float(env_value)
            except ValueError:
                if env_value.lower() in ('true', 'false'):
                    return env_value.lower() == 'true'
                return env_value
        
        # Get from config file
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value


# Global config instance
_config_instance = None

def get_config():
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance

def reload_config(config_path=None):
    """Reload the global configuration instance."""
    global _config_instance
    _config_instance = ConfigLoader(config_path)