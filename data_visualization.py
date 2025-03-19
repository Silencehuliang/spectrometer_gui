"""数据可视化模块

提供光谱数据的实时显示和历史数据回放功能。
包含曲线绘制、数据标注和交互控制等功能。
"""

from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtGui import QPen, QColor
from pyqtgraph import PlotWidget, mkPen
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PlotConfig:
    """绘图配置数据类"""
    title: str
    x_label: str
    y_label: str
    x_range: tuple
    y_range: Optional[tuple] = None
    grid: bool = True
    auto_range: bool = True

class SpectrumPlot(QWidget):
    """光谱数据绘图组件

    提供实时光谱数据显示和交互功能。
    """
    def __init__(self, config: PlotConfig):
        super().__init__()
        self._init_ui(config)
        self._setup_plot(config)
        self._setup_controls()

    def _init_ui(self, config: PlotConfig):
        layout = QVBoxLayout()
        
        # 绘图区域
        self.plot_widget = PlotWidget(title=config.title)
        layout.addWidget(self.plot_widget)
        
        # 控制区域
        controls = QHBoxLayout()
        self.auto_range_btn = QPushButton("自动范围")
        self.clear_btn = QPushButton("清除数据")
        self.peak_label = QLabel("峰值: --")
        controls.addWidget(self.auto_range_btn)
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.peak_label)
        layout.addLayout(controls)
        
        self.setLayout(layout)

    def _setup_plot(self, config: PlotConfig):
        # 设置坐标轴
        self.plot_widget.setLabel('left', config.y_label)
        self.plot_widget.setLabel('bottom', config.x_label)
        
        # 设置网格
        self.plot_widget.showGrid(x=config.grid, y=config.grid)
        
        # 创建数据曲线
        self.data_curve = self.plot_widget.plot(
            pen=mkPen(color='g', width=2)
        )
        self.peak_scatter = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolPen=mkPen(color='r', width=2),
            symbolBrush='r'
        )
        
        # 设置范围
        if config.x_range:
            self.plot_widget.setXRange(*config.x_range)
        if config.y_range:
            self.plot_widget.setYRange(*config.y_range)

    def _setup_controls(self):
        self.auto_range_btn.clicked.connect(self.plot_widget.autoRange)
        self.clear_btn.clicked.connect(self.clear_data)

    def update_data(self, x: np.ndarray, y: np.ndarray):
        """更新显示数据

        Args:
            x: X轴数据
            y: Y轴数据
        """
        self.data_curve.setData(x, y)

    def mark_peaks(self, peak_x: List[float], peak_y: List[float]):
        """标记峰值点

        Args:
            peak_x: 峰值X坐标列表
            peak_y: 峰值Y坐标列表
        """
        self.peak_scatter.setData(peak_x, peak_y)
        if peak_x:
            max_peak_idx = np.argmax(peak_y)
            self.peak_label.setText(
                f"峰值: {peak_x[max_peak_idx]:.1f}nm, {peak_y[max_peak_idx]:.1f}"
            )

    def clear_data(self):
        """清除显示数据"""
        self.data_curve.clear()
        self.peak_scatter.clear()
        self.peak_label.setText("峰值: --")

class DataPlayback(QObject):
    """数据回放控制器

    提供历史数据的回放和控制功能。
    """
    playback_frame = Signal(object)  # 发送回放帧数据
    playback_finished = Signal()    # 回放结束信号

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._next_frame)
        self._current_frame = 0
        self._frames = []
        self._interval = 100  # 回放间隔(ms)

    def load_data(self, data_frames: List):
        """加载回放数据

        Args:
            data_frames: 数据帧列表
        """
        self._frames = data_frames
        self._current_frame = 0

    def start(self, interval: Optional[int] = None):
        """开始回放

        Args:
            interval: 回放间隔(ms)
        """
        if interval is not None:
            self._interval = interval
        if self._frames:
            self._timer.start(self._interval)

    def pause(self):
        """暂停回放"""
        self._timer.stop()

    def stop(self):
        """停止回放"""
        self._timer.stop()
        self._current_frame = 0

    def _next_frame(self):
        """发送下一帧数据"""
        if self._current_frame < len(self._frames):
            self.playback_frame.emit(self._frames[self._current_frame])
            self._current_frame += 1
        else:
            self._timer.stop()
            self.playback_finished.emit()