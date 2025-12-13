## 1. 模块定位与职责
- 文件：`src/echem_sdl/services/kafka_client.py`
- 作用：可选的 Kafka 消息生产/消费，用于实验事件上报（progress/step_start/step_end/error）、云端监控/联动；可完全禁用（配置 `enable=false`）。若未配置或连接失败，自动禁用并进入 mock，不能影响实验流程。
- 要求：生产线程安全；消费可选（独立线程或上层轮询）；禁用/异常不应导致崩溃。

## 2. 文件与类结构
- `class KafkaClient`
  - 初始化参数：
    - `config: dict`
    - `logger: LoggerService | None = None`
    - `enabled: bool = True`（配置缺失自动 False）
    - 可选 `consumer_group: str | None = None`
  - 字段：
    - `producer: KafkaProducer | None`
    - `consumer: KafkaConsumer | None`
    - `topics: dict`（如 {"events": "ec_events", "status": "ec_status"}）
    - `enabled: bool`
    - `mock: bool`
    - `lock: threading.RLock`
    - `running: bool`（消费线程开关）
    - `worker: threading.Thread | None`
  - 方法（含类型注解）：
    - `initialize() -> None`
    - `produce(topic: str, msg: dict | str | bytes) -> None`
    - `start_consumer(callback: Callable[[dict], None]) -> None`
    - `stop_consumer() -> None`
    - `is_enabled() -> bool`
    - 内部：`_consumer_loop() -> None`, `_safe_encode(msg) -> bytes | None`

## 3. 依赖说明
- 外部：`kafka-python` 或 `confluent-kafka`（实现时二选一）
- 内部：`services.logger.LoggerService`，可选 `services.settings_service.SettingsService`/`lib_context`（由上层传入配置）
- 标准库：`json`, `threading`, `typing`, `time`

## 4. 线程与异步策略
- 生产：同步发送，使用 `lock` 保证 producer 线程安全。
- 消费：可选后台线程 `worker` 循环拉取并调用回调；或上层自定轮询。
- `enabled=False` 或 `mock=True`：所有方法直接返回，不做任何操作。
- 禁止阻塞 UI 线程。

## 5. 错误与日志处理机制
- 初始化失败/ broker 不可达：warning，自动禁用。
- 生产失败（断开/序列化失败）：warning；JSON 失败时退化为字符串。
- 消费失败（反序列化异常）：warning；消费线程异常退出：error。
- 发送成功/连接恢复：info。
- Kafka 不得抛出未捕获异常影响实验。

## 6. 测试要求
- 初始化：配置缺失/错误 broker → 自动禁用，不抛异常。
- 生产：支持 dict/str/bytes；多线程 produce 无冲突。
- 消费：mock Kafka 输入触发回调。
- 错误路径：序列化失败/连接断开 → 记录日志不崩溃。
- 禁用模式：enabled=False 时 produce/start_consumer 无操作。

## 7. 文档与注释要求
- 模块 docstring：说明可选功能、禁用机制、线程模型。
- 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解必须；在 consumer loop / producer send 处添加行内注释。

## 8. 验收标准
- Kafka 非核心依赖：连接失败不影响系统运行。
- API 稳定：produce / start_consumer / stop_consumer 可用。
- 线程安全，无死锁。
- 错误处理完备，日志可追踪。
- 测试通过：生产/消费/禁用/并发/异常路径。
- 可被 ExperimentEngine/UI 无感使用。 
