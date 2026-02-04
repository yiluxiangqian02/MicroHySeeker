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
    EChem = "echem"
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DilutionChannel':
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FlushChannel':
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
    target_concentration: float  # mol/L
    is_solvent: bool = False
    injection_order: List[str] = field(default_factory=list)  # 按注液顺序列出通道 ID
    total_volume_ul: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PrepSolStep':
        return PrepSolStep(**data)


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
    evacuate_only: bool = False  # 仅排空，不注水冲洗
    
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
