"""模板管理器 - 实验模板的保存、加载、列出和删除。"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class TemplateManager:
    """管理实验模板的存储和检索。

    每个模板作为 JSON 文件存储在 templates_dir 目录中，
    文件名格式: {id}.json

    模板 JSON 格式::

        {
            "id": "<uuid>",
            "name": "模板名称",
            "description": "模板描述",
            "tags": ["标签1", "标签2"],
            "steps": [ ... ],   # ProgStep.to_dict() 列表
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    """

    def __init__(self, templates_dir: str = "./templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        name: str,
        description: str,
        tags: List[str],
        steps: List[Dict[str, Any]],
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存实验模板到磁盘。

        Args:
            name: 模板名称。
            description: 模板描述。
            tags: 标签列表。
            steps: 步骤字典列表（来自 ``Experiment.steps[i].to_dict()``）。
            template_id: 可选的已有模板 ID；提供时更新，否则创建新模板。

        Returns:
            保存的完整模板字典。
        """
        now = datetime.now().isoformat()

        if template_id and self.exists(template_id):
            existing = self.load(template_id)
            created_at = existing["created_at"] if existing else now
        else:
            template_id = str(uuid.uuid4())
            created_at = now

        template: Dict[str, Any] = {
            "id": template_id,
            "name": name,
            "description": description,
            "tags": [t.strip() for t in tags if t.strip()],
            "steps": steps,
            "created_at": created_at,
            "updated_at": now,
        }

        file_path = self.templates_dir / f"{template_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

        return template

    def load(self, template_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 加载模板。

        Args:
            template_id: 模板 UUID。

        Returns:
            模板字典；未找到则返回 ``None``。
        """
        file_path = self.templates_dir / f"{template_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板，按 updated_at 倒序排列。

        Returns:
            完整模板字典列表。
        """
        templates = []
        for path in self.templates_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append(data)
            except (json.JSONDecodeError, IOError):
                continue

        templates.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        return templates

    def delete(self, template_id: str) -> bool:
        """删除模板。

        Args:
            template_id: 模板 UUID。

        Returns:
            成功删除返回 ``True``；文件不存在返回 ``False``。
        """
        file_path = self.templates_dir / f"{template_id}.json"
        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    def exists(self, template_id: str) -> bool:
        """检查模板文件是否存在。"""
        return (self.templates_dir / f"{template_id}.json").exists()


# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

_template_manager: Optional[TemplateManager] = None


def get_template_manager(templates_dir: str = "./templates") -> TemplateManager:
    """获取 TemplateManager 单例（懒初始化）。"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager(templates_dir)
    return _template_manager
