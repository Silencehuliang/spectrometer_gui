"""数据采集和处理模块

提供光谱数据采集、处理和分析功能，包括波长扫描、峰值检测等。
"""

from PySide6.QtCore import QObject, Signal
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ScanMode(Enum):
    """扫描模式枚举"""
    SINGLE = 'single'  # 单次扫描
    REPEAT = 'repeat'  # 重复扫描
    AUTO = 'auto'      # 自动扫描

@dataclass
class ScanConfig:
    """扫描配置数据类"""
    start_wavelength: float
    end_wavelength: float
    step_size: float
    mode: ScanMode
    repeat_count: int = 1  # 重复次数，仅在REPEAT模式下有效
    interval: float = 1.0  # 扫描间隔(秒)，仅在AUTO模式下有效

@dataclass
class SpectrumData:
    """光谱数据结构"""
    wavelengths: List[float]
    intensities: List[float]
    timestamp: float

@dataclass
class PeakData:
    """峰值数据结构"""
    wavelength: float
    intensity: float
    fwhm: float  # 半高宽

class DataAcquisition(QObject):
    """数据采集管理器

    处理光谱数据采集、分析和存储。
    """
    scan_progress = Signal(float)  # 扫描进度信号 0.0-1.0
    scan_completed = Signal(object)  # 扫描完成信号，携带SpectrumData
    peak_detected = Signal(object)  # 峰值检测信号，携带PeakData
    error_occurred = Signal(str)  # 错误信号
    state_changed = Signal(str)  # 状态变化信号

    def __init__(self, communicator):
        super().__init__()
        self._communicator = communicator
        self._current_scan = None
        self._scan_data = []
        self._is_scanning = False
        self._scan_state = 'idle'
        self._repeat_count = 0
        self._auto_timer = None

    def start_scan(self, config: ScanConfig):
        """启动波长扫描

        Args:
            config: 扫描配置参数
        """
        if self._is_scanning:
            return

        self._is_scanning = True
        self._current_scan = config
        self._scan_data.clear()
        self._scan_state = 'scanning'
        self._repeat_count = 0

        if config.mode == ScanMode.AUTO:
            self._start_auto_scan()
        elif config.mode == ScanMode.REPEAT:
            self._start_repeat_scan()
        else:
            self._execute_single_scan()

    def _execute_single_scan(self):
        """执行单次扫描"""
        if not self._current_scan:
            return

        # 计算扫描点数
        num_points = int((self._current_scan.end_wavelength - self._current_scan.start_wavelength) 
                        / self._current_scan.step_size) + 1
        wavelengths = np.linspace(self._current_scan.start_wavelength, 
                                self._current_scan.end_wavelength, num_points)

        # 开始扫描
        for i, wl in enumerate(wavelengths):
            if not self._is_scanning:
                break

            # 设置波长并读取强度
            self._communicator.send_command('set_wavelength', value=wl)
            self._communicator.send_command('read_intensity')

            # 更新进度
            progress = (i + 1) / num_points
            self.scan_progress.emit(progress)

        if self._is_scanning:
            self._handle_scan_complete()

    def _start_repeat_scan(self):
        """启动重复扫描模式"""
        if self._repeat_count < self._current_scan.repeat_count:
            self._repeat_count += 1
            self._execute_single_scan()
            if self._is_scanning:
                self._start_repeat_scan()

    def _start_auto_scan(self):
        """启动自动扫描模式"""
        from PySide6.QtCore import QTimer
        if not self._auto_timer:
            self._auto_timer = QTimer(self)
            self._auto_timer.timeout.connect(self._execute_single_scan)
        self._auto_timer.start(int(self._current_scan.interval * 1000))

    def _handle_scan_complete(self):
        """处理扫描完成事件"""
        if self._current_scan.mode == ScanMode.SINGLE:
            self.stop_scan()
        elif self._current_scan.mode == ScanMode.REPEAT:
            if self._repeat_count >= self._current_scan.repeat_count:
                self.stop_scan()
        # AUTO模式下继续扫描直到手动停止

    def stop_scan(self):
        """停止当前扫描"""
        self._is_scanning = False

    def detect_peaks(self, spectrum: SpectrumData, threshold: float = 0.1) -> List[PeakData]:
        """检测光谱数据中的峰值

        Args:
            spectrum: 光谱数据
            threshold: 峰值检测阈值（相对最大值的比例）

        Returns:
            检测到的峰值列表
        """
        intensities = np.array(spectrum.intensities)
        wavelengths = np.array(spectrum.wavelengths)

        # 寻找局部最大值
        peak_indices = []
        for i in range(1, len(intensities)-1):
            if (intensities[i] > intensities[i-1] and 
                intensities[i] > intensities[i+1] and
                intensities[i] > threshold * np.max(intensities)):
                peak_indices.append(i)

        # 计算峰值参数
        peaks = []
        for idx in peak_indices:
            # 计算半高宽
            half_max = intensities[idx] / 2
            left_idx = right_idx = idx
            
            while left_idx > 0 and intensities[left_idx] > half_max:
                left_idx -= 1
            while right_idx < len(intensities)-1 and intensities[right_idx] > half_max:
                right_idx += 1

            fwhm = wavelengths[right_idx] - wavelengths[left_idx]
            
            peak = PeakData(
                wavelength=wavelengths[idx],
                intensity=intensities[idx],
                fwhm=fwhm
            )
            peaks.append(peak)
            self.peak_detected.emit(peak)

        return peaks

    def _handle_scan_data(self, data: dict):
        """处理扫描数据回调

        Args:
            data: 设备返回的数据字典
        """
        if 'intensity' in data:
            self._scan_data.append(data['intensity'])

            # 检查是否完成一次扫描
            if len(self._scan_data) == len(self._current_scan.wavelengths):
                spectrum = SpectrumData(
                    wavelengths=self._current_scan.wavelengths,
                    intensities=self._scan_data,
                    timestamp=time.time()
                )
                self.scan_completed.emit(spectrum)
                self._scan_data.clear()

                # 处理不同扫描模式
                if self._current_scan.mode == ScanMode.SINGLE:
                    self._is_scanning = False
                elif self._current_scan.mode == ScanMode.REPEAT:
                    if len(self._completed_scans) >= self._current_scan.repeat_count:
                        self._is_scanning = False
                # AUTO模式下继续扫描，直到手动停止