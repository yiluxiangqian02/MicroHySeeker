"""Hardware driver tests."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware import PumpManager, RS485Driver


def test_syringe_pump():
    """Test syringe pump driver."""
    pump = PumpManager().add_syringe_pump(1)
    assert pump.start()
    assert pump.set_speed(10.0)
    assert pump.move_volume(1.0)
    assert pump.stop()
    print("✓ SyringePumpDriver tests passed")


def test_peristaltic_pump():
    """Test peristaltic pump driver."""
    pump = PumpManager().add_peristaltic_pump(1)
    assert pump.start()
    assert pump.set_speed(100.0)
    assert pump.set_direction("forward")
    assert pump.move_volume(5.0)
    assert pump.stop()
    print("✓ RS485PeristalticDriver tests passed")


def test_rs485_driver():
    """Test RS485 driver."""
    rs485 = RS485Driver(use_mock=True)
    assert rs485.connect()
    assert rs485.send(b'\x01\x03\x00\x00\x00\x0A')
    response = rs485.read()
    assert response is not None
    devices = rs485.scan_devices()
    assert len(devices) > 0
    assert rs485.disconnect()
    print("✓ RS485Driver tests passed")


if __name__ == "__main__":
    test_syringe_pump()
    test_peristaltic_pump()
    test_rs485_driver()
    print("\n✓ All hardware tests passed!")
