from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QSpinBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPen, QColor
from pyqtgraph import PlotWidget
from spectrometer_gui.communication import SerialCommunicator, TcpCommunicator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AE8600光谱仪测试平台")
        self._init_ui()
        self._init_communication()

    def _init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout()
        
        # 连接控制区域
        conn_group = QGroupBox("连接设置")
        conn_layout = QFormLayout()
        
        # 接口类型选择
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["串口", "TCP"])
        conn_layout.addRow("接口类型", self.interface_combo)
        
        # 串口连接参数
        self.serial_widget = QWidget()
        serial_layout = QFormLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItems([f"COM{i}" for i in range(1, 11)])
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "115200", "57600"])
        serial_layout.addRow("串口", self.port_combo)
        serial_layout.addRow("波特率", self.baudrate_combo)
        self.serial_widget.setLayout(serial_layout)
        
        # TCP连接参数
        self.tcp_widget = QWidget()
        tcp_layout = QFormLayout()
        self.ip_input = QLineEdit("127.0.0.1")
        self.port_input = QLineEdit("8000")
        tcp_layout.addRow("IP地址", self.ip_input)
        tcp_layout.addRow("端口", self.port_input)
        self.tcp_widget.setLayout(tcp_layout)
        
        # 默认显示串口设置
        conn_layout.addRow(self.serial_widget)
        self.tcp_widget.hide()
        conn_layout.addRow(self.tcp_widget)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        conn_layout.addRow(self.connect_btn)
        conn_group.setLayout(conn_layout)
        
        # 连接接口类型切换信号
        self.interface_combo.currentTextChanged.connect(self._on_interface_changed)

        # 控制指令区域
        control_tabs = QTabWidget()
        
        # 基础控制选项卡
        basic_control_tab = QWidget()
        basic_layout = QFormLayout()
        
        # 波长设置
        self.wl_input = QSpinBox()
        self.wl_input.setRange(200, 1000)
        self.wl_value_label = QLabel("--")
        self.set_wl_btn = QPushButton("设置波长")
        self.read_wl_btn = QPushButton("读取波长")
        basic_layout.addRow("目标波长(nm)", self.wl_input)
        basic_layout.addRow("当前波长(nm)", self.wl_value_label)
        basic_layout.addRow(self.set_wl_btn)
        basic_layout.addRow(self.read_wl_btn)
        
        # 积分时间设置
        self.int_input = QSpinBox()
        self.int_input.setRange(1, 65535)
        self.int_value_label = QLabel("--")
        self.set_int_btn = QPushButton("设置积分时间")
        self.read_int_btn = QPushButton("读取积分时间")
        basic_layout.addRow("积分时间(ms)", self.int_input)
        basic_layout.addRow("当前积分时间(ms)", self.int_value_label)
        basic_layout.addRow(self.set_int_btn)
        basic_layout.addRow(self.read_int_btn)
        basic_control_tab.setLayout(basic_layout)
        
        # 数据采集选项卡
        acquisition_tab = QWidget()
        acq_layout = QFormLayout()
        
        # 单次采集设置
        self.avg_input = QSpinBox()
        self.avg_input.setRange(1, 100)
        self.avg_value_label = QLabel("--")
        self.set_avg_btn = QPushButton("设置平均次数")
        self.read_avg_btn = QPushButton("读取平均次数")
        self.start_acq_btn = QPushButton("开始采集")
        acq_layout.addRow("平均次数", self.avg_input)
        acq_layout.addRow("当前平均次数", self.avg_value_label)
        acq_layout.addRow(self.set_avg_btn)
        acq_layout.addRow(self.read_avg_btn)
        acq_layout.addRow(self.start_acq_btn)
        
        # 扫描设置
        self.start_wl_input = QSpinBox()
        self.start_wl_input.setRange(200, 1000)
        self.end_wl_input = QSpinBox()
        self.end_wl_input.setRange(200, 1000)
        self.step_wl_input = QSpinBox()
        self.step_wl_input.setRange(1, 100)
        self.scan_mode_combo = QComboBox()
        self.scan_mode_combo.addItems(["单次扫描", "重复扫描", "自动扫描"])
        self.scan_status_label = QLabel("--")
        self.start_scan_btn = QPushButton("开始扫描")
        self.stop_scan_btn = QPushButton("停止扫描")
        self.stop_scan_btn.setEnabled(False)
        acq_layout.addRow("扫描模式", self.scan_mode_combo)
        acq_layout.addRow("起始波长(nm)", self.start_wl_input)
        acq_layout.addRow("终止波长(nm)", self.end_wl_input)
        acq_layout.addRow("步进值(nm)", self.step_wl_input)
        acq_layout.addRow("扫描状态", self.scan_status_label)
        acq_layout.addRow(self.start_scan_btn)
        acq_layout.addRow(self.stop_scan_btn)
        acquisition_tab.setLayout(acq_layout)
        
        # 校准管理选项卡
        calibration_tab = QWidget()
        cal_layout = QFormLayout()
        
        # 基础校准
        self.cal_mode_combo = QComboBox()
        self.cal_mode_combo.addItems(["DARK", "REF"])
        self.start_cal_btn = QPushButton("开始校准")
        cal_layout.addRow("校准模式", self.cal_mode_combo)
        cal_layout.addRow(self.start_cal_btn)
        
        # 高级校准
        self.temp_comp_check = QCheckBox("温度补偿")
        self.nonlinear_corr_check = QCheckBox("非线性校正")
        self.advanced_cal_btn = QPushButton("执行高级校准")
        cal_layout.addRow(self.temp_comp_check)
        cal_layout.addRow(self.nonlinear_corr_check)
        cal_layout.addRow(self.advanced_cal_btn)
        calibration_tab.setLayout(cal_layout)
        
        # 系统监控选项卡
        monitor_tab = QWidget()
        monitor_layout = QFormLayout()
        
        # 状态监控
        self.device_status_label = QLabel("--")
        self.firmware_version_label = QLabel("--")
        self.query_status_btn = QPushButton("查询状态")
        self.query_version_btn = QPushButton("查询版本")
        self.error_log_text = QTextEdit()
        self.error_log_text.setReadOnly(True)
        monitor_layout.addRow("设备状态", self.device_status_label)
        monitor_layout.addRow("固件版本", self.firmware_version_label)
        monitor_layout.addRow(self.query_status_btn)
        monitor_layout.addRow(self.query_version_btn)
        monitor_layout.addRow("错误日志", self.error_log_text)
        monitor_tab.setLayout(monitor_layout)
        
        control_tabs.addTab(basic_control_tab, "基础控制")
        control_tabs.addTab(acquisition_tab, "数据采集")
        control_tabs.addTab(calibration_tab, "校准管理")
        control_tabs.addTab(monitor_tab, "系统监控")
        
        # 波长设置
        wavelength_tab = QWidget()
        wl_layout = QFormLayout()
        self.wl_input = QSpinBox()
        self.wl_input.setRange(200, 1000)
        self.set_wl_btn = QPushButton("设置波长")
        wl_layout.addRow("目标波长(nm)", self.wl_input)
        wl_layout.addRow(self.set_wl_btn)
        wavelength_tab.setLayout(wl_layout)

        # 光谱显示区域
        self.plot_widget = PlotWidget(title="光谱数据")
        self.plot_curve = self.plot_widget.plot(pen=QPen(QColor(0, 255, 0), 2))

        # 状态显示
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(conn_group)
        layout.addWidget(control_tabs)
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.status_label)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # 连接信号
        self.connect_btn.clicked.connect(self._handle_connect)
        self.set_wl_btn.clicked.connect(self._set_wavelength)
        self.read_wl_btn.clicked.connect(self._read_wavelength)
        self.set_int_btn.clicked.connect(self._set_integration)
        self.read_int_btn.clicked.connect(self._read_integration)
        self.set_avg_btn.clicked.connect(self._set_average)
        self.read_avg_btn.clicked.connect(self._read_average)
        self.start_cal_btn.clicked.connect(self._start_calibration)
        self.start_acq_btn.clicked.connect(self._start_acquisition)
        self.query_status_btn.clicked.connect(self._query_status)
        self.query_version_btn.clicked.connect(self._query_version)
        self.start_scan_btn.clicked.connect(self._start_scan)
        self.stop_scan_btn.clicked.connect(self._stop_scan)

    def _init_communication(self):
        self.communicator = None

    @Slot(str)
    def _on_interface_changed(self, interface_type):
        if interface_type == "串口":
            self.serial_widget.show()
            self.tcp_widget.hide()
        else:
            self.serial_widget.hide()
            self.tcp_widget.show()

    @Slot()
    def _handle_connect(self):
        if not self.communicator:
            if self.interface_combo.currentText() == "串口":
                self.communicator = SerialCommunicator()
                self.communicator.connect(port=self.port_combo.currentText(),
                                        baudrate=int(self.baudrate_combo.currentText()))
            else:
                self.communicator = TcpCommunicator()
                self.communicator.connect(host=self.ip_input.text(),
                                        port=int(self.port_input.text()))
            
            self.communicator.data_received.connect(self._handle_response)
            self.communicator.connection_changed.connect(self._handle_connection_change)
            self.connect_btn.setText("断开连接")
        else:
            self.communicator.disconnect()
            self.communicator = None
            self.connect_btn.setText("连接")

    @Slot()
    def _set_wavelength(self):
        if self.communicator:
            self.communicator.send_command('set_wavelength', value=self.wl_input.value())

    @Slot()
    def _read_wavelength(self):
        if self.communicator:
            self.communicator.send_command('read_wavelength')

    @Slot()
    def _set_integration(self):
        if self.communicator:
            self.communicator.send_command('set_integration', value=self.int_input.value())

    @Slot()
    def _read_integration(self):
        if self.communicator:
            self.communicator.send_command('read_integration')

    @Slot()
    def _set_average(self):
        if self.communicator:
            self.communicator.send_command('set_average', value=self.avg_input.value())

    @Slot()
    def _read_average(self):
        if self.communicator:
            self.communicator.send_command('read_average')

    @Slot()
    def _start_calibration(self):
        if self.communicator:
            self.communicator.send_command('calibration',
                                          mode=self.cal_mode_combo.currentText())

    @Slot()
    def _start_acquisition(self):
        if self.communicator:
            self.communicator.send_command('read_spectrum')

    @Slot()
    def _query_status(self):
        if self.communicator:
            self.communicator.send_command('get_status')

    @Slot()
    def _query_version(self):
        if self.communicator:
            self.communicator.send_command('get_version')

    @Slot(dict)
    def _handle_response(self, response):
        if not response['valid']:
            self._update_status(f"错误: {response['error']}")
            return

        data = response['data']
        if 'error' in data:
            self._update_status(f"错误: {data['error']}")
            return

        if 'spectrum' in data:
            self._plot_spectrum(data['spectrum'])
            self._update_status("光谱数据已更新")
        elif 'value' in data:
            if response['command'] == 'WL':
                self.wl_value_label.setText(str(data['value']))
            elif response['command'] == 'INTTIME':
                self.int_value_label.setText(str(data['value']))
            elif response['command'] == 'AVG':
                self.avg_value_label.setText(str(data['value']))
            elif response['command'] == 'STAT':
                self.device_status_label.setText(str(data['value']))
            elif response['command'] == 'VER':
                self.firmware_version_label.setText(str(data['value']))
            self._update_status("参数已更新")
        elif 'status' in data:
            if data['status'] == 'success':
                self._update_status("校准完成")
            else:
                self._update_status("校准失败")

    @Slot(bool)
    def _handle_connection_change(self, connected):
        if connected:
            self._update_status("设备已连接")
        else:
            self._update_status("设备已断开")

    def _update_status(self, msg):
        self.status_label.setText(msg)

    def _plot_spectrum(self, data):
        if isinstance(data, list) and len(data) > 0:
            x = list(range(len(data)))
            self.plot_curve.setData(x=x, y=data)
            self._update_status("光谱图已更新")
            
    def _start_scan(self):
        if self.communicator:
            start_wl = self.start_wl_input.value()
            end_wl = self.end_wl_input.value()
            step = self.step_wl_input.value()
            
            if start_wl >= end_wl:
                self._update_status("错误：起始波长必须小于终止波长")
                return
                
            self.start_scan_btn.setEnabled(False)
            self.stop_scan_btn.setEnabled(True)
            self.scan_status_label.setText("扫描中...")
            
            # 开始扫描过程
            current_wl = start_wl
            while current_wl <= end_wl:
                if not self.stop_scan_btn.isEnabled():
                    break
                    
                self.communicator.send_command('set_wavelength', value=current_wl)
                self.communicator.send_command('read_spectrum')
                current_wl += step
                
            self.scan_status_label.setText("扫描完成")
            self.start_scan_btn.setEnabled(True)
            self.stop_scan_btn.setEnabled(False)
            
    def _stop_scan(self):
        self.stop_scan_btn.setEnabled(False)
        self.start_scan_btn.setEnabled(True)
        self.scan_status_label.setText("扫描已停止")