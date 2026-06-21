"""Configuration loading and override helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

Config = dict[str, Any]
OverrideInput = Mapping[str, Any] | Sequence[str]


class ConfigError(ValueError):
    """Raised when a configuration file or override cannot be interpreted."""


def load_config(path: str | Path, overrides: OverrideInput | None = None) -> Config:
    """Load a YAML configuration file and optionally merge dotted-key overrides."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML config: {config_path}") from exc

    if not isinstance(loaded, dict):
        raise ConfigError(f"Config root must be a mapping: {config_path}")

    config = deepcopy(loaded)
    if overrides:
        config = apply_overrides(config, overrides)
    return config


def apply_overrides(config: Mapping[str, Any], overrides: OverrideInput) -> Config:
    """Return a copy of config with CLI-style dotted-key overrides applied."""

    merged = deepcopy(dict(config))
    for key, value in _iter_overrides(overrides):
        _set_dotted_value(merged, key, value)
    return merged


def _iter_overrides(overrides: OverrideInput) -> list[tuple[str, Any]]:
    if isinstance(overrides, Mapping):
        return [(str(key), value) for key, value in overrides.items()]

    parsed: list[tuple[str, Any]] = []
    for override in overrides:
        if "=" not in override:
            raise ConfigError(f"Override must use KEY=VALUE syntax: {override}")
        key, raw_value = override.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigError(f"Override key cannot be empty: {override}")
        try:
            value = yaml.safe_load(raw_value)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid override value for {key}: {raw_value}") from exc
        parsed.append((key, value))
    return parsed


def _set_dotted_value(config: Config, dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    if any(part == "" for part in parts):
        raise ConfigError(f"Override key has an empty path segment: {dotted_key}")

    current: Config = config
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            current[part] = {}
            existing = current[part]
        if not isinstance(existing, dict):
            raise ConfigError(
                f"Cannot set {dotted_key}: {part} is not a mapping in the base config"
            )
        current = existing
    current[parts[-1]] = value
