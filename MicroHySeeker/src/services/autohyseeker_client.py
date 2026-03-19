"""AutoHySeeker API 客户端

MicroHySeeker 通过此客户端调用 AutoHySeeker 后端服务。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("microhyseeker.autohyseeker_client")


class AutoHySeekerClient:
    """AutoHySeeker API 客户端"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8200"):
        """初始化客户端
        
        Args:
            base_url: AutoHySeeker API 地址
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        
        if httpx is None:
            logger.warning("httpx not installed, AutoHySeeker integration disabled")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if httpx is None:
            raise RuntimeError("httpx not installed")
        
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, trust_env=False)
        return self._client
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # 健康检查
    # ─────────────────────────────────────────────────────────────────────────
    
    async def health_check(self) -> bool:
        """检查 AutoHySeeker 服务是否可用"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning("AutoHySeeker health check failed: %s", e)
            return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # 实验数据分析
    # ─────────────────────────────────────────────────────────────────────────
    
    async def analyze_experiment(self, run_dir: str) -> Dict[str, Any]:
        """请求分析实验数据
        
        Args:
            run_dir: 实验数据目录路径
        
        Returns:
            分析结果字典
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/agents/invoke",
                json={
                    "task": {"intent": "analyze experiment"},
                    "context": {"run_dir": run_dir}
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Experiment analysis completed for %s", run_dir)
            return result
        except Exception as e:
            logger.exception("Failed to analyze experiment: %s", e)
            return {"error": str(e)}
    
    async def analyze_cv_data(self, run_dir: str) -> Dict[str, Any]:
        """分析 CV 数据
        
        Args:
            run_dir: 实验数据目录路径
        
        Returns:
            CV 分析结果
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/agents/invoke",
                json={
                    "task": {"intent": "analyze CV data"},
                    "context": {"run_dir": run_dir}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Failed to analyze CV data: %s", e)
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────────────────────
    # 实验建议
    # ─────────────────────────────────────────────────────────────────────────
    
    async def suggest_next_experiment(
        self,
        history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """获取下一个实验建议
        
        Args:
            history: 历史实验列表
            context: 额外上下文信息
        
        Returns:
            实验建议（ExperimentPlan 格式）
        """
        try:
            client = await self._get_client()
            payload = {
                "history": history or [],
                "context": context or {}
            }
            response = await client.get(f"{self.base_url}/api/experiments/suggestions")
            response.raise_for_status()
            result = response.json()
            logger.info("Got experiment suggestion snapshot")
            return {"payload": payload, **result}
        except Exception as e:
            logger.exception("Failed to get experiment suggestion: %s", e)
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────────────────────
    # 诊断
    # ─────────────────────────────────────────────────────────────────────────
    
    async def diagnose_failure(self, run_dir: str) -> Dict[str, Any]:
        """诊断实验失败原因
        
        Args:
            run_dir: 失败实验的数据目录
        
        Returns:
            诊断报告
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/diagnostics/invoke",
                json={
                    "action": "analyze_failure",
                    "context": {"run_dir": run_dir}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Failed to diagnose failure: %s", e)
            return {"error": str(e)}
    
    async def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态
        
        Returns:
            健康检查报告
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/diagnostics/invoke",
                json={"action": "check_health"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Failed to check system health: %s", e)
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────────────────────
    # 实验模板
    # ─────────────────────────────────────────────────────────────────────────
    
    async def list_templates(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有实验模板
        
        Args:
            tag: 按标签过滤（可选）
        
        Returns:
            模板列表
        """
        try:
            client = await self._get_client()
            params = {"tag": tag} if tag else {}
            response = await client.get(
                f"{self.base_url}/templates",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Failed to list templates: %s", e)
            return []
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板详情
        
        Args:
            template_id: 模板ID
        
        Returns:
            模板详情，失败返回 None
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/templates/{template_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception("Failed to get template %s: %s", template_id, e)
            return None
    
    async def create_template(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """创建实验模板
        
        Args:
            name: 模板名称
            steps: 步骤列表
            description: 描述
            tags: 标签
        
        Returns:
            创建的模板，失败返回 None
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/templates",
                json={
                    "name": name,
                    "description": description,
                    "steps": steps,
                    "tags": tags or []
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Created template: %s", result.get("template_id"))
            return result
        except Exception as e:
            logger.exception("Failed to create template: %s", e)
            return None
    
    async def instantiate_template(
        self,
        template_id: str,
        exp_name: Optional[str] = None,
        params_override: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """从模板实例化实验
        
        Args:
            template_id: 模板ID
            exp_name: 实验名称（可选）
            params_override: 参数覆盖（可选）
        
        Returns:
            实验计划，失败返回 None
        """
        try:
            client = await self._get_client()
            params = {}
            if exp_name:
                params["exp_name"] = exp_name
            
            response = await client.post(
                f"{self.base_url}/templates/{template_id}/instantiate",
                params=params,
                json=params_override or {}
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Instantiated experiment from template %s", template_id)
            return result
        except Exception as e:
            logger.exception("Failed to instantiate template: %s", e)
            return None
    
    # ─────────────────────────────────────────────────────────────────────────
    # 数据查询
    # ─────────────────────────────────────────────────────────────────────────
    
    async def list_experiments(self, n: int = 10) -> List[Dict[str, Any]]:
        """列出最近的实验
        
        Args:
            n: 返回数量
        
        Returns:
            实验列表
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/data/experiments",
                params={"n": n}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("items", [])
        except Exception as e:
            logger.exception("Failed to list experiments: %s", e)
            return []


# 全局单例
_client: Optional[AutoHySeekerClient] = None


def get_autohyseeker_client(base_url: str = "http://127.0.0.1:8200") -> AutoHySeekerClient:
    """获取全局 AutoHySeeker 客户端实例"""
    global _client
    if _client is None:
        _client = AutoHySeekerClient(base_url)
    return _client
