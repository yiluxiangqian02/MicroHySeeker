"""Interactive troubleshooting skill for AutoHySeeker."""

from __future__ import annotations

from typing import Any

from src.common.types import DiagnosticResult
from src.skills.base import BaseSkill, SkillResult


class InteractiveTroubleshootingSkill(BaseSkill):
    """Interactive troubleshooting guide with decision trees for common issues."""

    name = "interactive_troubleshooting"
    description = "Guide users through troubleshooting common hardware and software issues"
    required_tools = []

    # Decision tree for common problems
    _TROUBLESHOOTING_TREES = {
        "pump_not_running": {
            "title": "泵不转动故障排查",
            "steps": [
                "检查泵电源连接是否正常",
                "检查 RS485 通信线路是否连接正确（A+/B-）",
                "检查泵地址设置是否与配置文件一致",
                "使用万用表测试泵供电电压（应为 24V DC）",
                "尝试手动发送泵控制指令测试响应",
                "检查泵控制器指示灯状态",
            ],
            "possible_causes": [
                "电源未接通或电压不足",
                "RS485 通信线路接反或松动",
                "泵地址配置错误",
                "泵控制器故障",
                "通信波特率不匹配",
            ],
        },
        "echem_no_signal": {
            "title": "电化学工作站无信号",
            "steps": [
                "检查工作站 USB 连接是否正常",
                "检查三电极连接是否牢固（工作电极、参比电极、对电极）",
                "检查电解液是否充足且电极浸入",
                "在 CHI 软件中手动测试是否能采集数据",
                "检查电极表面是否有气泡或污染",
                "测试开路电位（OCP）确认电极连接",
            ],
            "possible_causes": [
                "USB 驱动未安装或端口冲突",
                "电极连接松动或断路",
                "电解液不足或电极未浸入",
                "电极表面钝化或污染",
                "工作站软件未正确初始化",
            ],
        },
        "communication_timeout": {
            "title": "通信超时故障排查",
            "steps": [
                "检查设备是否上电且指示灯正常",
                "确认串口号配置是否正确（COM 端口）",
                "检查波特率、数据位、停止位配置",
                "使用串口调试工具测试设备响应",
                "检查 USB 转串口驱动是否正常",
                "尝试重启设备和重新连接",
            ],
            "possible_causes": [
                "串口号配置错误",
                "波特率不匹配",
                "设备未上电或故障",
                "USB 转串口驱动问题",
                "通信线路干扰",
            ],
        },
        "data_anomaly": {
            "title": "数据异常分析",
            "steps": [
                "检查原始数据文件是否完整（无截断）",
                "确认数据采集参数设置是否合理",
                "对比历史正常数据查看差异",
                "检查传感器校准状态",
                "分析数据趋势判断是否为物理异常",
                "检查数据处理流程是否有错误",
            ],
            "possible_causes": [
                "传感器漂移或需要校准",
                "采集参数设置不当",
                "数据文件损坏或格式错误",
                "物理过程异常（如反应未发生）",
              "数据处理算法错误",
            ],
        },
    }

    async def execute(self, symptom: str = "", **kwargs: Any) -> SkillResult:
        """Execute interactive troubleshooting for the given symptom.

        Args:
            symptom: Problem identifier (pump_not_running, echem_no_signal,
                     communication_timeout, data_anomaly)
            **kwargs: Additional context

        Returns:
            SkillResult with troubleshooting guide
        """
        if not symptom or symptom not in self._TROUBLESHOOTING_TREES:
            available = ", ".join(self._TROUBLESHOOTING_TREES.keys())
            return SkillResult(
    success=False,
                data={},
                message=f"Unknown symptom: {symptom}. Available: {available}",
                artifacts=[],
            )

        tree = self._TROUBLESHOOTING_TREES[symptom]

        # Build diagnostic result
        diagnostic = DiagnosticResult(
            severity="warning",
            category="troubleshooting",
            message=tree["title"],
            suggestion="\n".join(
                [f"{i+1}. {step}" for i, step in enumerate(tree["steps"])]
            ),
            evidence=tree["possible_causes"],
        )

        guide = {
            "symptom": symptom,
            "title": tree["title"],
            "steps": tree["steps"],
            "possible_causes": tree["possible_causes"],
            "diagnostic": diagnostic.model_dump(),
        }

        return SkillResult(
            success=True,
            data=guide,
            message=f"Generated troubleshooting guide for: {tree['title']}",
            artifacts=[],
        )

    def get_schema(self) -> dict:
        """Return JSON Schema for this skill's inputs."""
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "symptom": {
                    "type": "string",
                    "description": "Problem identifier",
                    "enum": list(self._TROUBLESHOOTING_TREES.keys()),
                }
            },
            "required": ["symptom"],
        }
