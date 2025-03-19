"""异步通信模块

提供基于QThread的异步通信实现，用于处理耗时的设备通信操作。
包含异步串口和TCP通信类，支持非阻塞数据收发。
"""

from PySide6.QtCore import QThread, Signal, QObject
from spectrometer_gui.protocol_handler import ProtocolHandler
import serial
import socket
import time

class CommunicationThread(QThread):
    """通信线程基类

    处理耗时的数据收发操作，避免阻塞主线程。
    """
    data_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._command_queue = []

    def add_command(self, cmd_type, **kwargs):
        """添加待发送的命令到队列"""
        command = ProtocolHandler.build_command(cmd_type, **kwargs)
        self._command_queue.append(command)

    def stop(self):
        """停止线程运行"""
        self._running = False
        self.wait()

class SerialThread(CommunicationThread):
    """串口通信线程

    异步处理串口数据收发。
    """
    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._serial = None

    def run(self):
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self._running = True

            while self._running:
                # 处理发送队列
                if self._command_queue:
                    command = self._command_queue.pop(0)
                    self._serial.write(command.encode())
                    response = self._serial.readline().decode().strip()
                    if response:
                        parsed = ProtocolHandler.parse_response(response)
                        self.data_received.emit(parsed)

                # 检查是否有新数据
                if self._serial.in_waiting:
                    data = self._serial.readline().decode().strip()
                    if data:
                        parsed = ProtocolHandler.parse_response(data)
                        self.data_received.emit(parsed)
                
                time.sleep(0.01)  # 避免CPU占用过高

        except serial.SerialException as e:
            self.error_occurred.emit(f'Serial error: {str(e)}')
        finally:
            if self._serial:
                self._serial.close()

class TcpThread(CommunicationThread):
    """TCP通信线程

    异步处理网络数据收发。
    """
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self._socket = None

    def run(self):
        try:
            self._socket = socket.create_connection(
                (self.host, self.port),
                timeout=3
            )
            self._socket.settimeout(1)  # 设置接收超时
            self._running = True

            while self._running:
                # 处理发送队列
                if self._command_queue:
                    command = self._command_queue.pop(0)
                    self._socket.sendall(command.encode())
                    try:
                        response = self._socket.recv(1024).decode().strip()
                        if response:
                            parsed = ProtocolHandler.parse_response(response)
                            self.data_received.emit(parsed)
                    except socket.timeout:
                        pass

                # 检查是否有新数据
                try:
                    data = self._socket.recv(1024).decode().strip()
                    if data:
                        parsed = ProtocolHandler.parse_response(data)
                        self.data_received.emit(parsed)
                except socket.timeout:
                    pass

                time.sleep(0.01)  # 避免CPU占用过高

        except socket.error as e:
            self.error_occurred.emit(f'TCP error: {str(e)}')
        finally:
            if self._socket:
                self._socket.close()

class AsyncCommunicator(QObject):
    """异步通信管理器

    管理通信线程的创建、启动和停止。
    提供统一的通信接口。
    """
    connection_changed = Signal(bool)
    data_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._comm_thread = None
        self._connected = False

    def connect(self, interface_type, **kwargs):
        """建立设备连接

        Args:
            interface_type (str): 接口类型，'serial'或'tcp'
            **kwargs: 连接参数
        """
        if self._connected:
            self.disconnect()

        if interface_type == 'serial':
            self._comm_thread = SerialThread(
                port=kwargs.get('port'),
                baudrate=kwargs.get('baudrate', 9600)
            )
        else:  # tcp
            self._comm_thread = TcpThread(
                host=kwargs.get('host'),
                port=kwargs.get('port')
            )

        self._comm_thread.data_received.connect(self.data_received.emit)
        self._comm_thread.error_occurred.connect(self._handle_error)
        self._comm_thread.start()
        self._connected = True
        self.connection_changed.emit(True)

    def disconnect(self):
        """断开设备连接"""
        if self._comm_thread:
            self._comm_thread.stop()
            self._comm_thread = None
        self._connected = False
        self.connection_changed.emit(False)

    def send_command(self, cmd_type, **kwargs):
        """发送命令

        Args:
            cmd_type (str): 命令类型
            **kwargs: 命令参数
        """
        if self._comm_thread and self._connected:
            self._comm_thread.add_command(cmd_type, **kwargs)

    def _handle_error(self, error_msg):
        """处理通信错误"""
        self.error_occurred.emit(error_msg)
        self.disconnect()