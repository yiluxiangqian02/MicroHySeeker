"""Translator service for internationalization."""

from typing import Dict, Optional


class TranslatorService:
    """多语言翻译服务。"""
    
    # 中文翻译表
    TRANSLATIONS = {
        "zh_CN": {
            # 菜单
            "File": "文件",
            "Single Experiment": "单次实验",
            "Combo Experiment": "组合实验",
            "Load Program": "加载程序",
            "Save Program": "保存程序",
            "Exit": "退出",
            "Tools": "工具",
            "Settings": "设置",
            "Calibrate": "校准",
            "Manual Control": "手动控制",
            "Prepare Solution": "配液",
            "Syringe Degas": "注射泵脱气",
            "EChem": "电化学",
            "Help": "帮助",
            "About": "关于",
            
            # 窗口标题
            "Main Window": "主窗口",
            "Program Editor": "程序编辑器",
            "Combo Editor": "组合编辑器",
            "Configuration": "配置",
            "Manual Dialog": "手动控制对话框",
            "RS485 Test": "RS485 测试",
            "EChem View": "电化学视图",
            
            # 按钮
            "Add": "添加",
            "Delete": "删除",
            "Up": "上移",
            "Down": "下移",
            "Save": "保存",
            "Run": "运行",
            "Close": "关闭",
            "Start": "启动",
            "Stop": "停止",
            "Import": "导入",
            "Export": "导出",
            
            # 字段
            "Step Type": "步骤类型",
            "Step Name": "步骤名称",
            "Solution Type": "溶液种类",
            "Concentration": "浓度",
            "Target Volume": "目标体积",
            "Pump Address": "泵地址",
            "Pump Speed": "泵转速",
            "Potential": "电位",
            "Current Limit": "电流限制",
            "Duration": "时间",
            "OCPT": "OCPT",
            "Delay": "延时",
            
            # 操作类型
            "配液": "配液",
            "电化学": "电化学",
            "冲洗": "冲洗",
            "移液": "移液",
            "空白": "空白",
            
            # 状态消息
            "Ready": "就绪",
            "Running": "运行中",
            "Error": "错误",
            "Success": "成功",
        },
        "en_US": {
            # 菜单
            "File": "File",
            "Single Experiment": "Single Experiment",
            "Combo Experiment": "Combo Experiment",
            "Load Program": "Load Program",
            "Save Program": "Save Program",
            "Exit": "Exit",
            "Tools": "Tools",
            "Settings": "Settings",
            "Calibrate": "Calibrate",
            "Manual Control": "Manual Control",
            "Prepare Solution": "Prepare Solution",
            "Syringe Degas": "Syringe Degas",
            "EChem": "EChem",
            "Help": "Help",
            "About": "About",
            
            # 窗口标题
            "Main Window": "Main Window",
            "Program Editor": "Program Editor",
            "Combo Editor": "Combo Editor",
            "Configuration": "Configuration",
            "Manual Dialog": "Manual Dialog",
            "RS485 Test": "RS485 Test",
            "EChem View": "EChem View",
            
            # 按钮
            "Add": "Add",
            "Delete": "Delete",
            "Up": "Up",
            "Down": "Down",
            "Save": "Save",
            "Run": "Run",
            "Close": "Close",
            "Start": "Start",
            "Stop": "Stop",
            "Import": "Import",
            "Export": "Export",
            
            # 字段
            "Step Type": "Step Type",
            "Step Name": "Step Name",
            "Solution Type": "Solution Type",
            "Concentration": "Concentration",
            "Target Volume": "Target Volume",
            "Pump Address": "Pump Address",
            "Pump Speed": "Pump Speed",
            "Potential": "Potential",
            "Current Limit": "Current Limit",
            "Duration": "Duration",
            "OCPT": "OCPT",
            "Delay": "Delay",
            
            # 操作类型
            "配液": "Solution Preparation",
            "电化学": "Electrochemistry",
            "冲洗": "Flush",
            "移液": "Pipette",
            "空白": "Blank",
            
            # 状态消息
            "Ready": "Ready",
            "Running": "Running",
            "Error": "Error",
            "Success": "Success",
        }
    }
    
    def __init__(self, language: str = "zh_CN"):
        self.current_language = language
    
    def translate(self, key: str) -> str:
        """翻译键值。"""
        translations = self.TRANSLATIONS.get(self.current_language, {})
        return translations.get(key, key)
    
    def set_language(self, language: str) -> None:
        """设置语言。"""
        if language in self.TRANSLATIONS:
            self.current_language = language
    
    def get_available_languages(self) -> Dict[str, str]:
        """获取可用的语言列表。"""
        return {
            "zh_CN": "中文",
            "en_US": "English"
        }
