import threading
import time
import serial
from .device_model import DeviceModel  # 导入基类
from ..exceptions import DeviceConnectionError, DataAcquisitionError
from ..utils.logger import setup_logger  # 导入日志记录器

from typing import List

# 计算CRC校验的表 (通常放在一个单独的模块中，这里为了演示)
# region   计算CRC
auchCRCHi = [
    0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01,
    0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41,
    0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81,
    0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
    0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01,
    0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
    0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01,
    0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
    0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
    0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01,
    0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
    0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
    0x40]

auchCRCLo = [
    0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06, 0x07, 0xC7, 0x05, 0xC5, 0xC4,
    0x04, 0xCC, 0x0C, 0x0D, 0xCD, 0x0F, 0xCF, 0xCE, 0x0E, 0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09,
    0x08, 0xC8, 0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A, 0x1E, 0xDE, 0xDF, 0x1F, 0xDD,
    0x1D, 0x1C, 0xDC, 0x14, 0xD4, 0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6, 0xD2, 0x12, 0x13, 0xD3,
    0x11, 0xD1, 0xD0, 0x10, 0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3, 0xF2, 0x32, 0x36, 0xF6, 0xF7,
    0x37, 0xF5, 0x35, 0x34, 0xF4, 0x3C, 0xFC, 0xFD, 0x3D, 0xFF, 0x3F, 0x3E, 0xFE, 0xFA, 0x3A,
    0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38, 0x28, 0xE8, 0xE9, 0x29, 0xEB, 0x2B, 0x2A, 0xEA, 0xEE,
    0x2E, 0x2F, 0xEF, 0x2D, 0xED, 0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26,
    0x22, 0xE2, 0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0, 0xA0, 0x60, 0x61, 0xA1, 0x63, 0xA3, 0xA2,
    0x62, 0x66, 0xA6, 0xA7, 0x67, 0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D, 0xAF, 0x6F,
    0x6E, 0xAE, 0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68, 0x78, 0xB8, 0xB9, 0x79, 0xBB,
    0x7B, 0x7A, 0xBA, 0xBE, 0x7E, 0x7F, 0xBF, 0x7D, 0xBD, 0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5,
    0x77, 0xB7, 0xB6, 0x76, 0x72, 0xB2, 0xB3, 0x73, 0xB1, 0x71, 0x70, 0xB0, 0x50, 0x90, 0x91,
    0x51, 0x93, 0x53, 0x52, 0x92, 0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C,
    0x5D, 0x9D, 0x5F, 0x9F, 0x9E, 0x5E, 0x5A, 0x9A, 0x9B, 0x5B, 0x99, 0x59, 0x58, 0x98, 0x88,
    0x48, 0x49, 0x89, 0x4B, 0x8B, 0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C, 0x8C,
    0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86, 0x82, 0x42, 0x43, 0x83, 0x41, 0x81, 0x80,
    0x40]

# endregion  计算CRC

logger = setup_logger(__name__)  # 创建一个 logger 实例


class DeviceWTVB01(DeviceModel):
    """WTVB01型号设备的具体实现"""

    def __init__(self, device_name: str, port: str, baudrate: int, address: int):
        super().__init__(device_name, port, baudrate, address)
        self.serial_port: serial.Serial = None   # type: ignore
        self.read_thread: threading.Thread = None   # type: ignore
        self.loop: bool = False
        self.temp_bytes: List[int] = []
        self.stat_reg: int = None   # type: ignore #起始寄存器
        self.receive_buffer: bytearray = bytearray() # 新增：接收缓冲区

    def get_crc(self, data: List[int], data_len: int) -> int:
        """计算 CRC 校验"""
        tempH = 0xff
        tempL = 0xff
        for i in range(data_len):
            temp_index = (tempH ^ data[i]) & 0xff
            tempH = (tempL ^ auchCRCHi[temp_index]) & 0xff
            tempL = auchCRCLo[temp_index]
        return (tempH << 8) | tempL

    def open_device(self):
        """打开设备连接"""
        logger.info(f"尝试打开设备: {self.device_name} ({self.port}, {self.baudrate}, {self.address})")
        if self.is_open:
           logger.warning("设备已打开，无需重复打开")
           return
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.serial_port = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=1.0,
                    write_timeout=1.0,
                    exclusive = True
                )
                if not self.serial_port.is_open:
                    self.serial_port.open()


                self.is_open = True
                logger.info(f"设备连接成功: {self.device_name}")
                return #成功连接,直接返回

            except serial.SerialException as e:
                error_msg = f"串口连接失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                logger.error(error_msg)
                if attempt == max_retries - 1:  # 最后一次尝试
                    raise DeviceConnectionError(error_msg) from e
                time.sleep(2)
            except Exception as e:  # 捕获其他可能的异常
                error_msg = f"打开设备时发生意外错误: {e}"
                logger.exception(error_msg)
                raise DeviceConnectionError(error_msg) from e

    def close_device(self):
        """关闭设备连接"""
        logger.info(f"正在关闭设备: {self.device_name}")
        self.stop_data_acquisition()  #先停数据采集
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.reset_input_buffer()
                    self.serial_port.reset_output_buffer()
                    self.serial_port.close()
                    logger.info("串口已关闭")
            except Exception as e:
                 logger.exception(f"关闭串口失败: {e}")
            finally:
               self.serial_port = None  # 确保 serial_port 被设置为 None
        self.is_open = False
        logger.info(f"设备已关闭: {self.device_name}")

    def start_data_acquisition(self):
        """启动数据采集"""
        if self.loop:
            logger.warning("数据采集已在进行中，无需重复启动")
            return
        if not self.is_open:
            logger.warning("设备未打开,无法启动数据采集")
            raise DeviceConnectionError("尝试开始采集数据时设备未打开")  # 使用自定义异常

        self.loop = True
        self.read_thread = threading.Thread(target=self._read_data_loop, daemon=True)
        self.read_thread.start()
        logger.info("数据采集已启动")
        self.read_data()  # 立即发送读取数据的命令

    def stop_data_acquisition(self):
      """停止数据采集"""
      if self.loop:
          self.loop = False
          if self.read_thread and self.read_thread.is_alive():
              self.read_thread.join(timeout=2)  # 等待线程结束,设置超时
              if self.read_thread.is_alive():  # 如果超时后线程仍在运行
                  logger.warning("数据采集线程无法正常停止")
          logger.info("数据采集已停止")
      else:
          logger.warning("数据采集未在进行中")

    def _read_data_loop(self):
        """数据读取循环 (内部方法)"""
        logger.debug("数据读取线程已启动")
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.loop:
            # print("Debug: _read_data_loop is running")  # 调试输出
            try:
                if not self.is_open or not self.serial_port or not self.serial_port.is_open:
                    logger.error("设备未连接或串口未打开")
                    raise DeviceConnectionError("设备未连接或串口未打开")

                # 从串口读取数据
                if self.serial_port.in_waiting > 0:
                    received_data = self.serial_port.read(self.serial_port.in_waiting)
                    self._on_data_received(received_data) #直接处理

                # 周期性发送读取命令(重要！！！)
                self.read_data()

                consecutive_errors = 0  # 重置连续错误计数
                time.sleep(0.05) # 这个延时是必要的,防止发送过于频繁

            except DataAcquisitionError as e:
                consecutive_errors += 1
                logger.error(f"数据采集错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                  logger.critical("连续数据采集错误次数过多，停止采集")
                  self.stop_data_acquisition()  # 停止数据采集
                  break
            except DeviceConnectionError:
                self.close_device()
                break

            except serial.SerialException as e:
              consecutive_errors += 1
              logger.error(f"串口读取错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
              if consecutive_errors >= max_consecutive_errors:
                logger.critical("连续串口读取错误次数过多，停止采集")
                self.stop_data_acquisition()
                break
            except Exception as e:
                consecutive_errors += 1
                logger.exception(f"数据采集线程发生未预期错误({consecutive_errors}/{max_consecutive_errors})")
                if consecutive_errors >= max_consecutive_errors:
                  logger.critical("发生太多未预期错误，停止采集")
                  self.stop_data_acquisition()
                  break

        logger.debug("数据读取线程已停止")

    def read_data(self):
        """读取设备数据"""
       # 从0x34(加速度)开始读取到0x46(振动频率)，总共19个寄存器
        self._read_reg(0x34, 19)


    def _read_reg(self, reg_addr, reg_count):
          """读取寄存器 (内部方法)"""
          self.stat_reg = reg_addr
          command = self._get_read_bytes(self.address, reg_addr, reg_count)
          self._send_data(command)

    def _write_reg(self, reg_addr, value):
        """写入寄存器 (内部方法)"""
        self._unlock() #先解锁
        time.sleep(0.1)
        command = self._get_write_bytes(self.address,reg_addr,value)
        self._send_data(command)
        time.sleep(0.1) #延迟
        self._save() #保存

        # 发送读取指令封装
    def _get_read_bytes(self, devid: int, reg_addr: int, reg_count: int) -> bytes:
        """获取读取寄存器的命令字节 (内部方法)"""
        temp_bytes = [0] * 8  # 使用列表存储整数
        temp_bytes[0] = devid
        temp_bytes[1] = 0x03
        temp_bytes[2] = reg_addr >> 8
        temp_bytes[3] = reg_addr & 0xff
        temp_bytes[4] = reg_count >> 8
        temp_bytes[5] = reg_count & 0xff
        temp_crc = self.get_crc(temp_bytes, len(temp_bytes) - 2)
        temp_bytes[6] = temp_crc >> 8
        temp_bytes[7] = temp_crc & 0xff
        return bytes(temp_bytes)  # 转换为 bytes


      # 发送写入指令封装
    def _get_write_bytes(self, devid, reg_addr, s_value):
        temp_bytes = [None] * 8
        temp_bytes[0] = devid
        temp_bytes[1] = 0x06
        temp_bytes[2] = reg_addr >> 8
        temp_bytes[3] = reg_addr & 0xff
        temp_bytes[4] = s_value >> 8
        temp_bytes[5] = s_value & 0xff
        temp_crc = self.get_crc(temp_bytes, len(temp_bytes) - 2)
        temp_bytes[6] = temp_crc >> 8
        temp_bytes[7] = temp_crc & 0xff
        return temp_bytes

    def _send_data(self, data: bytes):
        """发送数据 (内部方法,已修改)"""
        if not self.serial_port or not self.serial_port.is_open:
            raise DeviceConnectionError("尝试发送数据时串口未打开")
        try:
            self.serial_port.write(data) #直接传入bytes
        except serial.SerialException as e:
            raise DataAcquisitionError(f"发送数据失败: {e}") from e

    def _on_data_received(self, data: bytes):
        """
        处理接收到的数据 (内部方法)

        此方法模拟了 vibration_monitor_gui.py 中 revData 函数的逻辑。
        """
        # print(f"Debug: _on_data_received called, data: {data}") 
        self.receive_buffer.extend(data)  # 将接收到的数据添加到缓冲区
        # print(f"Debug: receive_buffer: {self.receive_buffer}")

        while len(self.receive_buffer) >= 8:  # 至少有8个字节才能进行处理 (最小数据包长度)
            if self.receive_buffer[0] != self.address:  # 地址不匹配
                logger.warning(f"接收到地址不匹配的数据包: {self.receive_buffer[0]}, 预期地址: {self.address}")
                del self.receive_buffer[0]
                continue

            if self.receive_buffer[1] != 0x03:  # 功能码不匹配
                 logger.warning(f"接收到功能码不匹配的数据包: {self.receive_buffer[1]}, 预期功能码: 0x03")
                 del self.receive_buffer[0]
                 continue

            data_length = self.receive_buffer[2]
            if len(self.receive_buffer) < data_length + 5:  # 数据长度不足
                break  # 等待更多数据

            # 提取完整数据包
            packet = list(self.receive_buffer[:data_length + 5])  # 转换为整数列表
            del self.receive_buffer[:data_length + 5] #删除

            # CRC 校验
            received_crc = packet[-2] << 8 | packet[-1]
            calculated_crc = self.get_crc(packet, len(packet) - 2)

            if received_crc != calculated_crc:
                logger.warning(f"CRC 校验失败: 收到 CRC = {received_crc:04X}, 计算 CRC = {calculated_crc:04X}")
                continue  # 丢弃数据包

            # 数据校验成功，处理数据
            try:
                self._process_data(packet)
            except Exception as e:
                logger.exception(f"处理数据包时发生错误: {e}")
                # 可以选择清空缓冲区或保留剩余数据,这里选择保留

    def _process_data(self, packet: List[int]):
        """解析数据 (内部方法)"""
        # print(f"Debug: _process_data called, packet: {packet}")
        data_length = packet[2]
        if data_length % 2 != 0:
            logger.error(f"数据长度错误: {data_length}，应为偶数")
            return

        start_reg = 0x34 #默认起始寄存器
        try:
            for i in range(int(data_length/2)):
                value = packet[2 * i + 3] << 8 | packet[2*i + 4]
                value = self._change(value) #有符号

                #根据寄存器地址进行解析
                if start_reg == 0x34:
                  key = "52" # "accel_x"
                elif start_reg == 0x35:
                  key = "53"  # accel_y
                elif start_reg == 0x36:
                  key = "54"  # accel_z
                elif start_reg == 0x37:
                    key = "55" # gyro_x
                elif start_reg == 0x38:
                    key = "56" # gyro_y
                elif start_reg == 0x39:
                   key = "57" # gyro_z
                elif start_reg == 0x3A:
                    key = "58" # "vib_x"
                elif start_reg == 0x3B:
                    key = "59"  # vib_y
                elif start_reg == 0x3C:
                    key = "60"  # vib_z
                elif start_reg ==0x3D:
                    key ="61" #angle_x
                elif start_reg == 0x3E:
                   key ="62"  #angle_y
                elif start_reg == 0x3F:
                   key ="63"  #angle_z
                elif start_reg == 0x40:
                   key = "64"  # temp
                elif start_reg == 0x41:
                    key = "65"  # disp_x
                elif start_reg == 0x42:
                    key = "66"  # disp_y
                elif start_reg == 0x43:
                    key = "67"  # disp_z
                elif start_reg == 0x44:
                    key = "68"  # freq_x
                elif start_reg == 0x45:
                    key = "69"  # freq_y
                elif start_reg == 0x46:
                    key = "70"  # freq_z
                else:
                  key = str(start_reg)  # 未知寄存器，直接使用寄存器地址作为键

                if 0x34 <= start_reg <= 0x36:  # 加速度
                  value = value / 32768 * 16
                elif 0x37 <= start_reg <= 0x39:  # 角速度
                    value = value / 32768 * 2000
                elif 0x3D <= start_reg <= 0x3F:  # 振动角度
                    value = value / 32768 * 180
                elif start_reg == 0x40:  # 温度
                    value = value / 100

                self._set_data(key, value)
                start_reg += 1
                # print(f"Debug: self.data in _process_data: {self.data}")
        except Exception as e:
            logger.exception(f"解析数据时发生错误: {e}")
            raise DataAcquisitionError("解析数据时发生错误") from e

     # 解锁
    def _unlock(self):
        cmd = self._get_write_bytes(self.address, 0x69, 0xb588)
        self._send_data(cmd)

    # 保存
    def _save(self):
        cmd = self._get_write_bytes(self.address, 0x00, 0x0000)
        self._send_data(cmd)

        
    @staticmethod
    def _change(data: int) -> int:
        if data > 32768:
            data = data - 65535;
        return data
