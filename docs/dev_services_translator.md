## 1. 模块定位与职责
- 文件：`src/echem_sdl/services/translator.py`
- 作用：负责加载多语言文件，提供键值翻译接口，支持动态切换 locale，并通过回调/事件通知 UI 或核心模块刷新文本。
- 服务对象：UI（按钮/菜单/提示）、核心日志与提示、配置/导出文本等。

## 2. 文件与类结构
- `TranslatorService` 类
  - 初始化参数：`translations_dir: Path`, `default_locale: str = "zh"`, 可选 `logger: LoggerService | None`, `settings_service: SettingsService | None`.
  - 属性：`_locale: str`, `_translations: dict[str, str]`, `_callbacks: list[Callable[[str], None]]`, `_lock`.
  - 方法（类型注解）：
    - `load_translations(locale: str | None = None) -> None`: 从目录加载指定/当前 locale 的 JSON（或 Qt 翻译文件，如果采用 QTranslator）。
    - `gettext(key: str) -> str`: 返回翻译值；缺失键返回 key 或占位符。
    - `set_locale(locale: str) -> None`: 切换当前语言并重新加载，触发回调。
    - `available_locales() -> list[str]`: 列出目录下可用语言。
    - `bind_reload_callback(callback: Callable[[str], None]) -> None`: 绑定语言切换通知。
    - 可选：`format(key: str, **kwargs) -> str`（插值包装）。
- 可选数据结构：`TranslationEntry = dict[str, str]`，如果需要更严格模型可用 pydantic，但非必需。

## 3. 依赖说明
- 标准库：`json`, `pathlib.Path`, `typing`, `threading`.
- 第三方（可选）：`PySide6.QtCore.QTranslator` 如果采用 Qt 原生翻译；否则纯 JSON。
- 内部依赖：`services.logger.LoggerService`（记录加载/错误），`services.settings_service.SettingsService`（可读取/保存当前 locale）。

## 4. 线程与异步策略
- 翻译加载为 IO 操作，可在后台线程调用，但需 `_lock` 保证 `_translations`/`_locale` 更新原子性。
- UI 切换需在 UI 线程应用：通过回调机制，调用方在 UI 线程处理控件刷新。
- 并发读取 `gettext` 应是线程安全的（只读）；更新时持锁替换整个字典。

## 5. 错误与日志处理机制
- 文件缺失：warning，并回退到默认 locale；若默认也缺失，error。
- 解析失败：error，保留旧翻译或回退默认。
- 缺失键：可记录 debug 或 warning（可配置），返回原 key。
- 切换失败：记录 error，不改变当前 locale。

## 6. 测试要求
- 加载有效翻译文件：`gettext` 返回正确值。
- 无效/缺失文件：回退默认，记录 warning/error。
- 切换语言：`set_locale` 后 `gettext` 结果变化，回调被触发。
- 缺失键：返回 key 或占位符。
- 并发访问：多线程 `gettext`/`set_locale` 无崩溃且数据一致（模拟简单并发）。
- UI 回调：绑定伪回调，切换时被调用一次，参数为新 locale。

## 7. 文档与注释要求
- 模块 docstring：说明翻译目录结构 `assets/translations/{locale}.json`，文件格式示例（键值对），默认语言策略。
- 方法 docstring：参数、返回、异常、线程/回调注意事项。
- 类型注解齐全；在加载/回退/回调处加简短注释。
- README 片段可描述如何添加新语言、如何在 UI 中使用 `translator.gettext`。

## 8. 验收标准
- 支持加载/切换多语言，`gettext` 工作正常，缺失键有可预期返回。
- 异常与日志输出符合预期；缺失/损坏文件有回退。
- 线程安全：并发读取安全，更新持锁。
- 测试通过：覆盖加载、切换、缺失键、错误回退、回调触发、并发读取。
- 可直接供 UI/核心调用（`translator.gettext("run")`），并能在语言切换时通知 UI。
