## 1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/pump_manager.py`
- 作用：统一管理所有 RS485 总线上的泵类设备（动态 Diluter 列表 + Flusher 三角色泵），提供地址→设备实例映射、动态注册/注销、RS485Driver 帧路由、查询泵列表/按地址取泵、调试接口。
- 特点：泵数量完全由配置驱动（`diluter_pumps` + `flusher_pumps`）；PumpManager 将配置转为实例，避免在 LibContext 内堆叠泵字段；自身不执行业务逻辑，仅负责映射与转发；LibContext 可委派所有泵管理给 PumpManager。

## 2. 文件与类结构
- `class PumpManager`
  - 初始化参数：
    - `driver: RS485Driver`
    - `logger: LoggerService | None = None`
    - 可选：`context: LibContext | None = None`
  - 字段：
    - `driver: RS485Driver`
    - `logger: LoggerService`
    - `diluters: dict[int, Diluter]`（addr → Diluter 实例）
    - `flusher_roles: dict[str, dict]`（配置镜像，如 inlet/outlet/transfer）
    - `flusher_pumps: dict[int, Any]`（若为 flusher 子泵实例）
    - `address_map: dict[int, Any]`（addr → Diluter/Flusher 或其子泵）
    - `lock: threading.RLock`
  - 方法（含类型注解）：
    - `register_diluters(cfg_list: list[dict]) -> None`
    - `register_flusher(flusher_cfg: dict) -> None`（自动注册 inlet/outlet/transfer 三角色地址）
    - `register_device(addr: int, dev: Any) -> None`
    - `unregister_device(addr: int) -> None`
    - `get(addr: int) -> Any | None`
    - `get_all() -> list[Any]`
    - `dispatch_frame(frame: bytes) -> None`（解析地址 → 调用对应设备 `handle_response`）
    - 调试：`list_devices() -> dict`, `summary() -> str`

> 说明：Flusher 主类管理三阶段流程，但每个角色对应独立泵地址，应注册到 `address_map`。若不拆子泵，则映射到 `Flusher.handle_response`，实现时需明确并保持线程安全。

## 3. 依赖说明
- 内部：`hardware.rs485_driver.RS485Driver`, `hardware.diluter.Diluter`, `hardware.flusher.Flusher`（或其子泵类型），`services.logger.LoggerService`, `lib_context.LibContext`（可选注入，避免强耦合）。
- 标准库：`threading`, `typing`, `collections`.

## 4. 线程与异步策略
- 注册/注销/映射更新需持 `lock`。
- `dispatch_frame` 在 RS485Driver 读线程触发，必须线程安全；`handle_response` 由各设备保证自身线程安全。
- PumpManager 不启动线程、不做异步处理，仅做映射与转发。

## 5. 错误与日志处理机制
- 未注册地址：warning，忽略帧。
- 重复地址：error，明确策略（覆盖或拒绝）并记录。
- 配置缺失字段：error，跳过该泵。
- 注册完成：info（注册数量、地址列表）。
- `dispatch_frame` 调用失败：捕获异常，error 日志，不中断 RS485Driver。

## 6. 测试要求
- 注册：加载 6–9 个 diluter 配置正确生成并注册；加载 flusher 配置后三角色地址注册完成。
- 映射：`address_map` 包含所有泵地址且无重复。
- 路由：模拟 RS485 帧按地址调用正确设备的 `handle_response`；未知地址 warning 不抛异常。
- 并发：多线程 register + dispatch 不崩溃，锁生效无脏读。
- 错误路径：缺失地址字段 → error + 跳过；实例化失败 → warning；`handle_response` 抛异常 → 捕获并记录 error。

## 7. 文档与注释要求
- 模块 docstring：说明 PumpManager 职责、与 LibContext/RS485Driver 的协作方式。
- 方法 docstring：参数、返回、异常、线程安全说明。
- 类型注解完整；在 `dispatch_frame` 内添加清晰注释（解析地址→查找→调用）。

## 8. 验收标准
- 支持动态泵数量（6～12 台均可），地址统一路由，无写死数量/地址。
- 映射与转发线程安全，日志完备，错误不影响主流程。
- 可直接被 LibContext 调用作为泵注册中心。
- 测试通过：注册/路由/并发/异常路径。 
