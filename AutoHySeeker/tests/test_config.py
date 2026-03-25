"""Tests for src/configs.py — TOML config loading edge cases.

Covers:
- Default values when TOML files are missing
- Values correctly loaded from real configs/
- Environment-variable override via ${VAR:-default} syntax
- Singleton / lazy-loading behaviour
- _expand_path helper
- All public classes and factory functions
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── import smoke ──────────────────────────────────────────────────────────────

class TestConfigsImport:
    def test_module_imports(self) -> None:
        from src import configs  # noqa: F401

    def test_all_exports_available(self) -> None:
        import src.configs as configs_mod
        for name in configs_mod.__all__:
            assert hasattr(configs_mod, name), f"Missing: {name}"


# ── Settings tests ────────────────────────────────────────────────────────────

class TestSettings:
    def test_defaults_when_no_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When configs dir is missing, Settings.load() returns defaults."""
        import src.configs as configs_mod
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path / "nonexistent")
        # Reset singleton
        configs_mod._settings = None
        s = configs_mod.Settings.load()
        assert s.general.project_name == "AutoHySeeker"
        assert s.api.port == 8100
        assert s.api.prefix == "/api/v1"

    def test_loads_from_real_settings_toml(self) -> None:
        """Settings loaded from the real settings.toml match expected values."""
        from src.configs import Settings

        s = Settings.load()
        assert s.general.project_name == "AutoHySeeker"
        assert s.api.port == 8100
        assert s.api.host == "0.0.0.0"

    def test_partial_toml_uses_defaults_for_missing_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A TOML with only [general] still gives ApiSettings defaults."""
        import src.configs as configs_mod

        toml_content = b"[general]\nproject_name = 'TestProject'\n"
        (tmp_path / "settings.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._settings = None
        s = configs_mod.Settings.load()
        assert s.general.project_name == "TestProject"
        assert s.api.port == 8100  # default

    def test_custom_api_port(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod

        toml_content = b"[api]\nport = 9999\n"
        (tmp_path / "settings.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._settings = None
        s = configs_mod.Settings.load()
        assert s.api.port == 9999


# ── LLMConfig tests ───────────────────────────────────────────────────────────

class TestLLMConfig:
    def test_defaults_when_no_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path / "no_dir")
        configs_mod._llm_config = None
        c = configs_mod.LLMConfig.load()
        assert c.default.model == "anthropic/claude-sonnet-4-6"
        assert c.default.temperature == 0.1
        assert c.fallback.model == "anthropic/claude-opus-4-6"

    def test_loads_from_real_agent_models_toml(self) -> None:
        from src.configs import LLMConfig

        c = LLMConfig.load()
        assert "claude" in c.default.model.lower()
        assert c.default.temperature >= 0.0
        assert c.default.max_tokens > 0
        assert "http" in c.default.base_url

    def test_custom_model_name(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod

        toml_content = b"[defaults]\nmodel = 'custom/my-model'\ntemperature = 0.7\n"
        (tmp_path / "agent_models.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._llm_config = None
        c = configs_mod.LLMConfig.load()
        assert c.default.model == "custom/my-model"
        assert c.default.temperature == 0.7
        assert c.fallback.model == "anthropic/claude-opus-4-6"  # default

    def test_fallback_model_customisable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod

        toml_content = b"[defaults]\nfallback_model = 'other/fallback-model'\n"
        (tmp_path / "agent_models.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._llm_config = None
        c = configs_mod.LLMConfig.load()
        assert c.fallback.model == "other/fallback-model"


# ── MicroHySeekerConfig tests ─────────────────────────────────────────────────

class TestMicroHySeekerConfig:
    def test_defaults_when_no_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path / "no_dir")
        configs_mod._mhs_config = None
        m = configs_mod.MicroHySeekerConfig.load()
        assert m.engine.mode == "file"
        assert m.paths.data_dir == ""

    def test_loads_from_real_toml(self) -> None:
        from src.configs import MicroHySeekerConfig

        m = MicroHySeekerConfig.load()
        assert m.engine.mode == "file"
        # data_dir should be a resolved path string
        assert isinstance(m.paths.data_dir, str)

    def test_env_var_expansion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """${MY_DATA_DIR:-fallback} should expand using the env variable."""
        import src.configs as configs_mod

        toml_content = (
            b"[paths]\n"
            b"data_dir = '${AUTOHYSEEKER_TEST_DATA_DIR:-./data}'\n"
            b"[engine]\nmode = 'file'\n"
        )
        (tmp_path / "microhyseeker.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._mhs_config = None
        monkeypatch.delenv("AUTOHYSEEKER_TEST_DATA_DIR", raising=False)
        m = configs_mod.MicroHySeekerConfig.load()
        # Should resolve './data' relative to tmp_path.parent (the "AutoHySeeker/" dir)
        assert m.paths.data_dir.endswith("data") or "data" in m.paths.data_dir

    def test_env_var_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When env var is set, its value should be used instead of the default."""
        import src.configs as configs_mod

        toml_content = (
            b"[paths]\n"
            b"data_dir = '${AUTOHYSEEKER_TEST_DATA_DIR:-./data_default}'\n"
        )
        (tmp_path / "microhyseeker.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._mhs_config = None
        monkeypatch.setenv("AUTOHYSEEKER_TEST_DATA_DIR", "/custom/data/path")
        m = configs_mod.MicroHySeekerConfig.load()
        assert Path(m.paths.data_dir).is_absolute()
        assert Path(m.paths.data_dir).as_posix().endswith("/custom/data/path")

    def test_engine_mode_customisable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod

        toml_content = b"[engine]\nmode = 'api'\n"
        (tmp_path / "microhyseeker.toml").write_bytes(toml_content)
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        configs_mod._mhs_config = None
        m = configs_mod.MicroHySeekerConfig.load()
        assert m.engine.mode == "api"


# ── Singleton / lazy-loading tests ───────────────────────────────────────────

class TestSingletons:
    def test_get_settings_returns_same_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        configs_mod._settings = None
        s1 = configs_mod.get_settings()
        s2 = configs_mod.get_settings()
        assert s1 is s2

    def test_get_llm_config_returns_same_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        configs_mod._llm_config = None
        c1 = configs_mod.get_llm_config()
        c2 = configs_mod.get_llm_config()
        assert c1 is c2

    def test_get_microhyseeker_config_returns_same_instance(self) -> None:
        import src.configs as configs_mod
        configs_mod._mhs_config = None
        m1 = configs_mod.get_microhyseeker_config()
        m2 = configs_mod.get_microhyseeker_config()
        assert m1 is m2

    def test_reset_singleton_reloads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Nulling the private variable forces a fresh load on next call."""
        import src.configs as configs_mod
        configs_mod._settings = None
        s1 = configs_mod.get_settings()
        configs_mod._settings = None  # reset
        s2 = configs_mod.get_settings()
        # Different objects but same values
        assert s1 is not s2
        assert s1.api.port == s2.api.port


# ── _expand_path helper tests ─────────────────────────────────────────────────

class TestExpandPath:
    def test_absolute_path_unchanged(self, tmp_path: Path) -> None:
        from src.configs import _expand_path  # type: ignore[attr-defined]

        absolute = "/absolute/path/to/data"
        result = _expand_path(absolute, tmp_path)
        assert Path(result).is_absolute()
        assert Path(result).as_posix().endswith("/absolute/path/to/data")

    def test_relative_path_resolved_against_base(self, tmp_path: Path) -> None:
        from src.configs import _expand_path  # type: ignore[attr-defined]

        result = _expand_path("../data", tmp_path)
        # Should resolve relative to tmp_path
        assert Path(result).is_absolute()

    def test_env_var_substitution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.configs import _expand_path  # type: ignore[attr-defined]

        monkeypatch.setenv("TEST_EXPAND_DIR", "/env/data")
        result = _expand_path("${TEST_EXPAND_DIR}", tmp_path)
        assert Path(result).is_absolute()
        assert Path(result).as_posix().endswith("/env/data")

    def test_env_var_default_when_unset(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.configs import _expand_path  # type: ignore[attr-defined]

        monkeypatch.delenv("UNSET_TEST_VAR_XYZ", raising=False)
        result = _expand_path("${UNSET_TEST_VAR_XYZ:-/fallback/dir}", tmp_path)
        assert Path(result).is_absolute()
        assert Path(result).as_posix().endswith("/fallback/dir")

    def test_env_var_overrides_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.configs import _expand_path  # type: ignore[attr-defined]

        monkeypatch.setenv("OVERRIDE_TEST_VAR", "/override/path")
        result = _expand_path("${OVERRIDE_TEST_VAR:-/ignored/default}", tmp_path)
        assert Path(result).is_absolute()
        assert Path(result).as_posix().endswith("/override/path")


# ── _load_toml helper tests ───────────────────────────────────────────────────

class TestLoadToml:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        result = configs_mod._load_toml("nonexistent_file.toml")
        assert result == {}

    def test_valid_toml_loaded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.configs as configs_mod
        monkeypatch.setattr(configs_mod, "_CONFIGS_DIR", tmp_path)
        (tmp_path / "test.toml").write_bytes(b"[section]\nkey = 'value'\n")
        result = configs_mod._load_toml("test.toml")
        assert result == {"section": {"key": "value"}}
