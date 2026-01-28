"""Optional Kafka client wrapper with safe-disable behavior."""

from __future__ import annotations

import json
import threading
import time
from typing import Callable

from .logger import LoggerService


class KafkaClient:
    def __init__(
        self,
        config: dict,
        logger: LoggerService | None = None,
        enabled: bool = True,
        consumer_group: str | None = None,
    ) -> None:
        self.config = config or {}
        self._logger = logger
        self.enabled = enabled and bool(self.config)
        self.consumer_group = consumer_group
        self.producer = None
        self.consumer = None
        self.mock = True
        self._lock = threading.RLock()
        self.running = False
        self.worker: threading.Thread | None = None
        self.topics = self.config.get("topics", {})

    def initialize(self) -> None:
        if not self.enabled:
            return
        try:
            from kafka import KafkaProducer, KafkaConsumer  # type: ignore

            self.producer = KafkaProducer(
                bootstrap_servers=self.config.get("bootstrap.servers")
            )
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.config.get("bootstrap.servers")
            )
            self.mock = False
            if self._logger:
                self._logger.info("kafka client initialized")
        except Exception as exc:
            self.enabled = False
            self.mock = True
            if self._logger:
                self._logger.warning("kafka unavailable, disabled")
                self._logger.exception("kafka init error", exc=exc)

    def is_enabled(self) -> bool:
        return self.enabled and not self.mock

    def produce(self, topic: str, msg: dict | str | bytes) -> None:
        if not self.is_enabled() or self.producer is None:
            return
        with self._lock:
            payload = self._safe_encode(msg)
            if payload is None:
                return
            try:
                self.producer.send(topic, payload)
            except Exception as exc:
                if self._logger:
                    self._logger.warning("kafka produce failed")
                    self._logger.exception("kafka produce error", exc=exc)

    def start_consumer(self, callback: Callable[[dict], None]) -> None:
        if not self.is_enabled() or self.consumer is None:
            return
        if self.running:
            return
        self.running = True
        self.worker = threading.Thread(
            target=self._consumer_loop, args=(callback,), daemon=True
        )
        self.worker.start()

    def stop_consumer(self) -> None:
        self.running = False
        if self.worker:
            self.worker.join(timeout=1.0)
            self.worker = None

    def _consumer_loop(self, callback: Callable[[dict], None]) -> None:
        while self.running:
            try:
                for msg in self.consumer.poll(timeout_ms=200).values():
                    for record in msg:
                        try:
                            data = json.loads(record.value.decode("utf-8"))
                        except Exception:
                            data = {"raw": record.value}
                        callback(data)
            except Exception:
                time.sleep(0.2)

    def _safe_encode(self, msg: dict | str | bytes) -> bytes | None:
        if isinstance(msg, bytes):
            return msg
        if isinstance(msg, str):
            return msg.encode("utf-8")
        try:
            return json.dumps(msg, ensure_ascii=True).encode("utf-8")
        except Exception:
            return None
