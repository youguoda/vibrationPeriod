import sys
from PyQt5.QtWidgets import QApplication
from .gui.main_window import VibrationMonitorWindow  # 从 gui 模块导入
from .device.device_wtvb01 import DeviceWTVB01 # 导入具体设备
from .config import Config  # 导入 Config
from .utils.logger import setup_logger  #导入日志

logger = setup_logger(__name__) #日志

def main():
    """程序主入口"""
    try:
        # 加载配置
        config = Config()

        # 从配置文件读取设备参数
        device_name = config.get('Device', 'device_name', fallback="未知设备")
        port = config.get('Device', 'port', fallback="COM9")
        baudrate = config.getint('Device', 'baudrate', fallback=230400)
        address = config.getint('Device', 'address', fallback=0x50)

        logger.info(f"使用配置: 设备名称={device_name}, 端口={port}, 波特率={baudrate}, 地址={address}")
        # 初始化设备
        # device = device_model.DeviceModel("测试设备", "COM5", 230400, 0x50)
        device = DeviceWTVB01(device_name, port, baudrate, address) #具体设备
        device.open_device()
        device.start_data_acquisition()

         # 创建 Qt 应用程序
        app = QApplication(sys.argv)
        # 创建主窗口
        window = VibrationMonitorWindow(device)
        window.show()
         # 运行应用程序
        sys.exit(app.exec_())
    except Exception as e:
       logger.exception(f"程序启动失败: {e}")
       print(f"程序启动失败，详情查看日志") # 给用户一个提示
    finally:
      # 确保在程序退出时关闭设备连接和停止轮询
      if 'device' in locals() and device.is_open:
          device.stop_data_acquisition()
          device.close_device()
if __name__ == "__main__":
    main()
