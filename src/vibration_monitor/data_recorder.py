import csv
import os  # 导入 os 模块
from datetime import datetime
from .device.device_model import DeviceModel
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class DataRecorder:
    """数据记录器类"""

    def __init__(self, device: DeviceModel):
        self.device = device
        self.filename = None
        self.file = None
        self.writer = None
        self.is_recording = False
        self.data_dir = os.path.join(os.path.dirname(__file__), "data_record")  # 数据文件夹路径

    def start_recording(self):
        """开始记录"""
        if self.is_recording:
            logger.warning("数据记录已在进行中")
            return False

        # 创建按日期命名的文件夹
        today_str = datetime.now().strftime("%Y%m%d")
        today_dir = os.path.join(self.data_dir, today_str)
        os.makedirs(today_dir, exist_ok=True)  # 确保文件夹存在

        # 创建文件名
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(
            today_dir, f"vibration_data_{current_time}.csv"
        )  # 完整文件路径

        try:
            self.file = open(self.filename, 'w', newline='', encoding='utf-8-sig')
            self.writer = csv.writer(self.file)
            self.writer.writerow([
              '记录时间', '设备名称',
              '加速度X(g)', '加速度Y(g)', '加速度Z(g)',
              '角速度X(°/s)', '角速度Y(°/s)', '角速度Z(°/s)',
              'X轴振动速度(mm/s)', 'Y轴振动速度(mm/s)', 'Z轴振动速度(mm/s)',
              'X轴振动位移(um)', 'Y轴振动位移(um)', 'Z轴振动位移(um)',
              'X轴振动频率(Hz)', 'Y轴振动频率(Hz)', 'Z轴振动频率(Hz)',
              '温度(°C)'
            ])
            self.is_recording = True
            logger.info(f"开始记录数据到文件: {self.filename}")
            return True
        except Exception as e:
            logger.exception(f"创建CSV文件失败: {e}")
            return False

    def stop_recording(self):
        """停止记录"""
        if self.is_recording:
            self.is_recording = False
            if self.file:
                self.file.close()
            self.writer = None
            logger.info(f"数据已保存到文件: {self.filename}")
        else:
            logger.warning("数据记录未在进行中")
    def write_data(self, data_values):
      """写入数据"""
      if self.is_recording and self.writer:
          timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
          data_row = [
                timestamp,
                self.device.device_name
          ] + [str(v) if v is not None else "" for v in data_values]
          try:
              self.writer.writerow(data_row)
              self.file.flush()  # 立即写入
          except Exception as e:
              logger.exception(f"写入数据失败: {e}")
