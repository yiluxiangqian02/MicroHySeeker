"""
ProgStep - 程序步骤模块

定义实验程序的基本执行单元，支持多种步骤类型。
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
import json


class StepType(str, Enum):
    """步骤类型枚举"""
    PREP_SOL = "prep_sol"      # 配液
    TRANSFER = "transfer"       # 转移/移液
    FLUSH = "flush"             # 冲洗
    ECHEM = "echem"             # 电化学
    BLANK = "blank"             # 空白/等待
    EVACUATE = "evacuate"       # 抽空


class ECTechnique(str, Enum):
    """电化学技术枚举"""
    CV = "CV"           # 循环伏安法
    LSV = "LSV"         # 线性扫描伏安法
    IT = "i-t"          # 安培-时间曲线
    OCPT = "OCPT"       # 开路电位测量
    CA = "CA"           # 计时电流法
    CP = "CP"           # 计时电位法
    DPV = "DPV"         # 差分脉冲伏安法
    SWV = "SWV"         # 方波伏安法


# ========================
# 配置数据类
# ========================

@dataclass
class PrepSolConfig:
    """配液配置
    
    支持多批次注入模式（类似C# InjectOrder）:
    - 单批次: 所有稀释剂一次性配制
    - 多批次: 按注入顺序分批配制，支持间隔时间
    """
    # 通道浓度映射 {"D1": 0.5, "D2": 0.3, ...}
    concentrations: Dict[str, float] = field(default_factory=dict)
    # 总体积 (uL)
    total_volume_ul: float = 100.0
    # 注液顺序（默认按配置顺序）
    injection_order: Optional[List[str]] = None
    # 混合次数
    mix_count: int = 0
    # 混合体积 (uL)
    mix_volume_ul: float = 50.0
    # === 多批次注入支持 ===
    # 启用多批次注入
    multi_batch: bool = False
    # 批次数量
    batch_count: int = 1
    # 批次间隔时间 (s)
    batch_interval_s: float = 1.0
    # 每批次体积百分比列表（如 [0.5, 0.5] 表示分两批各50%）
    batch_volumes: Optional[List[float]] = None
    
    def get_concentration(self, channel_id: str) -> float:
        """获取通道浓度"""
        return self.concentrations.get(channel_id, 0.0)
    
    def get_injection_order(self) -> List[str]:
        """获取注液顺序"""
        if self.injection_order:
            return self.injection_order
        return list(self.concentrations.keys())
    
    def get_batch_volumes_ul(self) -> List[float]:
        """获取每批次的体积(uL)"""
        if not self.multi_batch or self.batch_count <= 1:
            return [self.total_volume_ul]
        
        if self.batch_volumes and len(self.batch_volumes) == self.batch_count:
            # 使用指定的百分比
            return [self.total_volume_ul * pct for pct in self.batch_volumes]
        else:
            # 均分
            vol_per_batch = self.total_volume_ul / self.batch_count
            return [vol_per_batch] * self.batch_count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "concentrations": self.concentrations,
            "total_volume_ul": self.total_volume_ul,
            "injection_order": self.injection_order,
            "mix_count": self.mix_count,
            "mix_volume_ul": self.mix_volume_ul,
            "multi_batch": self.multi_batch,
            "batch_count": self.batch_count,
            "batch_interval_s": self.batch_interval_s,
            "batch_volumes": self.batch_volumes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrepSolConfig":
        return cls(
            concentrations=data.get("concentrations", {}),
            total_volume_ul=data.get("total_volume_ul", 100.0),
            injection_order=data.get("injection_order"),
            mix_count=data.get("mix_count", 0),
            mix_volume_ul=data.get("mix_volume_ul", 50.0),
            multi_batch=data.get("multi_batch", False),
            batch_count=data.get("batch_count", 1),
            batch_interval_s=data.get("batch_interval_s", 1.0),
            batch_volumes=data.get("batch_volumes"),
        )


@dataclass
class TransferConfig:
    """转移/移液配置"""
    # 泵地址 (1-12)
    pump_address: int = 1
    # 目标位置
    target_position: str = "pool"
    # 转移体积 (uL)
    volume_ul: float = 100.0
    # 转移速度 (RPM)
    speed_rpm: int = 100
    # 方向 FWD/REV
    direction: str = "FWD"
    # 持续时间 (s) - 替代体积计算
    duration_s: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransferConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FlushConfig:
    """冲洗配置"""
    # 冲洗轮数
    cycles: int = 3
    # 冲洗体积 (uL) - 可选
    volume_ul: float = 500.0
    # 使用的冲洗通道
    channels: List[str] = field(default_factory=lambda: ["inlet", "transfer", "outlet"])
    # 每阶段时间 (s)
    phase_duration_s: float = 10.0
    # 泵速度 (RPM)
    speed_rpm: int = 200
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycles": self.cycles,
            "volume_ul": self.volume_ul,
            "channels": self.channels,
            "phase_duration_s": self.phase_duration_s,
            "speed_rpm": self.speed_rpm,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlushConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ECConfig:
    """电化学配置"""
    # 技术类型
    technique: str = "CV"
    # 初始电位 (V)
    e_init: float = 0.0
    # 最高电位 (V)
    e_high: float = 0.8
    # 最低电位 (V)
    e_low: float = -0.2
    # 终止电位 (V)
    e_final: float = 0.0
    # 扫描速率 (V/s)
    scan_rate: float = 0.1
    # 扫描段数
    segments: int = 2
    # 静置时间 (s)
    quiet_time: float = 2.0
    # 运行时间 (s) - 用于 i-t, OCPT
    run_time: float = 60.0
    # 采样间隔 (s)
    sample_interval: float = 0.001
    # 灵敏度 (-1 = 自动)
    sensitivity: float = -1.0
    # OCPT 监控
    ocpt_enabled: bool = False
    ocpt_threshold_uA: float = -50.0
    ocpt_action: str = "log"  # log/pause/abort
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ECConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BlankConfig:
    """空白/等待配置"""
    # 等待时间 (s)
    wait_time: float = 5.0
    # 描述
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlankConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EvacuateConfig:
    """抽空配置"""
    # 抽空时间 (s)
    evacuate_time: float = 10.0
    # 抽空速度 (RPM)
    speed_rpm: int = 200
    # 使用的泵地址
    pump_address: int = 3  # 默认 outlet 泵
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvacuateConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ========================
# 主类
# ========================

@dataclass
class ProgStep:
    """程序步骤
    
    表示实验程序中的单个执行步骤。
    
    Attributes:
        step_type: 步骤类型
        name: 步骤名称
        enabled: 是否启用
        prep_sol_config: 配液配置
        transfer_config: 转移配置
        flush_config: 冲洗配置
        ec_config: 电化学配置
        blank_config: 空白配置
        evacuate_config: 抽空配置
        
    Example:
        >>> step = ProgStep(
        ...     step_type=StepType.ECHEM,
        ...     name="CV测量",
        ...     ec_config=ECConfig(technique="CV", scan_rate=0.1)
        ... )
    """
    # 基本信息
    step_type: StepType = StepType.BLANK
    name: str = ""
    enabled: bool = True
    notes: str = ""
    
    # 各类型配置（仅对应类型有效）
    prep_sol_config: Optional[PrepSolConfig] = None
    transfer_config: Optional[TransferConfig] = None
    flush_config: Optional[FlushConfig] = None
    ec_config: Optional[ECConfig] = None
    blank_config: Optional[BlankConfig] = None
    evacuate_config: Optional[EvacuateConfig] = None
    
    def get_config(self) -> Optional[object]:
        """获取当前步骤类型的配置"""
        config_map = {
            StepType.PREP_SOL: self.prep_sol_config,
            StepType.TRANSFER: self.transfer_config,
            StepType.FLUSH: self.flush_config,
            StepType.ECHEM: self.ec_config,
            StepType.BLANK: self.blank_config,
            StepType.EVACUATE: self.evacuate_config,
        }
        return config_map.get(self.step_type)
    
    def get_duration(self) -> float:
        """获取步骤预估时长（秒）
        
        Returns:
            float: 预估执行时间
        """
        if self.step_type == StepType.PREP_SOL:
            config = self.prep_sol_config
            if config is None:
                return 0.0
            # 每个通道约 10 秒
            return len(config.concentrations) * 10.0
        
        elif self.step_type == StepType.TRANSFER:
            config = self.transfer_config
            if config is None:
                return 0.0
            if config.duration_s:
                return config.duration_s
            # 基于体积和速度估算
            ul_per_sec = 0.5  # 默认流速
            return config.volume_ul / ul_per_sec
        
        elif self.step_type == StepType.FLUSH:
            config = self.flush_config
            if config is None:
                return 0.0
            # 每轮 3 阶段 x 阶段时间
            return config.cycles * 3 * config.phase_duration_s
        
        elif self.step_type == StepType.ECHEM:
            config = self.ec_config
            if config is None:
                return 0.0
            if config.technique in ["CV", "LSV"]:
                # 基于电位范围和扫描速率
                e_range = config.e_high - config.e_low
                return config.quiet_time + (e_range * config.segments / config.scan_rate)
            elif config.technique in ["i-t", "CA", "IT"]:
                return config.quiet_time + config.run_time
            elif config.technique == "OCPT":
                return config.run_time
            return 60.0
        
        elif self.step_type == StepType.BLANK:
            config = self.blank_config
            return config.wait_time if config else 5.0
        
        elif self.step_type == StepType.EVACUATE:
            config = self.evacuate_config
            return config.evacuate_time if config else 10.0
        
        return 0.0
    
    def validate(self) -> List[str]:
        """验证步骤配置
        
        Returns:
            List[str]: 错误消息列表（空表示有效）
        """
        errors = []
        
        config = self.get_config()
        if config is None and self.step_type != StepType.BLANK:
            errors.append(f"步骤类型 {self.step_type.value} 缺少配置")
            return errors
        
        if self.step_type == StepType.PREP_SOL and self.prep_sol_config:
            if not self.prep_sol_config.concentrations:
                errors.append("配液配置缺少通道")
            if self.prep_sol_config.total_volume_ul <= 0:
                errors.append("总体积必须大于0")
        
        elif self.step_type == StepType.ECHEM and self.ec_config:
            if self.ec_config.e_high <= self.ec_config.e_low:
                errors.append("最高电位必须大于最低电位")
            if self.ec_config.scan_rate <= 0:
                errors.append("扫描速率必须大于0")
        
        elif self.step_type == StepType.FLUSH and self.flush_config:
            if self.flush_config.cycles <= 0:
                errors.append("冲洗轮数必须大于0")
        
        elif self.step_type == StepType.TRANSFER and self.transfer_config:
            if self.transfer_config.volume_ul <= 0 and not self.transfer_config.duration_s:
                errors.append("移液体积或持续时间必须大于0")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "step_type": self.step_type.value,
            "name": self.name,
            "enabled": self.enabled,
            "notes": self.notes,
        }
        
        # 添加对应配置
        if self.prep_sol_config:
            result["prep_sol_config"] = self.prep_sol_config.to_dict()
        if self.transfer_config:
            result["transfer_config"] = self.transfer_config.to_dict()
        if self.flush_config:
            result["flush_config"] = self.flush_config.to_dict()
        if self.ec_config:
            result["ec_config"] = self.ec_config.to_dict()
        if self.blank_config:
            result["blank_config"] = self.blank_config.to_dict()
        if self.evacuate_config:
            result["evacuate_config"] = self.evacuate_config.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgStep":
        """从字典创建"""
        step_type_str = data.get("step_type", "blank")
        try:
            step_type = StepType(step_type_str)
        except ValueError:
            step_type = StepType.BLANK
        
        step = cls(
            step_type=step_type,
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            notes=data.get("notes", ""),
        )
        
        # 加载对应配置
        if "prep_sol_config" in data:
            step.prep_sol_config = PrepSolConfig.from_dict(data["prep_sol_config"])
        if "transfer_config" in data:
            step.transfer_config = TransferConfig.from_dict(data["transfer_config"])
        if "flush_config" in data:
            step.flush_config = FlushConfig.from_dict(data["flush_config"])
        if "ec_config" in data:
            step.ec_config = ECConfig.from_dict(data["ec_config"])
        if "blank_config" in data:
            step.blank_config = BlankConfig.from_dict(data["blank_config"])
        if "evacuate_config" in data:
            step.evacuate_config = EvacuateConfig.from_dict(data["evacuate_config"])
        
        return step
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ProgStep":
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def copy(self) -> "ProgStep":
        """创建副本"""
        return ProgStep.from_dict(self.to_dict())


# ========================
# 工厂方法
# ========================

class ProgStepFactory:
    """步骤工厂 - 快速创建常用步骤"""
    
    @staticmethod
    def create_prep_sol(
        name: str = "配液",
        concentrations: Dict[str, float] = None,
        total_volume_ul: float = 100.0
    ) -> ProgStep:
        """创建配液步骤"""
        return ProgStep(
            step_type=StepType.PREP_SOL,
            name=name,
            prep_sol_config=PrepSolConfig(
                concentrations=concentrations or {},
                total_volume_ul=total_volume_ul
            )
        )
    
    @staticmethod
    def create_transfer(
        name: str = "移液",
        pump_address: int = 1,
        volume_ul: float = 100.0,
        speed_rpm: int = 100,
        direction: str = "FWD"
    ) -> ProgStep:
        """创建移液步骤"""
        return ProgStep(
            step_type=StepType.TRANSFER,
            name=name,
            transfer_config=TransferConfig(
                pump_address=pump_address,
                volume_ul=volume_ul,
                speed_rpm=speed_rpm,
                direction=direction
            )
        )
    
    @staticmethod
    def create_flush(
        name: str = "冲洗",
        cycles: int = 3,
        phase_duration_s: float = 10.0,
        speed_rpm: int = 200
    ) -> ProgStep:
        """创建冲洗步骤"""
        return ProgStep(
            step_type=StepType.FLUSH,
            name=name,
            flush_config=FlushConfig(
                cycles=cycles,
                phase_duration_s=phase_duration_s,
                speed_rpm=speed_rpm
            )
        )
    
    @staticmethod
    def create_cv(
        name: str = "CV",
        e_low: float = -0.2,
        e_high: float = 0.8,
        e_init: float = 0.0,
        e_final: float = 0.0,
        scan_rate: float = 0.1,
        segments: int = 2,
        quiet_time: float = 2.0
    ) -> ProgStep:
        """创建CV步骤"""
        return ProgStep(
            step_type=StepType.ECHEM,
            name=name,
            ec_config=ECConfig(
                technique="CV",
                e_init=e_init,
                e_low=e_low,
                e_high=e_high,
                e_final=e_final,
                scan_rate=scan_rate,
                segments=segments,
                quiet_time=quiet_time
            )
        )
    
    @staticmethod
    def create_lsv(
        name: str = "LSV",
        e_init: float = 0.0,
        e_final: float = 0.8,
        scan_rate: float = 0.1,
        quiet_time: float = 2.0
    ) -> ProgStep:
        """创建LSV步骤"""
        return ProgStep(
            step_type=StepType.ECHEM,
            name=name,
            ec_config=ECConfig(
                technique="LSV",
                e_init=e_init,
                e_final=e_final,
                e_high=max(e_init, e_final),
                e_low=min(e_init, e_final),
                scan_rate=scan_rate,
                segments=1,
                quiet_time=quiet_time
            )
        )
    
    @staticmethod
    def create_it(
        name: str = "i-t",
        run_time: float = 60.0,
        sample_interval: float = 0.1,
        quiet_time: float = 2.0
    ) -> ProgStep:
        """创建 i-t 步骤"""
        return ProgStep(
            step_type=StepType.ECHEM,
            name=name,
            ec_config=ECConfig(
                technique="i-t",
                run_time=run_time,
                sample_interval=sample_interval,
                quiet_time=quiet_time
            )
        )
    
    @staticmethod
    def create_ocpt(
        name: str = "OCPT",
        run_time: float = 60.0,
        sample_interval: float = 0.1
    ) -> ProgStep:
        """创建 OCPT 步骤"""
        return ProgStep(
            step_type=StepType.ECHEM,
            name=name,
            ec_config=ECConfig(
                technique="OCPT",
                run_time=run_time,
                sample_interval=sample_interval,
                quiet_time=0.0
            )
        )
    
    @staticmethod
    def create_blank(
        name: str = "等待",
        wait_time: float = 5.0,
        description: str = ""
    ) -> ProgStep:
        """创建空白/等待步骤"""
        return ProgStep(
            step_type=StepType.BLANK,
            name=name,
            blank_config=BlankConfig(
                wait_time=wait_time,
                description=description
            )
        )
    
    @staticmethod
    def create_evacuate(
        name: str = "抽空",
        evacuate_time: float = 10.0,
        pump_address: int = 3,
        speed_rpm: int = 200
    ) -> ProgStep:
        """创建抽空步骤"""
        return ProgStep(
            step_type=StepType.EVACUATE,
            name=name,
            evacuate_config=EvacuateConfig(
                evacuate_time=evacuate_time,
                pump_address=pump_address,
                speed_rpm=speed_rpm
            )
        )
