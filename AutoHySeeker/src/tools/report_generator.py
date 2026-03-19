"""Report generation tools for AutoHySeeker."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.common.types import HealthStatus, RunSummary
from src.tools.log_analysis import summarize_run

# ---------------------------------------------------------------------------
# Jinja2 templates (inline; also loadable from data/templates/ if present)
# ---------------------------------------------------------------------------

_RUN_REPORT_TEMPLATE = """\
# 实验运行报告

**运行 ID**: {{ summary.run_id }}
**实验名称**: {{ summary.exp_name }}
**状态**: {{ "✅ 成功" if summary.success else "❌ 失败" }}
**开始时间**: {{ summary.started_at.strftime('%Y-%m-%d %H:%M:%S') }}
**结束时间**: {{ summary.finished_at.strftime('%Y-%m-%d %H:%M:%S') if summary.finished_at else "—" }}
**总耗时**: {{ "%.1f"|format(summary.elapsed_seconds) }} 秒

---

## 步骤时间线

| 序号 | 步骤 ID | 类型 | 状态 | 耗时(s) | 数据文件 |
|------|---------|------|------|---------|---------|
{% for s in summary.step_results -%}
| {{ s.step_index }} | {{ s.step_id }} | {{ s.step_type }} | {{ "✅" if s.success else "❌" }} | {{ "%.2f"|format(s.duration_s) if s.duration_s is not none else "—" }} | {{ s.data_file or "—" }} |
{% endfor %}

---

## 错误分析

{% if summary.errors -%}
检测到 **{{ summary.errors|length }}** 条错误：

{% for err in summary.errors -%}
- {{ err }}
{% endfor %}
{%- else -%}
无错误。
{%- endif %}

---

## 警告

{% if summary.warnings -%}
共 **{{ summary.warnings|length }}** 条警告：

{% for w in summary.warnings -%}
- {{ w }}
{% endfor %}
{%- else -%}
无警告。
{%- endif %}

---

## 数据质量评估

{% if summary.step_results -%}
- 总步骤数: {{ summary.step_results|length }}
- 成功步骤: {{ summary.step_results|selectattr('success')|list|length }}
- 失败步骤: {{ summary.step_results|rejectattr('success')|list|length }}
{%- else -%}
无步骤数据。
{%- endif %}

---

*报告生成时间: {{ now }}*
"""

_HEALTH_REPORT_TEMPLATE = """\
# 系统健康报告

**生成时间**: {{ now }}

| 组件 | 状态 | 消息 | 最后检查 |
|------|------|------|---------|
{% for s in statuses -%}
| {{ s.component }} | {{ s.status }} | {{ s.message }} | {{ s.last_checked.strftime('%Y-%m-%d %H:%M:%S') }} |
{% endfor %}

---

## 摘要

- 总组件数: {{ statuses|length }}
- 正常 (ok): {{ statuses|selectattr('status', 'equalto', 'ok')|list|length }}
- 警告 (warning): {{ statuses|selectattr('status', 'equalto', 'warning')|list|length }}
- 错误 (error): {{ statuses|selectattr('status', 'equalto', 'error')|list|length }}
- 未知 (unknown): {{ statuses|selectattr('status', 'equalto', 'unknown')|list|length }}

*报告生成时间: {{ now }}*
"""


def _load_template(template_name: str, fallback: str):
    """Load a report template, falling back to a minimal string renderer."""
    from src.common.config import DATA_ROOT

    tmpl_path = DATA_ROOT / "templates" / template_name
    if tmpl_path.exists():
        source = tmpl_path.read_text(encoding="utf-8")
    else:
        source = fallback
    try:
        from jinja2 import Environment
    except ImportError:
        class _SimpleTemplate:
            def __init__(self, template_source: str) -> None:
                self._template_source = template_source

            def render(self, **context: object) -> str:
                lines = [
                    "# AutoHySeeker Report",
                    "",
                    "Jinja2 未安装，使用简化报告输出。",
                    "",
                    f"template: {template_name}",
                    f"context_keys: {', '.join(sorted(context))}",
                ]
                summary = context.get("summary")
                if summary is not None:
                    lines.extend(
                        [
                            "",
                            f"run_id: {getattr(summary, 'run_id', 'unknown')}",
                            f"success: {getattr(summary, 'success', False)}",
                        ]
                    )
                statuses = context.get("statuses")
                if isinstance(statuses, list):
                    lines.extend(["", f"status_count: {len(statuses)}"])
                return "\n".join(lines) + "\n"

        return _SimpleTemplate(source)

    env = Environment(autoescape=False)
    return env.from_string(source)


def generate_run_report(run_dir: str, output_path: str) -> str:
    """Generate a Markdown experiment run report.

    Reads run_log.log + run_summary.json from *run_dir*, renders a Markdown
    report and writes it to *output_path*.  Returns the output path.
    """
    summary: RunSummary = summarize_run(run_dir)
    tmpl = _load_template("run_report.md.j2", _RUN_REPORT_TEMPLATE)
    content = tmpl.render(
        summary=summary,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


def generate_health_report(
    statuses: list[HealthStatus], output_path: str
) -> str:
    """Generate a Markdown system health report.

    Renders status information for all components and writes it to *output_path*.
    Returns the output path.
    """
    tmpl = _load_template("health_report.md.j2", _HEALTH_REPORT_TEMPLATE)
    content = tmpl.render(
        statuses=statuses,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)
