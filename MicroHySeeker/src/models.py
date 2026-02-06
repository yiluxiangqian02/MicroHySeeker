"""
数据模型：配置、泵定义、程序步骤
"""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
from pathlib import Path


class ProgramStepType(str, Enum):
    """程序步骤类型"""
    TRANSFER = "transfer"
    PREP_SOL = "prep_sol"
    FLUSH = "flush"
    ECHEM = "echem"
    BLANK = "blank"
    EVACUATE = "evacuate"  # 排空 - Flusher的outlet阶段


class ECTechnique(str, Enum):
    """电化学技术"""
    CV = "CV"
    LSV = "LSV"
    I_T = "i-t"
    OCPT = "OCPT"  # 开路电位计时法


class OCPTAction(str, Enum):
    """OCPT 触发动作"""
    LOG = "log"
    PAUSE = "pause"
    ABORT = "abort"


@dataclass
class PumpConfig:
    """单台泵配置"""
    address: int  # 1-12
    name: str
    direction: str = "FWD"  # FWD / REV
    default_rpm: int = 120
    calibration: Dict[str, float] = field(default_factory=lambda: {"ul_per_sec": 0.5})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PumpConfig':
        return PumpConfig(**data)


@dataclass
class DilutionChannel:
    """配液通道"""
    channel_id: str
    solution_name: str
    stock_concentration: float  # mol/L
    pump_address: int  # 1-12
    direction: str = "FWD"
    default_rpm: int = 120
    color: str = "#00FF00"
    tube_diameter_mm: float = 1.0  # 管道内径 (mm)，用于计算位移和体积

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DilutionChannel':
        # 向后兼容: 旧配置可能没有tube_diameter_mm
        data = data.copy()
        if 'tube_diameter_mm' not in data:
            data['tube_diameter_mm'] = 1.0
        return DilutionChannel(**data)


@dataclass
class FlushChannel:
    """冲洗通道"""
    channel_id: str
    pump_name: str
    pump_address: int  # 1-12
    direction: str = "FWD"
    rpm: int = 100
    cycle_duration_s: float = 30.0
    work_type: str = "Transfer"  # Inlet, Transfer, Outlet
    tube_diameter_mm: float = 1.0  # 管道内径 (mm)，用于计算位移和体积

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FlushChannel':
        # 向后兼容: 旧配置可能没有tube_diameter_mm
        data = data.copy()
        if 'tube_diameter_mm' not in data:
            data['tube_diameter_mm'] = 1.0
        return FlushChannel(**data)


@dataclass
class ECSettings:
    """电化学设置"""
    technique: ECTechnique = ECTechnique.CV
    e0: Optional[float] = None  # 起始电位 (V)
    eh: Optional[float] = None  # 高电位 (V)
    el: Optional[float] = None  # 低电位 (V)
    ef: Optional[float] = None  # 最终电位 (V)
    scan_rate: Optional[float] = None  # 扫描速率 (V/s)
    sample_interval_ms: int = 100
    sensitivity: str = "AUTO"
    autosensitivity: bool = True
    quiet_time_s: float = 0.0
    run_time_s: Optional[float] = None
    seg_num: int = 1
    scan_dir: str = "FWD"
    
    # OCPT 反向电流检测
    ocpt_enabled: bool = False
    ocpt_threshold_uA: float = -50.0
    ocpt_action: OCPTAction = OCPTAction.LOG
    ocpt_monitor_window_ms: int = 100

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['technique'] = self.technique.value
        d['ocpt_action'] = self.ocpt_action.value
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ECSettings':
        data = data.copy()
        if isinstance(data.get('technique'), str):
            data['technique'] = ECTechnique(data['technique'])
        if isinstance(data.get('ocpt_action'), str):
            data['ocpt_action'] = OCPTAction(data['ocpt_action'])
        return ECSettings(**data)


@dataclass
class PrepSolStep:
    """配液步骤参数"""
    target_concentration: float = 0.0  # 废弃，保留兼容
    is_solvent: bool = False  # 废弃，保留兼容
    injection_order: List[str] = field(default_factory=list)  # 按注液顺序列出溶液名称
    total_volume_ul: float = 100000.0  # 默认100mL = 100000μL
    
    # 新增：每个溶液的目标浓度 {溶液名称: 目标浓度}
    target_concentrations: Dict[str, float] = field(default_factory=dict)
    # 新增：溶剂标记 {溶液名称: 是否为溶剂}
    solvent_flags: Dict[str, bool] = field(default_factory=dict)
    # 新增：是否选中 {溶液名称: 是否选中}
    selected_solutions: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PrepSolStep':
        # 确保新字段存在
        if 'target_concentrations' not in data:
            data['target_concentrations'] = {}
        if 'solvent_flags' not in data:
            data['solvent_flags'] = {}
        if 'selected_solutions' not in data:
            data['selected_solutions'] = {}
        return PrepSolStep(**data)
    
    def get_summary(self) -> str:
        """获取配液步骤摘要"""
        selected = [name for name, sel in self.selected_solutions.items() if sel]
        if not selected:
            return "无配液"
        
        parts = []
        for name in self.injection_order:
            if name in selected:
                conc = self.target_concentrations.get(name, 0)
                is_solvent = self.solvent_flags.get(name, False)
                if is_solvent:
                    parts.append(f"{name}(溶剂)")
                elif conc > 0:
                    parts.append(f"{name}:{conc:.3f}M")
        
        vol_ml = self.total_volume_ul / 1000.0
        # 为大体积添加千位分隔符显示
        if vol_ml >= 1000:
            vol_str = f"{vol_ml:,.1f}mL"
        else:
            vol_str = f"{vol_ml:.1f}mL"
        
        return vol_str + (", " + ", ".join(parts) if parts else "")


@dataclass
class ProgStep:
    """程序步骤"""
    step_id: str
    step_type: ProgramStepType
    pump_address: Optional[int] = None
    pump_direction: Optional[str] = None
    pump_rpm: Optional[int] = None
    volume_ul: Optional[float] = None
    duration_s: Optional[float] = None
    
    # 移液持续时间（替代体积）
    transfer_duration: Optional[float] = None  # 持续时间数值
    transfer_duration_unit: str = "s"  # 单位: ms, s, min, hr, cycle
    
    # PrepSol 特定字段
    prep_sol_params: Optional[PrepSolStep] = None
    
    # Flush 特定字段
    flush_channel_id: Optional[str] = None
    flush_rpm: Optional[int] = None
    flush_cycle_duration_s: Optional[float] = None
    flush_cycles: int = 1
    
    # EChem 特定字段
    ec_settings: Optional[ECSettings] = None
    
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['step_type'] = self.step_type.value
        if self.prep_sol_params:
            d['prep_sol_params'] = self.prep_sol_params.to_dict()
        if self.ec_settings:
            d['ec_settings'] = self.ec_settings.to_dict()
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ProgStep':
        data = data.copy()
        if isinstance(data.get('step_type'), str):
            data['step_type'] = ProgramStepType(data['step_type'])
        if data.get('prep_sol_params') and isinstance(data['prep_sol_params'], dict):
            data['prep_sol_params'] = PrepSolStep.from_dict(data['prep_sol_params'])
        if data.get('ec_settings') and isinstance(data['ec_settings'], dict):
            data['ec_settings'] = ECSettings.from_dict(data['ec_settings'])
        return ProgStep(**data)


@dataclass
class Experiment:
    """实验程序"""
    exp_id: str
    exp_name: str
    steps: List[ProgStep] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'exp_id': self.exp_id,
            'exp_name': self.exp_name,
            'steps': [s.to_dict() for s in self.steps],
            'notes': self.notes,
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Experiment':
        exp = Experiment(
            exp_id=data.get('exp_id', ''),
            exp_name=data.get('exp_name', ''),
            notes=data.get('notes', ''),
        )
        exp.steps = [ProgStep.from_dict(s) for s in data.get('steps', [])]
        return exp

    @staticmethod
    def from_json_str(json_str: str) -> 'Experiment':
        data = json.loads(json_str)
        return Experiment.from_dict(data)


@dataclass
class SystemConfig:
    """系统全局配置"""
    rs485_port: str = "COM1"
    rs485_baudrate: int = 9600
    mock_mode: bool = True  # Mock模式，默认开启
    
    pumps: List[PumpConfig] = field(default_factory=list)
    dilution_channels: List[DilutionChannel] = field(default_factory=list)
    flush_channels: List[FlushChannel] = field(default_factory=list)
    
    calibration_data: Dict[int, Dict[str, float]] = field(default_factory=dict)  # pump_address -> calibration
    
    data_dir: str = "./data"

    def initialize_default_pumps(self):
        """初始化 12 台泵（仅一次）"""
        if not self.pumps:
            for i in range(1, 13):
                self.pumps.append(PumpConfig(
                    address=i,
                    name=f"Pump_{i}",
                    direction="FWD",
                    default_rpm=120,
                    calibration={"ul_per_sec": 0.5}
                ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rs485_port': self.rs485_port,
            'rs485_baudrate': self.rs485_baudrate,
            'mock_mode': self.mock_mode,
            'pumps': [p.to_dict() for p in self.pumps],
            'dilution_channels': [c.to_dict() for c in self.dilution_channels],
            'flush_channels': [c.to_dict() for c in self.flush_channels],
            'calibration_data': self.calibration_data,
            'data_dir': self.data_dir,
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SystemConfig':
        config = SystemConfig(
            rs485_port=data.get('rs485_port', 'COM1'),
            rs485_baudrate=data.get('rs485_baudrate', 9600),
            mock_mode=data.get('mock_mode', True),
            calibration_data=data.get('calibration_data', {}),
            data_dir=data.get('data_dir', './data'),
        )
        config.pumps = [PumpConfig.from_dict(p) for p in data.get('pumps', [])]
        config.dilution_channels = [DilutionChannel.from_dict(c) for c in data.get('dilution_channels', [])]
        config.flush_channels = [FlushChannel.from_dict(c) for c in data.get('flush_channels', [])]
        return config

    @staticmethod
    def from_json_str(json_str: str) -> 'SystemConfig':
        data = json.loads(json_str)
        return SystemConfig.from_dict(data)

    def save_to_file(self, file_path: str):
        """保存配置到 JSON 文件"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json_str())

    @staticmethod
    def load_from_file(file_path: str) -> 'SystemConfig':
        """从 JSON 文件加载配置"""
        if not Path(file_path).exists():
            return SystemConfig()
        with open(file_path, 'r', encoding='utf-8') as f:
            return SystemConfig.from_json_str(f.read())
