from abc import ABC, abstractmethod
from ..utils.logger import setup_logger

logger = setup_logger(__name__) #日志

class DeviceModel(ABC):
    """设备模型抽象基类"""

    def __init__(self, device_name, port, baudrate, address):
        """
        初始化设备模型

        Args:
            device_name (str): 设备名称
            port (str): 串口号
            baudrate (int): 波特率
            address (int): 设备地址
        """
        self.device_name = device_name
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.is_open = False
        self.data = {}  # 设备数据字典用于存储设备数据
        logger.info(f"初始化设备模型: {device_name} ({port}, {baudrate}, {address})")

    @abstractmethod
    def open_device(self):
        """打开设备连接"""
        pass

    @abstractmethod
    def close_device(self):
        """关闭设备连接"""
        pass
    @abstractmethod
    def start_data_acquisition(self):
         """开始数据采集"""
         pass
    @abstractmethod
    def stop_data_acquisition(self):
        """停止数据采集"""
        pass

    @abstractmethod
    def read_data(self):
        """读取设备数据"""
        pass

    def get_data(self, key):
        """
        获取设备数据

        Args:
            key (str): 数据的键

        Returns:
            any: 数据值，如果键不存在则返回 None
        """
        return self.data.get(key)

    def _set_data(self, key, value):
        """
        设置设备数据 (内部方法)
        """
        self.data[key] = value
