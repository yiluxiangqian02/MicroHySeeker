# 16 - KafkaClient 模块规范

> **文件路径**: `src/echem_sdl/services/kafka_client.py`  
> **优先级**: P3 (可选模块)  
> **依赖**: kafka-python  
> **原C#参考**: 无（新增功能）

---

## 一、模块职责

KafkaClient 是可选的消息队列客户端，负责：
1. 发送实验事件到 Kafka
2. 发送实验数据到 Kafka
3. 订阅远程控制指令
4. 提供离线缓冲

**使用场景**: 与外部系统集成、远程监控、数据流处理

---

## 二、消息格式

### 2.1 事件消息

```json
{
  "type": "experiment_event",
  "event": "step_completed",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "experiment_id": "exp_001",
  "data": {
    "step_index": 2,
    "step_name": "CV测量",
    "duration": 45.5
  }
}
```

### 2.2 数据消息

```json
{
  "type": "echem_data",
  "technique": "CV",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "experiment_id": "exp_001",
  "step_index": 2,
  "points": [
    {"t": 0.0, "e": 0.0, "i": 1.5e-6},
    {"t": 0.1, "e": 0.1, "i": 2.3e-6}
  ]
}
```

### 2.3 指令消息

```json
{
  "type": "command",
  "command": "pause",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "params": {}
}
```

---

## 三、配置

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class KafkaConfig:
    """Kafka 配置"""
    # 服务器地址
    bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    # 客户端 ID
    client_id: str = "echem_sdl"
    # 事件主题
    event_topic: str = "echem_events"
    # 数据主题
    data_topic: str = "echem_data"
    # 指令主题
    command_topic: str = "echem_commands"
    # 消费者组
    consumer_group: str = "echem_sdl_group"
    # 安全协议
    security_protocol: str = "PLAINTEXT"
    # SASL 配置（可选）
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    # 离线缓冲大小
    offline_buffer_size: int = 1000
```

---

## 四、类设计

### 4.1 主类定义

```python
from typing import Callable, Dict, Any, Optional
import json
import threading
from queue import Queue
from datetime import datetime

class KafkaClient:
    """Kafka 消息客户端
    
    提供与 Kafka 的消息交互功能。
    
    Attributes:
        is_connected: 是否已连接
        
    Example:
        >>> client = KafkaClient(config)
        >>> client.connect()
        >>> client.send_event("experiment_started", {"name": "test"})
        >>> client.close()
    """
```

### 4.2 构造函数

```python
def __init__(self, config: KafkaConfig) -> None:
    """初始化 Kafka 客户端
    
    Args:
        config: Kafka 配置
    """
    self._config = config
    self._producer = None
    self._consumer = None
    self._is_connected = False
    self._lock = threading.Lock()
    
    # 离线缓冲队列
    self._offline_buffer: Queue = Queue(maxsize=config.offline_buffer_size)
    
    # 指令回调
    self._command_callbacks: Dict[str, Callable] = {}
    
    # 消费者线程
    self._consumer_thread: Optional[threading.Thread] = None
    self._stop_consumer = threading.Event()
```

### 4.3 连接管理

```python
def connect(self) -> bool:
    """连接到 Kafka
    
    Returns:
        是否成功连接
    """
    try:
        from kafka import KafkaProducer, KafkaConsumer
    except ImportError:
        raise ImportError("需要安装 kafka-python: pip install kafka-python")
    
    try:
        # 创建生产者
        producer_config = {
            "bootstrap_servers": self._config.bootstrap_servers,
            "client_id": self._config.client_id,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
            "security_protocol": self._config.security_protocol,
        }
        
        if self._config.sasl_mechanism:
            producer_config["sasl_mechanism"] = self._config.sasl_mechanism
            producer_config["sasl_plain_username"] = self._config.sasl_username
            producer_config["sasl_plain_password"] = self._config.sasl_password
        
        self._producer = KafkaProducer(**producer_config)
        
        # 创建消费者（如果需要订阅指令）
        if self._command_callbacks:
            self._start_consumer()
        
        self._is_connected = True
        
        # 刷新离线缓冲
        self._flush_offline_buffer()
        
        return True
        
    except Exception as e:
        print(f"Kafka 连接失败: {e}")
        return False

def disconnect(self) -> None:
    """断开连接"""
    self._stop_consumer.set()
    
    if self._consumer_thread:
        self._consumer_thread.join(timeout=5.0)
    
    if self._producer:
        self._producer.close()
        self._producer = None
    
    if self._consumer:
        self._consumer.close()
        self._consumer = None
    
    self._is_connected = False

def close(self) -> None:
    """关闭客户端（disconnect 别名）"""
    self.disconnect()

@property
def is_connected(self) -> bool:
    """是否已连接"""
    return self._is_connected
```

### 4.4 发送消息

```python
def send_event(
    self,
    event_type: str,
    data: Dict[str, Any],
    experiment_id: Optional[str] = None
) -> bool:
    """发送事件消息
    
    Args:
        event_type: 事件类型
        data: 事件数据
        experiment_id: 实验 ID
        
    Returns:
        是否成功发送
    """
    message = {
        "type": "experiment_event",
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "experiment_id": experiment_id,
        "data": data
    }
    
    return self._send(self._config.event_topic, message)

def send_data(
    self,
    technique: str,
    points: list,
    experiment_id: Optional[str] = None,
    step_index: int = 0
) -> bool:
    """发送数据消息
    
    Args:
        technique: 技术类型
        points: 数据点列表 [{"t": ..., "e": ..., "i": ...}]
        experiment_id: 实验 ID
        step_index: 步骤索引
        
    Returns:
        是否成功发送
    """
    message = {
        "type": "echem_data",
        "technique": technique,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "experiment_id": experiment_id,
        "step_index": step_index,
        "points": points
    }
    
    return self._send(self._config.data_topic, message)

def _send(self, topic: str, message: Dict) -> bool:
    """发送消息（内部方法）"""
    with self._lock:
        if not self._is_connected or self._producer is None:
            # 离线缓冲
            if not self._offline_buffer.full():
                self._offline_buffer.put((topic, message))
            return False
        
        try:
            future = self._producer.send(topic, message)
            # 异步发送，不等待
            return True
        except Exception as e:
            print(f"发送消息失败: {e}")
            # 存入离线缓冲
            if not self._offline_buffer.full():
                self._offline_buffer.put((topic, message))
            return False

def _flush_offline_buffer(self) -> None:
    """刷新离线缓冲"""
    while not self._offline_buffer.empty():
        try:
            topic, message = self._offline_buffer.get_nowait()
            self._producer.send(topic, message)
        except Exception:
            break
```

### 4.5 接收指令

```python
def on_command(self, command: str, callback: Callable[[Dict], None]) -> None:
    """注册指令回调
    
    Args:
        command: 指令名称
        callback: 回调函数
    """
    self._command_callbacks[command] = callback
    
    # 如果已连接但消费者未启动，启动消费者
    if self._is_connected and self._consumer is None:
        self._start_consumer()

def _start_consumer(self) -> None:
    """启动消费者线程"""
    from kafka import KafkaConsumer
    
    consumer_config = {
        "bootstrap_servers": self._config.bootstrap_servers,
        "group_id": self._config.consumer_group,
        "value_deserializer": lambda v: json.loads(v.decode("utf-8")),
        "auto_offset_reset": "latest",
        "security_protocol": self._config.security_protocol,
    }
    
    if self._config.sasl_mechanism:
        consumer_config["sasl_mechanism"] = self._config.sasl_mechanism
        consumer_config["sasl_plain_username"] = self._config.sasl_username
        consumer_config["sasl_plain_password"] = self._config.sasl_password
    
    self._consumer = KafkaConsumer(
        self._config.command_topic,
        **consumer_config
    )
    
    self._stop_consumer.clear()
    self._consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
    self._consumer_thread.start()

def _consume_loop(self) -> None:
    """消费者循环"""
    while not self._stop_consumer.is_set():
        try:
            # 轮询消息（超时 1 秒）
            records = self._consumer.poll(timeout_ms=1000)
            
            for topic_partition, messages in records.items():
                for message in messages:
                    self._handle_command(message.value)
                    
        except Exception as e:
            print(f"消费消息错误: {e}")

def _handle_command(self, message: Dict) -> None:
    """处理指令消息"""
    if message.get("type") != "command":
        return
    
    command = message.get("command")
    params = message.get("params", {})
    
    if command in self._command_callbacks:
        try:
            self._command_callbacks[command](params)
        except Exception as e:
            print(f"指令回调错误: {e}")
```

---

## 五、测试要求

### 5.1 单元测试（Mock）

```python
# tests/test_kafka_client.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from echem_sdl.services.kafka_client import KafkaClient, KafkaConfig

class TestKafkaClient:
    @pytest.fixture
    def config(self):
        return KafkaConfig(
            bootstrap_servers=["localhost:9092"],
            event_topic="test_events"
        )
    
    @pytest.fixture
    def client(self, config):
        return KafkaClient(config)
    
    def test_offline_buffer(self, client):
        """测试离线缓冲"""
        # 未连接时发送
        result = client.send_event("test", {"key": "value"})
        
        assert result == False
        assert not client._offline_buffer.empty()
    
    @patch("kafka.KafkaProducer")
    def test_connect(self, mock_producer, client):
        """测试连接"""
        result = client.connect()
        
        assert result == True
        assert client.is_connected
    
    @patch("kafka.KafkaProducer")
    def test_send_event(self, mock_producer, client):
        """测试发送事件"""
        client.connect()
        
        result = client.send_event(
            "experiment_started",
            {"name": "test"},
            experiment_id="exp_001"
        )
        
        assert result == True
    
    def test_command_callback(self, client):
        """测试指令回调注册"""
        callback = Mock()
        client.on_command("pause", callback)
        
        assert "pause" in client._command_callbacks
```

### 5.2 集成测试

```python
# tests/integration/test_kafka_integration.py
# 需要运行 Kafka 实例

import pytest

@pytest.mark.integration
class TestKafkaIntegration:
    def test_send_receive(self):
        """测试发送和接收"""
        # 需要 Kafka 环境
        pass
```

---

## 六、使用示例

### 6.1 基本使用

```python
from echem_sdl.services.kafka_client import KafkaClient, KafkaConfig

# 配置
config = KafkaConfig(
    bootstrap_servers=["kafka.example.com:9092"],
    event_topic="echem_events",
    data_topic="echem_data"
)

# 创建客户端
client = KafkaClient(config)
client.connect()

# 发送事件
client.send_event(
    "experiment_started",
    {"program": "CV扫描", "steps": 5},
    experiment_id="exp_001"
)

# 发送数据
client.send_data(
    technique="CV",
    points=[{"t": 0.0, "e": 0.0, "i": 1e-6}],
    experiment_id="exp_001"
)

# 关闭
client.close()
```

### 6.2 接收指令

```python
def handle_pause(params):
    print("收到暂停指令")
    engine.pause()

def handle_stop(params):
    print("收到停止指令")
    engine.stop()

client.on_command("pause", handle_pause)
client.on_command("stop", handle_stop)
client.connect()
```

---

## 七、验收标准

- [ ] 连接/断开正确
- [ ] 事件发送正确
- [ ] 数据发送正确
- [ ] 离线缓冲正确
- [ ] 指令接收正确
- [ ] 回调触发正确
- [ ] 安全配置支持
- [ ] 线程安全
- [ ] 错误处理健壮
- [ ] 单元测试通过
