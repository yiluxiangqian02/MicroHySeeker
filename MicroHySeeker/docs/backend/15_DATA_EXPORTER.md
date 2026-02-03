# 15 - DataExporter 模块规范

> **文件路径**: `src/echem_sdl/services/data_exporter.py`  
> **优先级**: P2 (增强模块)  
> **依赖**: 无  
> **原C#参考**: 部分功能在 `Experiment.cs`

---

## 一、模块职责

DataExporter 是数据导出服务，负责：
1. 导出电化学数据到 CSV 格式
2. 导出电化学数据到 Excel 格式
3. 导出实验程序配置
4. 批量导出多个实验数据
5. 生成数据报告

---

## 二、数据结构

### 2.1 电化学数据

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class ECDataPoint:
    """电化学数据点"""
    time: float      # 时间 (s)
    potential: float # 电位 (V)
    current: float   # 电流 (A)

@dataclass
class ECDataSet:
    """电化学数据集"""
    name: str
    technique: str  # CV, LSV, i-t, OCPT
    timestamp: datetime
    points: List[ECDataPoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def times(self) -> List[float]:
        return [p.time for p in self.points]
    
    @property
    def potentials(self) -> List[float]:
        return [p.potential for p in self.points]
    
    @property
    def currents(self) -> List[float]:
        return [p.current for p in self.points]
```

### 2.2 实验结果

```python
@dataclass
class ExperimentResult:
    """实验结果"""
    experiment_name: str
    program_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    combo_index: int = 0
    combo_params: Dict[str, Any] = field(default_factory=dict)
    data_sets: List[ECDataSet] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
```

---

## 三、类设计

### 3.1 主类定义

```python
from pathlib import Path
from typing import Union
import csv

class DataExporter:
    """数据导出服务
    
    提供多格式数据导出功能。
    
    Example:
        >>> exporter = DataExporter()
        >>> exporter.export_csv(data_set, "output.csv")
        >>> exporter.export_excel(result, "report.xlsx")
    """
```

### 3.2 构造函数

```python
def __init__(
    self,
    default_dir: Optional[str | Path] = None,
    decimal_places: int = 6
) -> None:
    """初始化导出服务
    
    Args:
        default_dir: 默认输出目录
        decimal_places: 小数位数
    """
    self._default_dir = Path(default_dir) if default_dir else Path("data")
    self._decimal_places = decimal_places
    
    # 确保目录存在
    self._default_dir.mkdir(parents=True, exist_ok=True)
```

### 3.3 CSV 导出

```python
def export_csv(
    self,
    data_set: ECDataSet,
    file_path: Optional[str | Path] = None,
    include_header: bool = True,
    include_metadata: bool = True
) -> Path:
    """导出数据集到 CSV
    
    Args:
        data_set: 数据集
        file_path: 输出路径（None 则自动生成）
        include_header: 是否包含列标题
        include_metadata: 是否包含元数据
        
    Returns:
        输出文件路径
    """
    if file_path is None:
        timestamp = data_set.timestamp.strftime("%Y%m%d_%H%M%S")
        file_path = self._default_dir / f"{data_set.name}_{timestamp}.csv"
    else:
        file_path = Path(file_path)
    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # 元数据
        if include_metadata:
            writer.writerow(["# Name", data_set.name])
            writer.writerow(["# Technique", data_set.technique])
            writer.writerow(["# Timestamp", data_set.timestamp.isoformat()])
            for key, value in data_set.metadata.items():
                writer.writerow([f"# {key}", value])
            writer.writerow([])
        
        # 列标题
        if include_header:
            writer.writerow(["Time (s)", "Potential (V)", "Current (A)"])
        
        # 数据
        fmt = f"%.{self._decimal_places}f"
        for point in data_set.points:
            writer.writerow([
                fmt % point.time,
                fmt % point.potential,
                fmt % point.current
            ])
    
    return file_path

def export_multi_csv(
    self,
    data_sets: List[ECDataSet],
    output_dir: Optional[str | Path] = None
) -> List[Path]:
    """批量导出多个数据集
    
    Args:
        data_sets: 数据集列表
        output_dir: 输出目录
        
    Returns:
        输出文件路径列表
    """
    output_dir = Path(output_dir) if output_dir else self._default_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    paths = []
    for data_set in data_sets:
        path = self.export_csv(data_set, output_dir / f"{data_set.name}.csv")
        paths.append(path)
    
    return paths
```

### 3.4 Excel 导出

```python
def export_excel(
    self,
    result: ExperimentResult,
    file_path: Optional[str | Path] = None,
    include_chart: bool = True
) -> Path:
    """导出实验结果到 Excel
    
    Args:
        result: 实验结果
        file_path: 输出路径
        include_chart: 是否包含图表
        
    Returns:
        输出文件路径
        
    Note:
        需要安装 openpyxl 库
    """
    try:
        import openpyxl
        from openpyxl.chart import ScatterChart, Reference, Series
    except ImportError:
        raise ImportError("需要安装 openpyxl: pip install openpyxl")
    
    if file_path is None:
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        file_path = self._default_dir / f"{result.experiment_name}_{timestamp}.xlsx"
    else:
        file_path = Path(file_path)
    
    wb = openpyxl.Workbook()
    
    # 概览页
    ws_overview = wb.active
    ws_overview.title = "Overview"
    self._write_overview(ws_overview, result)
    
    # 每个数据集一个工作表
    for i, data_set in enumerate(result.data_sets):
        ws = wb.create_sheet(title=f"Data_{i+1}")
        self._write_data_sheet(ws, data_set)
        
        if include_chart:
            self._add_chart(ws, data_set, len(data_set.points))
    
    wb.save(file_path)
    return file_path

def _write_overview(self, ws, result: ExperimentResult) -> None:
    """写入概览页"""
    rows = [
        ["实验名称", result.experiment_name],
        ["程序名称", result.program_name],
        ["开始时间", result.start_time.isoformat()],
        ["结束时间", result.end_time.isoformat() if result.end_time else ""],
        ["持续时间", f"{result.duration:.1f} 秒"],
        ["组合索引", result.combo_index],
        [],
        ["组合参数:"],
    ]
    
    for key, value in result.combo_params.items():
        rows.append([f"  {key}", value])
    
    rows.extend([
        [],
        ["数据集数量", len(result.data_sets)],
    ])
    
    for i, row in enumerate(rows, 1):
        for j, value in enumerate(row, 1):
            ws.cell(row=i, column=j, value=value)

def _write_data_sheet(self, ws, data_set: ECDataSet) -> None:
    """写入数据工作表"""
    # 元数据
    ws.cell(row=1, column=1, value="名称")
    ws.cell(row=1, column=2, value=data_set.name)
    ws.cell(row=2, column=1, value="技术")
    ws.cell(row=2, column=2, value=data_set.technique)
    
    # 数据标题
    ws.cell(row=4, column=1, value="Time (s)")
    ws.cell(row=4, column=2, value="Potential (V)")
    ws.cell(row=4, column=3, value="Current (A)")
    
    # 数据
    for i, point in enumerate(data_set.points, 5):
        ws.cell(row=i, column=1, value=point.time)
        ws.cell(row=i, column=2, value=point.potential)
        ws.cell(row=i, column=3, value=point.current)

def _add_chart(self, ws, data_set: ECDataSet, point_count: int) -> None:
    """添加图表"""
    from openpyxl.chart import ScatterChart, Reference, Series
    
    chart = ScatterChart()
    chart.title = data_set.name
    chart.style = 13
    
    if data_set.technique in ["CV", "LSV"]:
        # E vs I
        chart.x_axis.title = "Potential (V)"
        chart.y_axis.title = "Current (A)"
        x_values = Reference(ws, min_col=2, min_row=5, max_row=4 + point_count)
        y_values = Reference(ws, min_col=3, min_row=5, max_row=4 + point_count)
    else:
        # t vs I
        chart.x_axis.title = "Time (s)"
        chart.y_axis.title = "Current (A)"
        x_values = Reference(ws, min_col=1, min_row=5, max_row=4 + point_count)
        y_values = Reference(ws, min_col=3, min_row=5, max_row=4 + point_count)
    
    series = Series(y_values, x_values, title="Data")
    chart.series.append(series)
    
    ws.add_chart(chart, "E4")
```

### 3.5 程序配置导出

```python
def export_program(
    self,
    program: "ExpProgram",
    file_path: Optional[str | Path] = None
) -> Path:
    """导出实验程序配置
    
    Args:
        program: 实验程序
        file_path: 输出路径
        
    Returns:
        输出文件路径
    """
    if file_path is None:
        file_path = self._default_dir / f"{program.name}.json"
    else:
        file_path = Path(file_path)
    
    program.save(file_path)
    return file_path
```

### 3.6 报告生成

```python
def generate_report(
    self,
    result: ExperimentResult,
    file_path: Optional[str | Path] = None,
    format: str = "html"
) -> Path:
    """生成实验报告
    
    Args:
        result: 实验结果
        file_path: 输出路径
        format: 报告格式 ("html", "md")
        
    Returns:
        输出文件路径
    """
    if file_path is None:
        ext = "html" if format == "html" else "md"
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        file_path = self._default_dir / f"report_{timestamp}.{ext}"
    else:
        file_path = Path(file_path)
    
    if format == "html":
        content = self._generate_html_report(result)
    else:
        content = self._generate_md_report(result)
    
    file_path.write_text(content, encoding="utf-8")
    return file_path

def _generate_md_report(self, result: ExperimentResult) -> str:
    """生成 Markdown 报告"""
    lines = [
        f"# 实验报告: {result.experiment_name}",
        "",
        "## 基本信息",
        "",
        f"- **程序名称**: {result.program_name}",
        f"- **开始时间**: {result.start_time.isoformat()}",
        f"- **结束时间**: {result.end_time.isoformat() if result.end_time else 'N/A'}",
        f"- **持续时间**: {result.duration:.1f} 秒",
        "",
    ]
    
    if result.combo_params:
        lines.append("## 组合参数")
        lines.append("")
        for key, value in result.combo_params.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    
    lines.append("## 数据集")
    lines.append("")
    for i, data_set in enumerate(result.data_sets, 1):
        lines.append(f"### {i}. {data_set.name}")
        lines.append(f"- 技术: {data_set.technique}")
        lines.append(f"- 数据点数: {len(data_set.points)}")
        lines.append("")
    
    return "\n".join(lines)
```

---

## 四、测试要求

### 4.1 单元测试

```python
# tests/test_data_exporter.py

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from echem_sdl.services.data_exporter import (
    DataExporter, ECDataSet, ECDataPoint, ExperimentResult
)

class TestDataExporter:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)
    
    @pytest.fixture
    def sample_data_set(self):
        return ECDataSet(
            name="CV_test",
            technique="CV",
            timestamp=datetime.now(),
            points=[
                ECDataPoint(0.0, 0.0, 1e-6),
                ECDataPoint(0.1, 0.1, 2e-6),
                ECDataPoint(0.2, 0.2, 3e-6),
            ],
            metadata={"scan_rate": 0.1}
        )
    
    @pytest.fixture
    def exporter(self, temp_dir):
        return DataExporter(temp_dir)
    
    def test_export_csv(self, exporter, sample_data_set):
        """测试 CSV 导出"""
        path = exporter.export_csv(sample_data_set)
        
        assert path.exists()
        content = path.read_text()
        assert "Time (s)" in content
        assert "CV_test" in content
    
    def test_export_csv_no_metadata(self, exporter, sample_data_set):
        """测试无元数据导出"""
        path = exporter.export_csv(sample_data_set, include_metadata=False)
        
        content = path.read_text()
        assert "# Name" not in content
    
    def test_export_multi_csv(self, exporter, sample_data_set):
        """测试批量导出"""
        data_sets = [sample_data_set, sample_data_set]
        paths = exporter.export_multi_csv(data_sets)
        
        assert len(paths) == 2
        for path in paths:
            assert path.exists()

class TestExcelExport:
    @pytest.fixture
    def sample_result(self, sample_data_set):
        return ExperimentResult(
            experiment_name="Test Experiment",
            program_name="Test Program",
            start_time=datetime.now(),
            data_sets=[sample_data_set]
        )
    
    def test_export_excel(self, exporter, sample_result):
        """测试 Excel 导出"""
        path = exporter.export_excel(sample_result)
        
        assert path.exists()
        assert path.suffix == ".xlsx"

class TestReportGeneration:
    def test_generate_md_report(self, exporter, sample_result):
        """测试 Markdown 报告"""
        path = exporter.generate_report(sample_result, format="md")
        
        assert path.exists()
        content = path.read_text()
        assert "# 实验报告" in content
```

---

## 五、验收标准

- [ ] CSV 导出正确（含元数据）
- [ ] CSV 批量导出正确
- [ ] Excel 导出正确
- [ ] Excel 图表正确
- [ ] 程序配置导出正确
- [ ] Markdown 报告正确
- [ ] HTML 报告正确
- [ ] 路径自动生成正确
- [ ] 小数精度可配置
- [ ] 单元测试通过
