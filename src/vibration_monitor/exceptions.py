class VibrationMonitorError(Exception):
    """自定义异常基类"""
    pass

class DeviceConnectionError(VibrationMonitorError):
    """设备连接错误"""
    pass

class DataAcquisitionError(VibrationMonitorError):
    """数据采集错误"""
    pass
# 可以根据需要添加更多自定义异常

