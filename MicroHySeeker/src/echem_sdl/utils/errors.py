"""
Exception Definitions for echem_sdl

定义系统中使用的所有自定义异常类。
"""


# ============================================================================
# 基础异常类
# ============================================================================

class EChemSDLError(Exception):
    """echem_sdl 系统错误基类"""
    pass


# ============================================================================
# RS485 协议相关异常
# ============================================================================

class RS485ProtocolError(EChemSDLError):
    """RS485 协议错误基类"""
    pass


class ChecksumError(RS485ProtocolError):
    """校验和错误
    
    当接收帧的校验和与计算值不匹配时抛出。
    """
    pass


class FrameError(RS485ProtocolError):
    """帧格式错误
    
    当接收帧格式不符合协议规范时抛出。
    """
    pass


class InvalidAddressError(RS485ProtocolError):
    """设备地址错误
    
    当设备地址超出有效范围时抛出。
    """
    pass


class InvalidCommandError(RS485ProtocolError):
    """命令字节错误
    
    当命令字节不在协议定义范围内时抛出。
    """
    pass


# ============================================================================
# RS485 驱动相关异常
# ============================================================================

class RS485DriverError(EChemSDLError):
    """RS485 驱动错误基类"""
    pass


class SerialPortError(RS485DriverError):
    """串口错误
    
    当串口打开、读写失败时抛出。
    """
    pass


class DeviceNotFoundError(RS485DriverError):
    """设备未找到
    
    当扫描或通信时设备无响应时抛出。
    """
    pass


class CommunicationTimeoutError(RS485DriverError):
    """通信超时
    
    当等待设备响应超时时抛出。
    """
    pass


class DeviceOfflineError(RS485DriverError):
    """设备离线
    
    当长时间未收到设备响应时抛出。
    """
    pass


# ============================================================================
# 硬件控制相关异常
# ============================================================================

class HardwareError(EChemSDLError):
    """硬件错误基类"""
    pass


class PumpError(HardwareError):
    """泵控制错误"""
    pass


class DiluterError(HardwareError):
    """配液器错误"""
    pass


class FlusherError(HardwareError):
    """冲洗器错误"""
    pass


class CHIError(HardwareError):
    """CHI 电化学仪器错误"""
    pass


# ============================================================================
# 实验引擎相关异常
# ============================================================================

class ExperimentError(EChemSDLError):
    """实验错误基类"""
    pass


class ExperimentStoppedError(ExperimentError):
    """实验被停止"""
    pass


class ExperimentAbortedError(ExperimentError):
    """实验被中止"""
    pass


class InvalidStepError(ExperimentError):
    """无效步骤
    
    当步骤参数不合法时抛出。
    """
    pass


# ============================================================================
# 配置相关异常
# ============================================================================

class ConfigError(EChemSDLError):
    """配置错误基类"""
    pass


class ConfigFileError(ConfigError):
    """配置文件错误
    
    当配置文件读取、解析失败时抛出。
    """
    pass


class InvalidConfigError(ConfigError):
    """无效配置
    
    当配置参数不符合要求时抛出。
    """
    pass


# ============================================================================
# 数据处理相关异常
# ============================================================================

class DataError(EChemSDLError):
    """数据错误基类"""
    pass


class DataExportError(DataError):
    """数据导出错误"""
    pass


class DataValidationError(DataError):
    """数据验证错误"""
    pass
