"""
Unit Tests for RS485 Driver Module

测试 RS485 驱动层的串口通信、线程安全、Mock 模式等功能。
"""

import pytest
import sys
import time
from pathlib import Path
from threading import Thread

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from echem_sdl.hardware.rs485_driver import RS485Driver
from echem_sdl.utils.constants import CMD_ENABLE, CMD_SPEED, CMD_READ_ENCODER


class TestRS485DriverBasics:
    """测试基本功能"""
    
    def test_init_mock_mode(self):
        """测试Mock模式初始化"""
        driver = RS485Driver(mock_mode=True)
        assert driver.mock_mode == True
        assert driver.is_open == False
    
    def test_init_with_params(self):
        """测试带参数初始化"""
        driver = RS485Driver(
            port="COM3",
            baudrate=38400,
            timeout=0.5,
            mock_mode=True
        )
        assert driver.port == "COM3"
        assert driver.baudrate == 38400
        assert driver.timeout == 0.5
    
    def test_list_ports(self):
        """测试列出可用串口"""
        ports = RS485Driver.list_ports()
        assert isinstance(ports, list)


class TestRS485DriverOpenClose:
    """测试打开关闭功能"""
    
    def test_open_close_mock(self):
        """测试Mock模式打开关闭"""
        driver = RS485Driver(mock_mode=True)
        
        # 打开
        assert driver.open() == True
        assert driver.is_open == True
        
        # 关闭
        driver.close()
        assert driver.is_open == False
    
    def test_open_twice(self):
        """测试重复打开"""
        driver = RS485Driver(mock_mode=True)
        assert driver.open() == True
        assert driver.open() == True  # 应该返回成功
        driver.close()
    
    def test_close_without_open(self):
        """测试未打开就关闭"""
        driver = RS485Driver(mock_mode=True)
        driver.close()  # 不应抛出异常
        assert driver.is_open == False
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with RS485Driver(mock_mode=True) as driver:
            assert driver.is_open == True
        assert driver.is_open == False


class TestRS485DriverSendFrame:
    """测试帧发送功能"""
    
    def test_send_frame_basic(self):
        """测试基本帧发送"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        result = driver.send_frame(addr=1, cmd=CMD_ENABLE, data=b'\x01')
        assert result == True
        
        driver.close()
    
    def test_send_frame_without_open(self):
        """测试未打开时发送"""
        driver = RS485Driver(mock_mode=True)
        result = driver.send_frame(addr=1, cmd=CMD_ENABLE)
        assert result == False
    
    def test_send_multiple_frames(self):
        """测试发送多个帧"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        for i in range(5):
            result = driver.send_frame(addr=1, cmd=CMD_SPEED)
            assert result == True
            time.sleep(0.05)
        
        driver.close()


class TestRS485DriverCallback:
    """测试回调功能"""
    
    def test_set_callback(self):
        """测试设置回调"""
        driver = RS485Driver(mock_mode=True)
        
        received = []
        def callback(addr, cmd, payload):
            received.append((addr, cmd, payload))
        
        driver.set_callback(callback)
        driver.open()
        
        # 发送命令并等待响应
        driver.send_frame(addr=1, cmd=CMD_ENABLE, data=b'\x01')
        time.sleep(0.2)
        
        # Mock模式下应该收到响应
        assert len(received) > 0
        
        driver.close()
    
    def test_callback_with_multiple_frames(self):
        """测试多帧回调"""
        driver = RS485Driver(mock_mode=True)
        
        received = []
        def callback(addr, cmd, payload):
            received.append((addr, cmd, payload))
        
        driver.set_callback(callback)
        driver.open()
        
        # 发送多个命令
        for addr in [1, 2, 3]:
            driver.send_frame(addr=addr, cmd=CMD_ENABLE, data=b'\x01')
            time.sleep(0.1)
        
        time.sleep(0.3)
        
        # 应该收到3个响应
        assert len(received) >= 3
        
        driver.close()


class TestRS485DriverDeviceDiscovery:
    """测试设备发现功能"""
    
    def test_discover_devices_mock(self):
        """测试Mock模式设备扫描"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        # Mock模式应该能找到设备
        devices = driver.discover_devices(addresses=[1, 2, 3], timeout_per_addr=0.1)
        assert isinstance(devices, list)
        
        driver.close()
    
    def test_discover_without_open(self):
        """测试未打开时扫描"""
        driver = RS485Driver(mock_mode=True)
        # 应该返回空列表或抛出异常
        devices = driver.discover_devices()
        assert isinstance(devices, list)


class TestRS485DriverMotorControl:
    """测试电机控制功能"""
    
    def test_run_speed(self):
        """测试设置转速"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        result = driver.run_speed(addr=1, rpm=100, forward=True)
        assert result == True
        
        result = driver.run_speed(addr=1, rpm=200, forward=False)
        assert result == True
        
        driver.close()
    
    def test_enable_motor(self):
        """测试使能电机"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        result = driver.enable_motor(addr=1, enable=True)
        assert result == True
        
        result = driver.enable_motor(addr=1, enable=False)
        assert result == True
        
        driver.close()
    
    def test_motor_control_without_open(self):
        """测试未打开时控制电机"""
        driver = RS485Driver(mock_mode=True)
        
        result = driver.run_speed(addr=1, rpm=100)
        assert result == False
        
        result = driver.enable_motor(addr=1, enable=True)
        assert result == False


class TestRS485DriverThreadSafety:
    """测试线程安全"""
    
    def test_concurrent_sends(self):
        """测试并发发送"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        errors = []
        
        def send_task():
            try:
                for _ in range(20):
                    driver.send_frame(addr=1, cmd=CMD_SPEED)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程并发发送
        threads = [Thread(target=send_task) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 不应该有异常
        assert len(errors) == 0
        
        driver.close()
    
    def test_concurrent_open_close(self):
        """测试并发打开关闭"""
        driver = RS485Driver(mock_mode=True)
        
        def toggle_task():
            for _ in range(3):
                driver.open()
                time.sleep(0.05)
                driver.close()
                time.sleep(0.05)
        
        threads = [Thread(target=toggle_task) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 最终应该是关闭状态
        driver.close()
        assert driver.is_open == False


class TestRS485DriverCommunicationStatus:
    """测试通信状态"""
    
    def test_last_comm_time(self):
        """测试最后通信时间"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        initial_time = driver.last_comm_time
        time.sleep(0.1)
        
        driver.send_frame(addr=1, cmd=CMD_ENABLE)
        time.sleep(0.1)
        
        # 发送后应该更新时间
        assert driver.last_comm_time > initial_time
        
        driver.close()


class TestRS485DriverEdgeCases:
    """测试边界情况"""
    
    def test_large_address(self):
        """测试大地址"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        # 地址255是有效的
        result = driver.send_frame(addr=255, cmd=CMD_ENABLE)
        assert result == True
        
        driver.close()
    
    def test_empty_payload(self):
        """测试空载荷"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        result = driver.send_frame(addr=1, cmd=CMD_READ_ENCODER, data=b'')
        assert result == True
        
        driver.close()
    
    def test_long_payload(self):
        """测试长载荷"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        # 发送一个较长的载荷
        long_data = b'\x00' * 50
        result = driver.send_frame(addr=1, cmd=CMD_SPEED, data=long_data)
        assert result == True
        
        driver.close()


class TestRS485DriverCleanup:
    """测试清理功能"""
    
    def test_del_closes_port(self):
        """测试析构函数关闭端口"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        assert driver.is_open == True
        
        # 删除对象应该自动关闭
        del driver
        # 由于Mock模式，这不会有实际的端口资源泄漏
    
    def test_multiple_close_calls(self):
        """测试多次关闭"""
        driver = RS485Driver(mock_mode=True)
        driver.open()
        
        driver.close()
        driver.close()  # 第二次关闭不应抛出异常
        driver.close()  # 第三次也不应该


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
