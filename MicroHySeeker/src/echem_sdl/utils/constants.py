"""
RS485 Protocol Constants

定义 RS485 通信协议相关常量，包括帧头、命令字节、编码器参数等。
"""

# ============================================================================
# 帧头常量
# ============================================================================

TX_HEADER = 0xFA  # 发送帧头 (主机→从机)
RX_HEADER = 0xFB  # 接收帧头 (从机→主机)


# ============================================================================
# 命令常量 - 读取命令 (Query)
# ============================================================================

CMD_READ_ENCODER = 0x30           # 读取进位制多圈编码器值
CMD_READ_ENCODER_ACCUM = 0x31     # 读取累加制多圈编码器值 (用于位置模式)
CMD_READ_SPEED = 0x32             # 读取当前转速
CMD_READ_IO = 0x34                # 读取IO状态
CMD_READ_ENCODER_RAW = 0x35       # 读取原始累加多圈编码器值
CMD_READ_ENABLE = 0x3A            # 读取使能状态
CMD_READ_HOMING_STATUS = 0x3B     # 读取单圈回零状态
CMD_CLEAR_STALL = 0x3D            # 解除堵转状态
CMD_READ_FAULT = 0x3E             # 读取故障状态
CMD_READ_VERSION = 0x40           # 读取固件版本
CMD_READ_ALL_SETTINGS = 0x47      # 读取所有设置参数
CMD_READ_ALL_STATUS = 0x48        # 读取所有状态参数
CMD_READ_RUN_STATUS = 0xF1        # 读取运行状态


# ============================================================================
# 命令常量 - 控制命令 (Control)
# ============================================================================

CMD_ENABLE = 0xF3            # 使能/禁用电机 (串行模式)
CMD_POSITION_REL = 0xF4      # 位置模式3: 按坐标值相对运动 (16384编码器单位/圈)
CMD_POSITION_ABS = 0xF5      # 位置模式4: 按坐标值绝对运动 (16384编码器单位/圈)
CMD_SPEED = 0xF6             # 速度模式运行
CMD_STOP_EMERGENCY = 0xF7    # 紧急停止
CMD_POSITION_PULSE_REL = 0xFD  # 位置模式1: 按脉冲数相对运动
CMD_POSITION_PULSE_ABS = 0xFE  # 位置模式2: 按脉冲数绝对运动
CMD_STOP = 0xFE              # 紧急停止 (兼容旧代码)

# 别名 (向后兼容)
CMD_POSITION = CMD_POSITION_REL


# ============================================================================
# 编码器参数
# ============================================================================

ENCODER_DIVISIONS_PER_REV = 16384  # 编码器分度/圈 (0x4000)
MAX_RPM = 3000                      # 最大转速 (RPM)
MIN_RPM = 0                         # 最小转速 (RPM)
DEFAULT_ACCELERATION = 0x10         # 默认加速度 (0-255)
DEFAULT_DILUTION_ACCELERATION = 0x02  # 配液默认加速度 (较平稳)
DEFAULT_DILUTION_SPEED = 100        # 配液默认速度 (RPM)

# ============================================================================
# SR_VFOC 控制模式常量
# ============================================================================

# 工作模式 (Mode菜单)
MODE_CR_OPEN = 0x00   # 脉冲接口开环模式
MODE_CR_CLOSE = 0x01  # 脉冲接口闭环模式
MODE_CR_VFOC = 0x02   # 脉冲接口FOC模式
MODE_SR_OPEN = 0x03   # 串行接口开环模式
MODE_SR_CLOSE = 0x04  # 串行接口闭环模式
MODE_SR_VFOC = 0x05   # 串行接口FOC模式 (当前使用)

# 运行状态返回值 (0xF1指令)
RUN_STATUS_STOPPED = 0x01   # 电机停止运行
RUN_STATUS_ACCEL = 0x02     # 电机加速运行
RUN_STATUS_DECEL = 0x03     # 电机减速运行
RUN_STATUS_FULL = 0x04      # 电机全速运行
RUN_STATUS_HOMING = 0x05    # 电机归零运行
RUN_STATUS_CAL = 0x06       # 电机校准运行

# 位置控制返回值
POS_CTRL_FAIL = 0x00        # 位置控制失败
POS_CTRL_START = 0x01       # 位置控制开始
POS_CTRL_COMPLETE = 0x02    # 位置控制完成
POS_CTRL_LIMIT = 0x03       # 触碰限位停止


# ============================================================================
# 串口参数 (与原C#项目一致)
# ============================================================================

DEFAULT_BAUDRATE = 38400            # 波特率
DEFAULT_DATA_BITS = 8               # 数据位
DEFAULT_STOP_BITS = 2               # 停止位 (serial.STOPBITS_TWO)
DEFAULT_PARITY = 'N'                # 校验位 (N=None)
DEFAULT_TIMEOUT = 0.5               # 读取超时 (秒)
DEFAULT_WRITE_TIMEOUT = 0.5         # 写入超时 (秒)


# ============================================================================
# 通信参数
# ============================================================================

DEFAULT_CMD_INTERVAL_MS = 25        # 命令间隔 (毫秒) - 原C#为25ms
MAX_FRAME_SIZE = 256                # 最大帧长度
OFFLINE_THRESHOLD_SEC = 5.0         # 掉线阈值 (秒)
DISCOVER_TIMEOUT_PER_ADDR = 0.1     # 设备扫描单地址超时 (秒)


# ============================================================================
# 设备地址范围
# ============================================================================

MIN_DEVICE_ADDRESS = 1              # 最小设备地址
MAX_DEVICE_ADDRESS = 12             # 最大设备地址 (系统支持12个泵)
SCAN_ADDRESS_RANGE = range(MIN_DEVICE_ADDRESS, MAX_DEVICE_ADDRESS + 1)


# ============================================================================
# 响应帧长度映射 (根据命令返回不同长度)
# ============================================================================

EXPECTED_RESPONSE_LENGTH = {
    CMD_READ_ENCODER: 8,          # 帧头(1)+地址(1)+命令(1)+进位值(4)+编码器值(2)+校验(1) = 10? 文档说8
    CMD_READ_ENCODER_ACCUM: 9,    # 帧头(1)+地址(1)+命令(1)+编码器值(6)+校验(1) = 10? 文档说int48_t
    CMD_READ_SPEED: 6,            # 帧头(1)+地址(1)+命令(1)+速度(2)+校验(1) = 6
    CMD_READ_VERSION: 8,          # 版本信息
    CMD_READ_ALL_SETTINGS: 38,    # 所有设置参数
    CMD_READ_ALL_STATUS: 31,      # 所有状态参数
    CMD_READ_RUN_STATUS: 5,       # 帧头(1)+地址(1)+命令(1)+状态(1)+校验(1) = 5
    CMD_READ_ENABLE: 5,           # 使能状态
    CMD_READ_FAULT: 5,            # 故障状态
    CMD_CLEAR_STALL: 5,           # 解除堵转确认
    CMD_ENABLE: 5,                # 使能确认
    CMD_SPEED: 5,                 # 速度设置确认
    CMD_POSITION_REL: 5,          # 位置模式3确认
    CMD_POSITION_ABS: 5,          # 位置模式4确认
    CMD_POSITION_PULSE_REL: 5,    # 位置模式1确认
    CMD_POSITION_PULSE_ABS: 5,    # 位置模式2确认
    CMD_STOP_EMERGENCY: 5,        # 紧急停止确认
}

DEFAULT_RESPONSE_LENGTH = 5          # 默认响应长度 (最小有效帧)


# ============================================================================
# 方向常量
# ============================================================================

DIRECTION_FORWARD = 0x00             # 正转方向标志
DIRECTION_REVERSE = 0x80             # 反转方向标志


# ============================================================================
# 命令名称映射 (用于日志)
# ============================================================================

CMD_NAME_MAP = {
    CMD_READ_ENCODER: "READ_ENCODER",
    CMD_READ_ENCODER_ACCUM: "READ_ENCODER_ACCUM",
    CMD_READ_SPEED: "READ_SPEED",
    CMD_READ_IO: "READ_IO",
    CMD_READ_ENCODER_RAW: "READ_ENCODER_RAW",
    CMD_READ_ENABLE: "READ_ENABLE",
    CMD_READ_HOMING_STATUS: "READ_HOMING_STATUS",
    CMD_CLEAR_STALL: "CLEAR_STALL",
    CMD_READ_FAULT: "READ_FAULT",
    CMD_READ_VERSION: "READ_VERSION",
    CMD_READ_ALL_SETTINGS: "READ_ALL_SETTINGS",
    CMD_READ_ALL_STATUS: "READ_ALL_STATUS",
    CMD_READ_RUN_STATUS: "READ_RUN_STATUS",
    CMD_ENABLE: "ENABLE",
    CMD_POSITION_REL: "POSITION_REL",
    CMD_POSITION_ABS: "POSITION_ABS",
    CMD_SPEED: "SPEED",
    CMD_STOP_EMERGENCY: "STOP_EMERGENCY",
    CMD_POSITION_PULSE_REL: "POSITION_PULSE_REL",
    CMD_POSITION_PULSE_ABS: "POSITION_PULSE_ABS",
    CMD_STOP: "STOP",
}


def get_cmd_name(cmd: int) -> str:
    """获取命令名称
    
    Args:
        cmd: 命令字节
        
    Returns:
        str: 命令名称，未知命令返回 "UNKNOWN_0xXX"
    """
    return CMD_NAME_MAP.get(cmd, f"UNKNOWN_0x{cmd:02X}")


def get_expected_response_length(cmd: int) -> int:
    """获取命令期望的响应长度
    
    Args:
        cmd: 命令字节
        
    Returns:
        int: 期望的响应帧长度
    """
    return EXPECTED_RESPONSE_LENGTH.get(cmd, DEFAULT_RESPONSE_LENGTH)
