"""Tests for src/configs.py — TOML loading, env expansion, edge cases."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


# ── _expand_path ──────────────────────────────────────────────────────────────

class TestExpandPath:
    def test_env_var_resolved(self) -> None:
        from src.configs import _expand_path

        with patch.dict(os.environ, {"MY_VAR": "/custom/path"}):
            result = _expand_path("${MY_VAR}/subdir", Path("/base"))
        assert result == str(Path("/custom/path/subdir"))

    def test_env_var_with_default(self) -> None:
        from src.configs import _expand_path

        env = os.environ.copy()
        env.pop("NONEXISTENT_VAR_12345", None)
        with patch.dict(os.environ, env, clear=True):
            result = _expand_path("${NONEXISTENT_VAR_12345:-fallback}", Path("/base"))
        assert "fallback" in result

    def test_relative_path_resolved_against_base(self) -> None:
        from src.configs import _expand_path

        result = _expand_path("relative/dir", Path("/some/base"))
        assert Path(result).is_absolute()

    def test_absolute_path_unchanged(self) -> None:
        from src.configs import _expand_path

        if os.name == "nt":
            result = _expand_path("C:\\absolute\\dir", Path("/base"))
            assert result == "C:\\absolute\\dir"
        else:
            result = _expand_path("/absolute/dir", Path("/base"))
            assert result == "/absolute/dir"


# ── _load_toml ────────────────────────────────────────────────────────────────

class TestLoadToml:
    def test_missing_file_returns_empty(self) -> None:
        from src.configs import _load_toml

        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            assert _load_toml("does_not_exist.toml") == {}

    def test_loads_valid_toml(self, tmp_path: Path) -> None:
        from src.configs import _load_toml

        toml_file = tmp_path / "test.toml"
        toml_file.write_text('[section]\nkey = "value"\n', encoding="utf-8")
        with patch("src.configs._CONFIGS_DIR", tmp_path):
            data = _load_toml("test.toml")
        assert data["section"]["key"] == "value"


# ── Settings ──────────────────────────────────────────────────────────────────

class TestSettings:
    def test_defaults_when_no_file(self) -> None:
        from src.configs import GeneralSettings, Settings

        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            s = Settings.load()
        assert s.general.project_name == "AutoHySeeker"
        assert s.api.port == 8100

    def test_loads_from_toml(self, tmp_path: Path) -> None:
        from src.configs import Settings

        toml_file = tmp_path / "settings.toml"
        toml_file.write_text(
            textwrap.dedent("""\
                [general]
                project_name = "CustomProject"
                version = "2.0.0"
                log_level = "DEBUG"

                [api]
                host = "127.0.0.1"
                port = 9090
                prefix = "/v2"
            """),
            encoding="utf-8",
        )
        with patch("src.configs._CONFIGS_DIR", tmp_path):
            s = Settings.load()
        assert s.general.project_name == "CustomProject"
        assert s.api.port == 9090

    def test_partial_toml(self, tmp_path: Path) -> None:
        from src.configs import Settings

        toml_file = tmp_path / "settings.toml"
        toml_file.write_text("[general]\nlog_level = 'WARN'\n", encoding="utf-8")
        with patch("src.configs._CONFIGS_DIR", tmp_path):
            s = Settings.load()
        assert s.general.log_level == "WARN"
        assert s.api.host == "0.0.0.0"  # default preserved


# ── LLMConfig ─────────────────────────────────────────────────────────────────

class TestLLMConfig:
    def test_defaults_when_no_file(self) -> None:
        from src.configs import LLMConfig

        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            c = LLMConfig.load()
        assert c.default.provider == "openai"
        assert c.fallback.model == "anthropic/claude-opus-4-6"

    def test_loads_from_toml(self, tmp_path: Path) -> None:
        from src.configs import LLMConfig

        toml_file = tmp_path / "llm_config.toml"
        toml_file.write_text(
            textwrap.dedent("""\
                [default]
                provider = "anthropic"
                model = "custom-model"
                temperature = 0.5
                max_tokens = 2048
                base_url = "https://example.com"
                api_key_env = "CUSTOM_KEY"

                [fallback]
                model = "fallback-model"
            """),
            encoding="utf-8",
        )
        with patch("src.configs._CONFIGS_DIR", tmp_path):
            c = LLMConfig.load()
        assert c.default.model == "custom-model"
        assert c.default.temperature == 0.5
        assert c.fallback.model == "fallback-model"


# ── MicroHySeekerConfig ──────────────────────────────────────────────────────

class TestMicroHySeekerConfig:
    def test_defaults_when_no_file(self) -> None:
        from src.configs import MicroHySeekerConfig

        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            c = MicroHySeekerConfig.load()
        assert c.engine.mode == "file"

    def test_env_expansion(self, tmp_path: Path) -> None:
        from src.configs import MicroHySeekerConfig

        toml_file = tmp_path / "microhyseeker.toml"
        toml_file.write_text(
            textwrap.dedent("""\
                [paths]
                data_dir = "${TEST_DATA_12345:-./test_data}"
                config_dir = "./conf"
                logs_dir = "./logs"

                [engine]
                mode = "api"
            """),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.pop("TEST_DATA_12345", None)
        with patch("src.configs._CONFIGS_DIR", tmp_path), patch.dict(os.environ, env, clear=True):
            c = MicroHySeekerConfig.load()
        assert c.engine.mode == "api"
        assert "test_data" in c.paths.data_dir


# ── Singleton accessors ──────────────────────────────────────────────────────

class TestSingletonAccessors:
    def test_get_settings_returns_settings(self) -> None:
        import src.configs as configs_mod

        configs_mod._settings = None
        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            s = configs_mod.get_settings()
        assert s.general.project_name == "AutoHySeeker"
        configs_mod._settings = None  # reset for other tests

    def test_get_llm_config_returns_config(self) -> None:
        import src.configs as configs_mod

        configs_mod._llm_config = None
        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            c = configs_mod.get_llm_config()
        assert c.default.provider == "openai"
        configs_mod._llm_config = None

    def test_get_microhyseeker_config_returns_config(self) -> None:
        import src.configs as configs_mod

        configs_mod._mhs_config = None
        with patch("src.configs._CONFIGS_DIR", Path("/nonexistent")):
            c = configs_mod.get_microhyseeker_config()
        assert c.engine.mode == "file"
        configs_mod._mhs_config = None
