import numpy as np
from scipy.signal import find_peaks, peak_widths

class SpectrumProcessor:
    def __init__(self):
        self.raw_data = None
        self.wavelengths = None
        
    def set_data(self, wavelengths, intensities):
        """设置光谱数据"""
        self.wavelengths = np.array(wavelengths)
        self.raw_data = np.array(intensities)
        
    def find_peaks_threshold(self, height_threshold=None, distance=None):
        """基于阈值的峰值检测
        
        Args:
            height_threshold: 峰值高度阈值
            distance: 峰值之间的最小距离
            
        Returns:
            peaks_info: 包含峰值信息的字典
        """
        if self.raw_data is None:
            raise ValueError("No data available for peak detection")
            
        peaks, properties = find_peaks(self.raw_data, 
                                      height=height_threshold,
                                      distance=distance)
        
        # 计算半高宽
        widths_result = peak_widths(self.raw_data, peaks, rel_height=0.5)
        
        peaks_info = {
            'peak_indices': peaks,
            'peak_heights': properties['peak_heights'],
            'peak_wavelengths': self.wavelengths[peaks],
            'fwhm': widths_result[0],  # Full Width at Half Maximum
            'fwhm_wavelengths': [
                self.wavelengths[int(left):int(right)] 
                for left, right in zip(widths_result[2], widths_result[3])
            ]
        }
        
        return peaks_info
    
    def calculate_snr(self, signal_range=None, noise_range=None):
        """计算信噪比
        
        Args:
            signal_range: 信号区域的索引范围 (start, end)
            noise_range: 噪声区域的索引范围 (start, end)
            
        Returns:
            float: 信噪比值
        """
        if self.raw_data is None:
            raise ValueError("No data available for SNR calculation")
            
        if signal_range is None:
            # 使用最大值点作为信号
            signal = np.max(self.raw_data)
        else:
            signal = np.mean(self.raw_data[signal_range[0]:signal_range[1]])
            
        if noise_range is None:
            # 使用全谱图标准差作为噪声
            noise = np.std(self.raw_data)
        else:
            noise = np.std(self.raw_data[noise_range[0]:noise_range[1]])
            
        return signal / noise if noise != 0 else float('inf')
    
    def apply_smoothing(self, window_size=5):
        """应用移动平均平滑处理
        
        Args:
            window_size: 平滑窗口大小
        """
        if self.raw_data is None:
            raise ValueError("No data available for smoothing")
            
        kernel = np.ones(window_size) / window_size
        self.raw_data = np.convolve(self.raw_data, kernel, mode='same')
    
    def get_processed_data(self):
        """获取处理后的数据"""
        return {
            'wavelengths': self.wavelengths,
            'intensities': self.raw_data
        }