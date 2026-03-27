"""Pump fault/event helpers for UI fault feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FaultEvent:
    level: str
    source: str
    message: str


def describe_pump_fault(fault_code: int) -> str:
    fault_map = {
        0x01: "堵转保护触发",
    }
    return fault_map.get(fault_code, f"未知故障码 0x{fault_code:02X}")


class PumpFaultTracker:
    """Track pump fault/offline transitions and emit deduplicated UI events."""

    def __init__(self) -> None:
        self._fault_by_addr: dict[int, int | None] = {}
        self._online_by_addr: dict[int, bool | None] = {}

    def reset(self) -> None:
        self._fault_by_addr.clear()
        self._online_by_addr.clear()

    def consume_state(self, address: int, state: dict[str, Any] | None) -> list[FaultEvent]:
        if not state:
            return []

        events: list[FaultEvent] = []

        prev_fault = self._fault_by_addr.get(address)
        curr_fault_raw = state.get("fault")
        curr_fault = curr_fault_raw if isinstance(curr_fault_raw, int) else None

        prev_online = self._online_by_addr.get(address)
        curr_online_raw = state.get("online")
        curr_online = bool(curr_online_raw) if curr_online_raw is not None else None

        if curr_online is False and prev_online not in (None, False):
            events.append(
                FaultEvent(
                    level="ERROR",
                    source="RS485",
                    message=f"泵 {address} 通信超时或离线，请检查电源、地址和串口连线。",
                )
            )
        elif curr_online is True and prev_online is False:
            events.append(
                FaultEvent(
                    level="INFO",
                    source="RS485",
                    message=f"泵 {address} 通信已恢复。",
                )
            )

        if curr_fault not in (None, 0) and curr_fault != prev_fault:
            events.append(
                FaultEvent(
                    level="ERROR",
                    source="PUMP",
                    message=f"泵 {address} 检测到故障: {describe_pump_fault(curr_fault)}。",
                )
            )
        elif prev_fault not in (None, 0) and curr_fault in (None, 0):
            events.append(
                FaultEvent(
                    level="INFO",
                    source="PUMP",
                    message=f"泵 {address} 故障已清除，状态恢复正常。",
                )
            )

        self._fault_by_addr[address] = curr_fault
        self._online_by_addr[address] = curr_online
        return events
