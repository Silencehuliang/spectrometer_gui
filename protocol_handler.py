class ProtocolHandler:
    """
    AE8600光谱仪协议处理核心模块
    版本号：1.0
    功能：
    - 指令集定义与封装
    - 响应数据解析
    - 校验和计算
    """

    COMMAND_SET = {
        'set_wavelength': 'WL {value}',  # 设置波长，value范围200-1000nm
        'read_wavelength': 'WL?',        # 读取当前波长
        'read_spectrum': 'SPT?',         # 读取光谱数据
        'read_intensity': 'INT?',        # 读取光强度
        'set_integration': 'INTTIME {value}',  # 设置积分时间，value范围1-65535ms
        'read_integration': 'INTTIME?',   # 读取积分时间
        'calibration': 'CAL {mode}',     # 校准模式，mode: DARK=暗校准, REF=参考校准
        'get_status': 'STAT?',           # 读取设备状态
        'set_average': 'AVG {value}',    # 设置平均次数，value范围1-100
        'read_average': 'AVG?',          # 读取平均次数
        'reset_device': 'RST',           # 设备复位
        'get_version': 'VER?'            # 读取固件版本
    }

    @staticmethod
    def build_command(cmd_type, **kwargs):
        """
        构造带校验和的完整指令
        """
        raw_cmd = ProtocolHandler.COMMAND_SET[cmd_type].format(**kwargs)
        checksum = sum(ord(c) for c in raw_cmd) % 256
        return f"${raw_cmd}*{checksum:02X}\r\n"

    @staticmethod
    def parse_response(response):
        """
        解析设备响应数据
        返回格式：
        {
            'valid': bool,
            'command': str,
            'data': dict,
            'error': str
        }
        """
        if not response.startswith('$') or '*' not in response:
            return {'valid': False, 'error': 'Invalid frame format'}

        try:
            payload, checksum = response[1:-3].split('*')
            calculated_csum = sum(ord(c) for c in payload) % 256
            if calculated_csum != int(checksum, 16):
                return {'valid': False, 'error': 'Checksum mismatch'}

            return {
                'valid': True,
                'command': payload.split(' ')[0],
                'data': ProtocolHandler._parse_payload(payload)
            }
        except Exception as e:
            return {'valid': False, 'error': f'Parsing error: {str(e)}'}

    @staticmethod
    def _parse_payload(payload):
        """解析不同类型的响应数据"""
        try:
            # 分离命令和数据部分
            parts = payload.split(' ', 1)
            cmd = parts[0]
            data = parts[1] if len(parts) > 1 else ''

            # 根据命令类型解析数据
            if cmd in ['WL', 'INTTIME', 'AVG']:
                return {'value': float(data) if '.' in data else int(data)}
            elif cmd == 'SPT':
                # 解析光谱数据数组
                values = [float(x) for x in data.split(',')]
                return {'spectrum': values}
            elif cmd == 'INT':
                return {'intensity': float(data)}
            elif cmd == 'STAT':
                # 状态位解析
                status_code = int(data, 16)
                return {
                    'ready': bool(status_code & 0x01),
                    'error': bool(status_code & 0x02),
                    'calibrating': bool(status_code & 0x04),
                    'measuring': bool(status_code & 0x08)
                }
            elif cmd == 'VER':
                return {'version': data.strip()}
            elif cmd == 'CAL':
                return {'status': 'success' if data == 'OK' else 'error'}
            else:
                return {'raw': payload}
        except Exception as e:
            return {'error': f'Data parsing error: {str(e)}'}