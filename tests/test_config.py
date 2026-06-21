from pathlib import Path

import pytest

from vrptw_hybrid.utils.config import ConfigError, apply_overrides, load_config

ROOT = Path(__file__).resolve().parents[1]


def test_load_default_config() -> None:
    config = load_config(ROOT / "configs" / "default.yaml")

    assert config["seed"] == 42
    assert config["objective"]["vehicle_weight"] == 100000.0
    assert config["solver"]["time_limit_sec"] == 60
    assert config["ablation"]["name"] == "default"
    assert config["alns"]["disabled_destroy_operators"] == []
    assert config["alns"]["candidate_neighbor_size"] == 25
    assert config["experiment"]["seeds"] == [1, 2, 3, 4, 5]


def test_load_config_applies_cli_style_overrides() -> None:
    config = load_config(
        ROOT / "configs" / "default.yaml",
        overrides=[
            "seed=7",
            "solver.time_limit_sec=30",
            "experiment.seeds=[10, 11]",
            "alns.exploration_floor=0.1",
        ],
    )

    assert config["seed"] == 7
    assert config["solver"]["time_limit_sec"] == 30
    assert config["experiment"]["seeds"] == [10, 11]
    assert config["alns"]["exploration_floor"] == 0.1


def test_load_ablation_config_lists_recommended_groups() -> None:
    config = load_config(ROOT / "configs" / "ablation.yaml")

    names = {ablation["name"] for ablation in config["experiment"]["ablations"]}

    assert config["ablation"]["name"] == "alns_mosade_adaptive"
    assert "alns_mosade_no_shaw_destroy" in names
    assert "alns_mosade_no_regret_repair" in names


def test_apply_overrides_does_not_mutate_base_config() -> None:
    base = {"solver": {"time_limit_sec": 60}}

    merged = apply_overrides(base, {"solver.time_limit_sec": 15})

    assert base["solver"]["time_limit_sec"] == 60
    assert merged["solver"]["time_limit_sec"] == 15


def test_missing_config_file_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(missing)


def test_invalid_override_rejects_non_mapping_parent() -> None:
    base = {"solver": 60}

    with pytest.raises(ConfigError, match="solver is not a mapping"):
        apply_overrides(base, {"solver.time_limit_sec": 15})


def test_invalid_override_requires_key_value_syntax() -> None:
    with pytest.raises(ConfigError, match="KEY=VALUE"):
        apply_overrides({}, ["solver.time_limit_sec"])
