"""
光谱仪通信模块

该模块提供与光谱仪设备通信的基类及具体实现，支持串口和TCP两种通信方式。
包含基础通信协议处理、连接状态管理以及数据收发功能。
"""

import serial
import socket
from PySide6.QtCore import QObject, Signal
from spectrometer_gui.protocol_handler import ProtocolHandler

class BaseCommunicator(QObject):
    """
    通信基类

    定义通信组件的通用接口和基础功能，包含连接状态管理、数据收发信号。

    Attributes:
        data_received (Signal[dict]): 当收到完整数据包时触发，携带解析后的数据字典
        connection_changed (Signal[bool]): 连接状态变化时触发，True表示已连接，False表示断开

    Args:
        QObject (QObject): 继承自Qt核心对象以支持信号槽机制
    """
    data_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._is_connected = False

    def connect(self, **kwargs):
        """
        建立设备连接抽象方法

        Args:
            **kwargs: 具体连接参数，由子类实现定义

        Raises:
            NotImplementedError: 必须由子类具体实现
        """
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def send_command(self, cmd_type, **kwargs):
        command = ProtocolHandler.build_command(cmd_type, **kwargs)
        self._raw_send(command)

class SerialCommunicator(BaseCommunicator):
    """
    串口通信实现类

    提供通过RS-232串口与光谱仪通信的具体实现，支持异步数据收发。

    Attributes:
        _serial (serial.Serial): 底层的PySerial对象实例
    """
    def __init__(self):
        super().__init__()
        self._serial = None

    def connect(self, port, baudrate=9600, timeout=1):
        """
        建立串口连接

        Args:
            port (str): 串口设备路径(如COM3或/dev/ttyUSB0)
            baudrate (int, optional): 波特率，默认9600
            timeout (int, optional): 读取超时时间(秒)，默认1

        Raises:
            serial.SerialException: 当串口无法打开时抛出
        """
        try:
            self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            self._is_connected = True
            self.connection_changed.emit(True)
        except serial.SerialException as e:
            self.data_received.emit({'error': f'Serial connection failed: {str(e)}'})

    def _raw_send(self, data):
        if self._serial:
            self._serial.write(data.encode())
            response = self._serial.readline().decode().strip()
            parsed = ProtocolHandler.parse_response(response)
            self.data_received.emit(parsed)

class TcpCommunicator(BaseCommunicator):
    """
    TCP网络通信实现类

    提供通过TCP/IP协议与网络型光谱仪通信的具体实现。

    Attributes:
        _socket (socket.socket): 底层网络套接字对象
    """
    def __init__(self):
        super().__init__()
        self._socket = None

    def connect(self, host, port=5000, timeout=3):
        """
        建立TCP连接

        Args:
            host (str): 目标主机IP地址或域名
            port (int, optional): 目标端口号，默认5000
            timeout (int, optional): 连接超时时间(秒)，默认3

        Raises:
            socket.error: 当网络连接失败时抛出
        """
        try:
            self._socket = socket.create_connection((host, port), timeout=timeout)
            self._is_connected = True
            self.connection_changed.emit(True)
        except socket.error as e:
            self.data_received.emit({'error': f'TCP connection failed: {str(e)}'})

    def _raw_send(self, data):
        """
        原始数据发送实现（TCP版本）

        Args:
            data (str): 要发送的原始字符串数据

        Raises:
            ConnectionError: 当网络连接异常中断时抛出
            TimeoutError: 当响应超时时抛出
        """
        if self._socket:
            self._socket.sendall(data.encode())
            response = self._socket.recv(1024).decode().strip()
            parsed = ProtocolHandler.parse_response(response)
            self.data_received.emit(parsed)