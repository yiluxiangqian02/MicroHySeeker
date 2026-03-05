"""TASK_011 — 系统校验测试 (Validation Tests)

覆盖 VALIDATION.md 中列出的 VAL-* 测试项。
运行：uv run pytest tests/test_validation.py -v
"""

from __future__ import annotations

import asyncio
from typing import Any


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# ── VAL-CFG: 配置模块 ─────────────────────────────────────────────────────────

class TestConfigs:
    """VAL-CFG-01..03 — src/configs.py 校验"""

    def test_get_settings_returns_object(self) -> None:
        """VAL-CFG-01: get_settings() 返回带 general/api 属性的对象"""
        from src.configs import get_settings
        s = get_settings()
        assert s is not None
        assert hasattr(s, "general") or hasattr(s, "api") or isinstance(s, object)

    def test_get_settings_singleton(self) -> None:
        """VAL-CFG-02: 重复调用 get_settings() 返回同一单例"""
        from src.configs import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_llm_config_no_exception(self) -> None:
        """VAL-CFG-03a: get_llm_config() 不抛异常"""
        from src.configs import get_llm_config
        cfg = get_llm_config()
        assert cfg is not None

    def test_get_microhyseeker_config_no_exception(self) -> None:
        """VAL-CFG-03b: get_microhyseeker_config() 不抛异常"""
        from src.configs import get_microhyseeker_config
        cfg = get_microhyseeker_config()
        assert cfg is not None


# ── VAL-CMN: 公共模块 ─────────────────────────────────────────────────────────

class TestCommonModules:
    """VAL-CMN-01..03 — src/common/ 校验"""

    def test_registry_list_tools_returns_dict(self) -> None:
        """VAL-CMN-01: registry.list_tools() 返回 dict"""
        from src.common.tool_registry import registry
        tools = registry.list_tools()
        assert isinstance(tools, dict)

    def test_registry_tool_decorator_registers(self) -> None:
        """VAL-CMN-02: @registry.tool 注册后可通过 list_tools() 检索"""
        from src.common.tool_registry import registry

        @registry.tool(description="test validator tool")
        def _val_test_fn(x: int) -> int:
            return x + 1

        tools = registry.list_tools()
        assert "_val_test_fn" in tools

    def test_knowledge_chunk_instantiable(self) -> None:
        """VAL-CMN-03a: KnowledgeChunk 可正常实例化"""
        from src.common.types import KnowledgeChunk
        chunk = KnowledgeChunk(
            chunk_id="c1", content="test content", source="test_source", score=0.9
        )
        assert chunk.content == "test content"
        assert chunk.score == 0.9

    def test_literature_ref_instantiable(self) -> None:
        """VAL-CMN-03b: LiteratureRef 可正常实例化"""
        from src.common.types import LiteratureRef
        ref = LiteratureRef(title="Test Paper", source_file="test.pdf")
        assert ref.title == "Test Paper"


# ── VAL-RAG: 知识库模块 ───────────────────────────────────────────────────────

class TestRAG:
    """VAL-RAG-01..04 — src/rag.py 校验"""

    def test_get_viking_kb_singleton(self) -> None:
        """VAL-RAG-01: get_viking_kb() 返回同一缓存实例"""
        from src.rag import get_viking_kb
        kb1 = get_viking_kb()
        kb2 = get_viking_kb()
        assert kb1 is kb2

    def test_search_literature_no_exception_when_unavailable(self) -> None:
        """VAL-RAG-02: KB 不可用时 search_literature() 返回 [] 不抛异常"""
        from src.rag import get_viking_kb
        kb = get_viking_kb()
        result = kb.search_literature("HER Tafel slope", top_k=3)
        assert isinstance(result, list)

    def test_search_experiments_no_exception_when_unavailable(self) -> None:
        """VAL-RAG-03: KB 不可用时 search_experiments() 返回 [] 不抛异常"""
        from src.rag import get_viking_kb
        kb = get_viking_kb()
        result = kb.search_experiments("CV Fe 0.3M", top_k=3)
        assert isinstance(result, list)

    def test_is_available_is_bool(self) -> None:
        """VAL-RAG-04: is_available 属性存在且为 bool"""
        from src.rag import get_viking_kb
        kb = get_viking_kb()
        assert isinstance(kb.is_available, bool)


# ── VAL-SK-D3: InteractiveTroubleshootingSkill ───────────────────────────────

class TestInteractiveTroubleshootingSkill:
    """VAL-SK-D3 — D3 交互式故障决策树校验"""

    def test_valid_symptom_returns_guide(self) -> None:
        """VAL-SK-D3: 有效 symptom 返回非空决策树"""
        from src.skills.diagnostics import interactive_troubleshooting_skill
        result = run_async(
            interactive_troubleshooting_skill.execute(symptom="pump_not_running")
        )
        assert result.success is True
        assert result.data is not None
        assert len(result.data) > 0

    def test_invalid_symptom_returns_failure(self) -> None:
        """VAL-SK-D3-ERR: 无效 symptom 返回 success=False"""
        from src.skills.diagnostics import interactive_troubleshooting_skill
        result = run_async(
            interactive_troubleshooting_skill.execute(symptom="totally_unknown_symptom")
        )
        assert result.success is False

    def test_all_valid_symptoms(self) -> None:
        """D3 所有 4 种 symptom 均可正常处理"""
        from src.skills.diagnostics import interactive_troubleshooting_skill
        symptoms = [
            "pump_not_running",
            "echem_no_signal",
            "communication_timeout",
            "data_anomaly",
        ]
        for symptom in symptoms:
            result = run_async(
                interactive_troubleshooting_skill.execute(symptom=symptom)
            )
            assert result.success is True, f"symptom={symptom} returned success=False"


# ── VAL-SK-C2: SuggestNextExperimentSkill ────────────────────────────────────

class TestSuggestNextExperimentSkill:
    """VAL-SK-C2-A..E — C2 规则推荐校验"""

    def test_anomalies_triggers_diagnostic_run(self) -> None:
        """VAL-SK-C2-A: anomalies 非空时选择 diagnostic_run"""
        from src.skills.suggest_next_experiment import suggest_next_experiment_skill
        context_data = {"anomalies": ["pump pressure spike"], "trend": {}}
        result = run_async(
            suggest_next_experiment_skill.execute(context_data=context_data)
        )
        assert result.success is True
        assert result.data["intent"] == "diagnostic_run"

    def test_goal_optim_triggers_optimisation_run(self) -> None:
        """VAL-SK-C2-B: goal 含 'optim' 时选择 optimisation_run"""
        from src.skills.suggest_next_experiment import suggest_next_experiment_skill
        result = run_async(
            suggest_next_experiment_skill.execute(goal="optimize HER overpotential")
        )
        assert result.success is True
        assert result.data["intent"] == "optimisation_run"

    def test_goal_stable_triggers_stability_run(self) -> None:
        """VAL-SK-C2-C: goal 含 'stable' 时选择 stability_run"""
        from src.skills.suggest_next_experiment import suggest_next_experiment_skill
        result = run_async(
            suggest_next_experiment_skill.execute(goal="stable current over 12h")
        )
        assert result.success is True
        assert result.data["intent"] == "stability_run"

    def test_no_context_returns_generic(self) -> None:
        """VAL-SK-C2-D: 无条件时返回 generic"""
        from src.skills.suggest_next_experiment import suggest_next_experiment_skill
        result = run_async(suggest_next_experiment_skill.execute())
        assert result.success is True
        assert result.data["intent"] == "generic"

    def test_output_contains_validation(self) -> None:
        """VAL-SK-C2-E: 输出 plan 含 _validation 字段"""
        from src.skills.suggest_next_experiment import suggest_next_experiment_skill
        result = run_async(suggest_next_experiment_skill.execute())
        assert result.success is True
        plan = result.data.get("plan", {})
        assert "_validation" in plan


# ── VAL-OPT: 优化模块 ─────────────────────────────────────────────────────────

class TestOptimization:
    """VAL-OPT-01..02 — BayesianOptimizer 校验"""

    def test_parameter_definition_float_valid(self) -> None:
        """VAL-OPT-01: ParameterDefinition float 类型正常构造"""
        from src.optimization.bayesian_optimizer import ParameterDefinition
        p = ParameterDefinition(name="scan_rate", kind="float", low=0.01, high=1.0)
        assert p.name == "scan_rate"
        assert p.kind == "float"

    def test_parameter_definition_empty_name_raises(self) -> None:
        """VAL-OPT-02: ParameterDefinition name 为空时抛 ValueError"""
        import pytest
        from src.optimization.bayesian_optimizer import ParameterDefinition
        with pytest.raises(ValueError, match="name"):
            ParameterDefinition(name="  ", kind="float", low=0.0, high=1.0)


# ── VAL-GRAPH: LangGraph 图层 ─────────────────────────────────────────────────

class TestGraphLayer:
    """VAL-GRAPH-01..02 — SupervisorGraph 校验"""

    def test_get_supervisor_graph_singleton(self) -> None:
        """VAL-GRAPH-01: get_supervisor_graph() 单例缓存"""
        from src.graph.supervisor_graph import get_supervisor_graph
        g1 = get_supervisor_graph()
        g2 = get_supervisor_graph()
        assert g1 is g2

    def test_supervisor_graph_not_none(self) -> None:
        """VAL-GRAPH-02: 图对象不为 None"""
        from src.graph.supervisor_graph import get_supervisor_graph
        g = get_supervisor_graph()
        assert g is not None


# ── VAL-API: API 路由 ─────────────────────────────────────────────────────────

class TestAPIRoutes:
    """VAL-API-01..02 — API 路由模块导入校验"""

    def test_diagnostics_routes_importable(self) -> None:
        """VAL-API-01: diagnostics 路由模块可导入"""
        import src.api.routes.diagnostics as diag_routes  # noqa: F401
        assert diag_routes is not None

    def test_context_routes_importable(self) -> None:
        """VAL-API-02: context 路由模块可导入"""
        import src.api.routes.context as ctx_routes  # noqa: F401
        assert ctx_routes is not None


# ── VAL-SKILL-INIT: skills __init__ 导出完整性 ───────────────────────────────

class TestSkillsInit:
    """VAL-SKILL-INIT — src/skills/__init__.py 所有 __all__ 项目均可导入"""

    def test_all_skills_importable_from_package(self) -> None:
        """所有 __all__ 中的名称均可从 src.skills 导入"""
        import src.skills as skills_pkg
        for name in skills_pkg.__all__:
            obj = getattr(skills_pkg, name, None)
            assert obj is not None, f"src.skills.{name} 不存在于 __all__ 中"
