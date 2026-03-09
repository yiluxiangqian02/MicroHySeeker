# Task 7: 实现实验模板管理（MicroHySeeker 项目）

## 目标
在 MicroHySeeker GUI 中添加实验模板功能

## 核心功能

### 1. 保存当前实验为模板
- 模板名称、描述、标签
- 保存所有步骤配置
- 保存到 templates/ 目录（JSON 格式）

### 2. 模板库浏览
- 列表显示所有模板
- 搜索和过滤（按名称、标签）
- 预览模板详情

### 3. 从模板创建实验
- 加载模板到程序编辑器
- 可修改参数后运行

## 技术栈
- PySide6（Qt）
- 现有代码：MicroHySeeker/src/ui/main_window.py
- 程序编辑器：MicroHySeeker/src/ui/program_editor.py

## 实现要求

### 1. 创建 MicroHySeeker/src/core/template_manager.py
- TemplateManager 类
- save_template(name, description, steps, tags)
- load_template(template_id)
- list_templates(filter_tags)
- delete_template(template_id)

### 2. 在 main_window.py 中添加
- "保存为模板" 按钮
- "模板库" 对话框

### 3. 创建 MicroHySeeker/src/ui/template_dialog.py
- TemplateLibraryDialog（模板库浏览）
- SaveTemplateDialog（保存模板）

### 4. 模板文件格式（JSON）
```json
{
  "id": "uuid",
  "name": "模板名称",
  "description": "描述",
  "tags": ["CV", "优化"],
  "steps": [...],
  "created_at": "2026-03-10T00:00:00",
  "updated_at": "2026-03-10T00:00:00"
}
```

## 注意事项
- 模板目录：MicroHySeeker/templates/
- 错误处理（文件读写）
- 模板验证（步骤格式检查）
- UI 集成到现有界面
