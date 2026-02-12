"""
国际化 (i18n) 模块 - 支持简体中文 / English 切换
"""
import json
from pathlib import Path
from typing import Dict, Optional

# 当前语言
_current_lang = "zh"  # "zh" | "en"

# 翻译字典
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── 主窗口 ──
    "app_title":          {"zh": "MicroHySeeker - 自动化实验平台", "en": "MicroHySeeker - Automated Experiment Platform"},
    "file":               {"zh": "文件(&F)", "en": "&File"},
    "tools":              {"zh": "工具(&T)", "en": "&Tools"},
    "help":               {"zh": "帮助(&H)", "en": "&Help"},
    "single_exp":         {"zh": "单次实验(&S)", "en": "&Single Experiment"},
    "combo_exp":          {"zh": "组合实验(&C)", "en": "&Combo Experiment"},
    "load_exp":           {"zh": "载入实验(&L)", "en": "&Load Experiment"},
    "save_exp":           {"zh": "保存实验(&V)", "en": "Sa&ve Experiment"},
    "exit":               {"zh": "退出(&X)", "en": "E&xit"},
    "sys_config":         {"zh": "系统配置(&S)", "en": "&System Config"},
    "manual_ctrl":        {"zh": "手动控制(&M)", "en": "&Manual Control"},
    "calibrate":          {"zh": "泵校准(&C)", "en": "&Calibrate"},
    "prep_solution":      {"zh": "配制溶液(&P)", "en": "&Prepare Solution"},
    "about":              {"zh": "关于(&A)", "en": "&About"},
    "language":           {"zh": "语言 / Language", "en": "Language / 语言"},
    "lang_zh":            {"zh": "简体中文", "en": "简体中文 (Chinese)"},
    "lang_en":            {"zh": "English (英语)", "en": "English"},

    # ── 工具栏 ──
    "tb_single_exp":      {"zh": "单次实验", "en": "Single Exp"},
    "tb_combo_exp":       {"zh": "组合实验", "en": "Combo Exp"},
    "tb_load":            {"zh": "载入实验", "en": "Load"},
    "tb_save":            {"zh": "保存实验", "en": "Save"},
    "tb_config":          {"zh": "系统设置", "en": "Settings"},
    "tb_prep":            {"zh": "配制溶液", "en": "Prep Sol"},
    "tb_calibrate":       {"zh": "泵校准", "en": "Calibrate"},
    "tb_manual":          {"zh": "手动控制", "en": "Manual"},
    "tb_flush":           {"zh": "冲洗", "en": "Flush"},

    # ── 泵状态 ──
    "pump_status":        {"zh": "泵状态指示", "en": "Pump Status"},
    "pump_n":             {"zh": "泵{n}", "en": "Pump {n}"},

    # ── 实验过程 ──
    "exp_process":        {"zh": "实验过程", "en": "Experiment Process"},
    "ws_title":           {"zh": "电化学工作站", "en": "Electrochemical Workstation"},
    "ws_disconnected":    {"zh": "暂未连接", "en": "Not Connected"},
    "ws_connected":       {"zh": "已连接", "en": "Connected"},
    "ws_failed":          {"zh": "连接失败", "en": "Connection Failed"},
    "ws_waiting":         {"zh": "等待测量", "en": "Waiting"},
    "ws_measuring":       {"zh": "{tech} 测量中...", "en": "{tech} Measuring..."},
    "ws_done":            {"zh": "{tech} 测量完成", "en": "{tech} Done"},
    "mix_beaker":         {"zh": "混合烧杯", "en": "Mix Beaker"},
    "react_beaker":       {"zh": "反应烧杯", "en": "React Beaker"},
    "not_configured":     {"zh": "未配置", "en": "N/A"},
    "combo_label":        {"zh": "组合", "en": "Combo"},

    # ── 实验控制 ──
    "exp_control":        {"zh": "实验控制", "en": "Experiment Control"},
    "single_exp_ctrl":    {"zh": "单次实验", "en": "Single Experiment"},
    "combo_exp_ctrl":     {"zh": "组合实验", "en": "Combo Experiment"},
    "start_single":       {"zh": "开始单次实验", "en": "Start Single"},
    "start_combo":        {"zh": "开始组合实验", "en": "Start Combo"},
    "stop_exp":           {"zh": "停止实验", "en": "Stop"},
    "prev":               {"zh": "上一个", "en": "Prev"},
    "next":               {"zh": "下一个", "en": "Next"},
    "jump_to":            {"zh": "跳至:", "en": "Jump:"},
    "jump":               {"zh": "跳转", "en": "Go"},
    "reset_combo":        {"zh": "复位组合实验进度", "en": "Reset Combo"},
    "list_params":        {"zh": "列出参数", "en": "List Params"},
    "no_exp_to_save":     {"zh": "没有可保存的实验", "en": "No experiment to save"},
    "completed":          {"zh": "完成", "en": "Completed"},
    "failed":             {"zh": "失败", "en": "Failed"},
    "sys_started":        {"zh": "系统已启动，欢迎使用 MicroHySeeker", "en": "System started. Welcome to MicroHySeeker"},
    "exp_done_ok":        {"zh": "成功完成", "en": "Completed successfully"},
    "exp_done_fail":      {"zh": "异常结束", "en": "Ended with errors"},

    # ── 步骤类型 ──
    "step_transfer":      {"zh": "移液", "en": "Transfer"},
    "step_prep_sol":      {"zh": "配液", "en": "Prep Sol"},
    "step_flush":         {"zh": "冲洗", "en": "Flush"},
    "step_echem":         {"zh": "电化学", "en": "EChem"},
    "step_blank":         {"zh": "空白", "en": "Blank"},
    "step_evacuate":      {"zh": "排空", "en": "Evacuate"},

    # ── 步骤进度 / 日志 ──
    "step_progress":      {"zh": "步骤进度", "en": "Step Progress"},
    "run_log":            {"zh": "运行日志", "en": "Run Log"},

    # ── 状态栏 ──
    "status_running":     {"zh": "状态: 运行中", "en": "Status: Running"},
    "status_idle":        {"zh": "状态: 就绪", "en": "Status: Ready"},
    "status_done":        {"zh": "状态: 完成", "en": "Status: Done"},
    "status_failed":      {"zh": "状态: 失败", "en": "Status: Failed"},
    "echem_status":       {"zh": "电化学仪: 未连接", "en": "EChem: Not Connected"},
    "rs485_status":       {"zh": "RS485: 未连接", "en": "RS485: Not Connected"},

    # ── EChem 参数描述 ──
    "scan_rate":          {"zh": "扫速", "en": "Scan Rate"},
    "segments":           {"zh": "段数", "en": "Seg"},
    "run_time":           {"zh": "时间", "en": "Time"},
    "sensitivity":        {"zh": "灵敏度", "en": "Sens"},
    "freq_range":         {"zh": "频率", "en": "Freq"},
    "amplitude":          {"zh": "振幅", "en": "Amp"},
    "wait_s":             {"zh": "等待{d}s", "en": "Wait {d}s"},

    # ── 对话框 ──
    "warning":            {"zh": "警告", "en": "Warning"},
    "error":              {"zh": "错误", "en": "Error"},
    "info":               {"zh": "信息", "en": "Info"},
    "no_steps_warning":   {"zh": "请先编辑单次实验程序", "en": "Please edit single experiment program first"},
    "precheck_fail":      {"zh": "预检查失败", "en": "Pre-check Failed"},
    "lang_restart_hint":  {"zh": "语言已切换为 {lang}，部分界面重启后生效。", "en": "Language changed to {lang}. Some UI will update after restart."},
}


def tr(key: str, **kwargs) -> str:
    """翻译函数
    
    Args:
        key: 翻译键
        **kwargs: 格式化参数
        
    Returns:
        翻译后的文本
    """
    entry = _TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_current_lang, entry.get("zh", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_lang() -> str:
    """获取当前语言"""
    return _current_lang


def set_lang(lang: str):
    """设置语言 ('zh' | 'en')"""
    global _current_lang
    if lang in ("zh", "en"):
        _current_lang = lang
        _save_lang_pref(lang)


def _load_lang_pref():
    """从配置文件加载语言偏好"""
    global _current_lang
    try:
        pref_file = Path("./config/lang.json")
        if pref_file.exists():
            data = json.loads(pref_file.read_text(encoding="utf-8"))
            lang = data.get("lang", "zh")
            if lang in ("zh", "en"):
                _current_lang = lang
    except Exception:
        pass


def _save_lang_pref(lang: str):
    """保存语言偏好到配置文件"""
    try:
        pref_file = Path("./config/lang.json")
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        pref_file.write_text(json.dumps({"lang": lang}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# 启动时加载语言偏好
_load_lang_pref()
