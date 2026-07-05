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
    EIS = "EIS"    # 交流阻抗谱
    ADT = "ADT"    # 加速耐久性测试 (Accelerated Durability Test)


# ---- 向后兼容：旧 OCPT 枚举（已废弃，保留以防旧配置文件反序列化）----
class OCPTAction(str, Enum):
    """[已废弃] 旧 OCPT 触发动作"""
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
    total_volume_ml: float = 0.0       # 原液总量 (mL)，用户配置; 0=不追踪
    remaining_volume_ml: float = 0.0   # 剩余量 (mL)，运行时递减

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DilutionChannel':
        # 向后兼容: 旧配置可能没有tube_diameter_mm / total_volume_ml / remaining_volume_ml
        data = data.copy()
        if 'tube_diameter_mm' not in data:
            data['tube_diameter_mm'] = 1.0
        if 'total_volume_ml' not in data:
            data['total_volume_ml'] = 0.0
        if 'remaining_volume_ml' not in data:
            data['remaining_volume_ml'] = 0.0
        return DilutionChannel(**data)


@dataclass
class FlushChannel:
    """冲洗通道"""
    channel_id: str
    pump_name: str
    pump_address: int  # 1-12
    direction: str = "FWD"
    rpm: int = 100
    cycle_duration_s: float = 30.0  # 保留用于向后兼容
    work_type: str = "Transfer"  # Inlet, Transfer, Outlet
    tube_diameter_mm: float = 1.0  # 管道内径 (mm)，用于计算位移和体积
    total_volume_ml: float = float('inf')  # 原液总量 (mL), inf=不限量
    remaining_volume_ml: float = 0.0  # 剩余量 (mL)，Inlet泵运行时递减

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # JSON 不支持 inf, 用 null 表示
        if d.get('total_volume_ml') is not None and d['total_volume_ml'] == float('inf'):
            d['total_volume_ml'] = None
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FlushChannel':
        # 向后兼容: 旧配置可能没有tube_diameter_mm / total_volume_ml / remaining_volume_ml
        data = data.copy()
        if 'tube_diameter_mm' not in data:
            data['tube_diameter_mm'] = 1.0
        # total_volume_ml: None / 缺失 → inf
        if 'total_volume_ml' not in data or data['total_volume_ml'] is None:
            data['total_volume_ml'] = float('inf')
        if 'remaining_volume_ml' not in data:
            data['remaining_volume_ml'] = 0.0
        return FlushChannel(**data)


@dataclass
class ECSettings:
    """电化学设置"""
    technique: ECTechnique = ECTechnique.CV
    e0: Optional[float] = -0.8  # 起始电位 (V)
    eh: Optional[float] = -0.8  # 高电位 (V)
    el: Optional[float] = -1.8  # 低电位 (V)
    ef: Optional[float] = -0.8  # 最终电位 (V)
    scan_rate: Optional[float] = 0.05  # 扫描速率 (V/s)
    sample_interval_ms: int = 1
    sensitivity: Optional[float] = 0.1  # 灵敏度 (A/V), None表示自动
    autosensitivity: bool = False
    quiet_time_s: float = 2.0
    run_time_s: Optional[float] = 120.0
    seg_num: int = 6
    scan_dir: str = "FWD"
    
    # EIS 参数
    freq_low: float = 1.0          # 最低频率 (Hz)
    freq_high: float = 100000.0    # 最高频率 (Hz)
    amplitude: float = 0.005       # AC 振幅 (V)
    bias_mode: int = 0             # 偏置模式: 0=vs Eref, 1=vs Eoc
    
    # Dummy Cell 模式 (测试用，不连接真实电极)
    use_dummy_cell: bool = False
    
    # ADT (加速耐久性测试) 参数 — 替代旧 OCPT
    adt_enabled: bool = False
    adt_num_cycles: int = 500              # ADT 循环轮数
    # -- CP (计时电位法) 完整参数 --
    adt_cathodic_current_mA: float = -250.0  # 阴极电流 ic (mA), 默认使用无 Booster 风险参数
    adt_cp_anodic_current_mA: float = 0.0    # 阳极电流 ia (mA)
    adt_cp_e_high: float = 10.0              # CP 电位上限 eh (V)
    adt_cp_e_low: float = -10.0              # CP 电位下限 el (V)
    adt_cp_high_e_hold_time: float = 0.0     # 高电位保持时间 heht (s)
    adt_cp_low_e_hold_time: float = 0.0      # 低电位保持时间 leht (s)
    adt_cathodic_duration_s: float = 3.0     # 阴极时间 tc (s)
    adt_cp_anodic_time_s: float = 0.05       # 阳极时间 ta (s)
    adt_cp_polarity: str = 'n'               # 首步极性 pn: 'p'=阳极先, 'n'=阴极先
    adt_cp_sample_interval: float = 0.01     # CP 采样间隔 si (s)
    adt_cp_segments: int = 1                 # CP 段数 cl
    adt_cp_priority: str = 'time'            # 优先级: 'time'=时间优先, 'potential'=电位优先
    # -- CA (计时电流法) 完整参数 --
    adt_anodic_potential_V: float = 0.0      # 初始电位 ei (V)
    adt_ca_e_high: float = 0.476             # 高电位限 eh (V)
    adt_ca_e_low: float = -2.4               # 低电位限 el (V)
    adt_ca_polarity: str = 'p'               # 变化方向 pn: 'p'=正向, 'n'=负向
    adt_ca_steps: int = 1                    # 阶跃数 cl (1~320)
    adt_anodic_duration_s: float = 2.0       # 脉冲宽度 pw (s)
    adt_ca_sample_interval: float = 0.01     # CA 采样间隔 si (s)
    adt_ca_quiet_time: float = 0.0           # CA 静置时间 qt (s)
    adt_ca_sensitivity: float = 0.1          # CA 灵敏度 sens (A/V)

    # iR 补偿 (手动正反馈法)
    ir_compensation_enabled: bool = False  # 是否启用 iR 补偿
    ir_compensation_ohm: float = 0.0  # 补偿电阻 (Ω), 0 = 不补偿, 通过 EIS 预先测量

    # ---- 旧 OCPT 字段 (向后兼容，加载旧配置时不报错) ----
    ocpt_enabled: bool = False
    ocpt_threshold_uA: float = -50.0
    ocpt_action: OCPTAction = OCPTAction.LOG
    ocpt_monitor_window_ms: int = 100

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['technique'] = self.technique.value if hasattr(self.technique, 'value') else str(self.technique)
        # 不再序列化旧 OCPT 字段
        for k in ('ocpt_enabled', 'ocpt_threshold_uA', 'ocpt_action', 'ocpt_monitor_window_ms'):
            d.pop(k, None)
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ECSettings':
        data = data.copy()
        # 技术类型：兼容旧 OCPT → ADT
        tech_str = data.get('technique', 'CV')
        if isinstance(tech_str, str):
            if tech_str == 'OCPT':
                tech_str = 'ADT'
            try:
                data['technique'] = ECTechnique(tech_str)
            except ValueError:
                data['technique'] = ECTechnique.CV
        # 旧 ocpt_action 兼容
        if isinstance(data.get('ocpt_action'), str):
            try:
                data['ocpt_action'] = OCPTAction(data['ocpt_action'])
            except ValueError:
                data['ocpt_action'] = OCPTAction.LOG
        # 兼容旧字段名
        if 'sample_interval' in data and 'sample_interval_ms' not in data:
            data['sample_interval_ms'] = int(data.pop('sample_interval'))
        elif 'sample_interval' in data:
            data.pop('sample_interval')
        # 过滤未知字段
        valid_keys = set(ECSettings.__dataclass_fields__.keys())
        data = {k: v for k, v in data.items() if k in valid_keys}
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
    # 新增：注液顺序编号 {溶液名称: 顺序号}，相同编号表示同时注液
    injection_order_numbers: Dict[str, int] = field(default_factory=dict)
    # Prep strategy:
    # - standard: use injection_order/injection_order_numbers directly.
    # - solvent_transfer_first: inject solvent channels, run Transfer, then inject non-solvent channels.
    prep_strategy: str = "standard"
    # Used only by solvent_transfer_first. 0 means auto (solvent volume + 20 mL).
    intermediate_transfer_volume_ul: float = 0.0

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
        if 'injection_order_numbers' not in data:
            data['injection_order_numbers'] = {}
        if 'prep_strategy' not in data:
            data['prep_strategy'] = "standard"
        if 'intermediate_transfer_volume_ul' not in data:
            data['intermediate_transfer_volume_ul'] = 0.0
        # injection_order 为空时，从 injection_order_numbers + selected_solutions 派生
        io = data.get('injection_order')
        if not io or (isinstance(io, str)):
            ion = data.get('injection_order_numbers', {})
            sel = data.get('selected_solutions', {})
            sf  = data.get('solvent_flags', {})
            # 已选中且有顺序号的溶液，按顺序号排列
            ordered = sorted(
                [k for k in ion if sel.get(k, True)],
                key=lambda x: ion[x],
            )
            # 追加已选中但无顺序号的溶液（如溶剂 H2O）
            for name, is_sel in sel.items():
                if is_sel and name not in ordered:
                    ordered.append(name)
            if ordered:
                data['injection_order'] = ordered
            elif isinstance(io, str) and io:
                data['injection_order'] = [io]
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

    # 并行执行组: 0=串行(默认), 相同正整数=同时执行
    parallel_group: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['step_type'] = self.step_type.value if hasattr(self.step_type, 'value') else str(self.step_type)
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
    """实验程序 (v2.0 协议)"""
    exp_id: str
    exp_name: str
    steps: List[ProgStep] = field(default_factory=list)
    notes: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    operator: str = ""
    _protocol_version: str = "2.0"
    _created_at: str = ""
    _modified_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        from datetime import datetime
        now_iso = datetime.now().isoformat()
        return {
            '_protocol_version': self._protocol_version,
            '_created_at': self._created_at or now_iso,
            '_modified_at': now_iso,
            '_software_version': '1.0.0',
            'exp_id': self.exp_id,
            'exp_name': self.exp_name,
            'description': self.description,
            'tags': self.tags,
            'operator': self.operator,
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
            description=data.get('description', ''),
            tags=data.get('tags', []),
            operator=data.get('operator', ''),
            _protocol_version=data.get('_protocol_version', '1.0'),
            _created_at=data.get('_created_at', ''),
            _modified_at=data.get('_modified_at', ''),
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
    rs485_port: str = "COM10"
    rs485_baudrate: int = 38400
    mock_mode: bool = False  # Mock模式，默认关闭（真实硬件）
    auto_connect: bool = True  # 启动时自动连接RS485
    
    pumps: List[PumpConfig] = field(default_factory=list)
    dilution_channels: List[DilutionChannel] = field(default_factory=list)
    flush_channels: List[FlushChannel] = field(default_factory=list)
    
    calibration_data: Dict[int, Dict[str, float]] = field(default_factory=dict)  # pump_address -> calibration
    calibration_ui_state: Dict[str, Any] = field(default_factory=dict)
    
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
            'auto_connect': self.auto_connect,
            'pumps': [p.to_dict() for p in self.pumps],
            'dilution_channels': [c.to_dict() for c in self.dilution_channels],
            'flush_channels': [c.to_dict() for c in self.flush_channels],
            'calibration_data': {str(k): v for k, v in self.calibration_data.items()},
            'calibration_ui_state': self.calibration_ui_state,
            'data_dir': self.data_dir,
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SystemConfig':
        # calibration_data 的 key 在 JSON 中是字符串，需转回 int
        raw_cal = data.get('calibration_data', {})
        calibration_data = {}
        for k, v in raw_cal.items():
            try:
                calibration_data[int(k)] = v
            except (ValueError, TypeError):
                calibration_data[k] = v
        
        config = SystemConfig(
            rs485_port=data.get('rs485_port', 'COM10'),
            rs485_baudrate=data.get('rs485_baudrate', 38400),
            mock_mode=data.get('mock_mode', False),
            auto_connect=data.get('auto_connect', True),
            calibration_data=calibration_data,
            calibration_ui_state=data.get('calibration_ui_state', {}),
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

    def save(self):
        """保存配置到加载时的源文件（需先通过 load_from_file 加载）"""
        if hasattr(self, '_source_path') and self._source_path:
            self.save_to_file(self._source_path)

    @staticmethod
    def load_from_file(file_path: str) -> 'SystemConfig':
        """从 JSON 文件加载配置"""
        if not Path(file_path).exists():
            cfg = SystemConfig()
            cfg._source_path = str(Path(file_path).resolve())
            return cfg
        with open(file_path, 'r', encoding='utf-8') as f:
            cfg = SystemConfig.from_json_str(f.read())
        cfg._source_path = str(Path(file_path).resolve())
        return cfg
