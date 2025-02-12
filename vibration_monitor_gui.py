import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QGridLayout, QGroupBox, QTableWidget,
                           QTableWidgetItem)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPalette, QColor, QFont
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import device_model
import time

# 定义一个信号,用于传递数据
class DataSignal(QThread):
    data_signal = pyqtSignal(dict)

    def __init__(self, device):
        super().__init__()
        self.device = device
        self._running = True

    def run(self):
         while self._running:
            try:
                # 获取所有数据
                data_values = {
                    "58": self.device.get("58"),
                    "59": self.device.get("59"),
                    "60": self.device.get("60"),
                    "61": self.device.get("61"),
                    "62": self.device.get("62"),
                    "63": self.device.get("63"),
                    "65": self.device.get("65"),
                    "66": self.device.get("66"),
                    "67": self.device.get("67"),
                    "68": self.device.get("68"),
                    "69": self.device.get("69"),
                    "70": self.device.get("70"),
                }

                self.data_signal.emit(data_values)
                time.sleep(0.2)  # 与主界面更新频率同步

            except Exception as e:
                print(f"Data acquisition error: {e}")
                # 可以添加重连逻辑
                if not self.device.isOpen:
                    print("Device disconnected")
                    break

    def stop(self):
      self._running = False
      self.wait()
      
class VibrationMonitor(QMainWindow):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.init_ui()
        self.data_thread = DataSignal(self.device)
        self.data_thread.data_signal.connect(self.update_data)
        self.data_thread.start()

        # 数据缓存
        self.data_length = 500  # 显示最近500个数据点
        self.timestamps = []

        # 振动速度数据
        self.vib_speed_x = []
        self.vib_speed_y = []
        self.vib_speed_z = []

        # 振动角度数据
        self.vib_angle_x = []
        self.vib_angle_y = []
        self.vib_angle_z = []

        # 振动位移数据
        self.vib_disp_x = []
        self.vib_disp_y = []
        self.vib_disp_z = []

        # 振动频率数据
        self.vib_freq_x = []
        self.vib_freq_y = []
        self.vib_freq_z = []

        # 上次更新时间
        self.last_timestamp = 0

        # 更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50) #更快的刷新频率

    def create_plot_widget(self, title, y_label, y_units):
        """创建统一样式的图表部件"""
        plot = pg.PlotWidget(title=title)
        plot.setBackground('w')  # 白色背景
        plot.showGrid(x=True, y=True, alpha=0.3)  # 显示网格
        plot.setLabel('left', y_label, units=y_units)
        plot.setLabel('bottom', '时间 (s)')
        plot.addLegend()

        # 设置标题样式
        plot.setTitle(title, size='12pt', color='k')

        # 设置坐标轴样式
        plot.getAxis('bottom').setPen('k')
        plot.getAxis('left').setPen('k')
        plot.getAxis('bottom').setTextPen('k')
        plot.getAxis('left').setTextPen('k')

        return plot

    def init_ui(self):
        self.setWindowTitle('振动监测系统')
        self.setGeometry(100, 100, 1600, 900)
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QLabel {
                font-size: 10pt;
                color: #333333;
            }
            QTableWidget {
                font-size: 10pt;
                color: #333333;
                gridline-color: #cccccc;
                border: 1px solid #cccccc; /* 添加边框 */
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #cccccc;
            }
        """)

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建网格布局, 用于放置图表
        grid_layout = QGridLayout()
        
        # 第1行第1列
        # 1. 振动速度图
        speed_group = QGroupBox("振动速度")
        speed_layout = QVBoxLayout()
        self.speed_plot = self.create_plot_widget('', '速度', 'mm/s')
        self.speed_x_curve = self.speed_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.speed_y_curve = self.speed_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.speed_z_curve = self.speed_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        speed_layout.addWidget(self.speed_plot)
        speed_group.setLayout(speed_layout)
        grid_layout.addWidget(speed_group, 0, 0)

        # 第1行第2列
        # 2. 振动角度图
        angle_group = QGroupBox("振动角度")
        angle_layout = QVBoxLayout()
        self.angle_plot = self.create_plot_widget('', '角度', '°')
        self.angle_x_curve = self.angle_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.angle_y_curve = self.angle_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.angle_z_curve = self.angle_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        angle_layout.addWidget(self.angle_plot)
        angle_group.setLayout(angle_layout)
        grid_layout.addWidget(angle_group, 0, 1)

        # 第2行第1列
        # 3. 振动位移图
        disp_group = QGroupBox("振动位移")
        disp_layout = QVBoxLayout()
        self.disp_plot = self.create_plot_widget('', '位移', 'μm')
        self.disp_x_curve = self.disp_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.disp_y_curve = self.disp_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.disp_z_curve = self.disp_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        disp_layout.addWidget(self.disp_plot)
        disp_group.setLayout(disp_layout)
        grid_layout.addWidget(disp_group, 1, 0)
        
        #第2行第2列
        # 4. 振动频率图
        freq_group = QGroupBox("振动频率")
        freq_layout = QVBoxLayout()
        self.freq_plot = self.create_plot_widget('', '频率', 'Hz')
        self.freq_x_curve = self.freq_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.freq_y_curve = self.freq_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.freq_z_curve = self.freq_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        freq_layout.addWidget(self.freq_plot)
        freq_group.setLayout(freq_layout)
        grid_layout.addWidget(freq_group, 1, 1)
        
        # 添加到主布局
        main_layout.addLayout(grid_layout)

       # 创建表格布局(实时数据)
        table_layout = QHBoxLayout()

        self.data_table = QTableWidget()
        # data_table最小宽度
        self.data_table.setMinimumWidth(1000)


        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['参数', 'X轴', 'Y轴', 'Z轴', '单位', '状态', '报警阈值'])
        self.data_table.setRowCount(4)
        # 创建表格项,并添加到表格中,第一列
        self.data_table.setItem(0, 0, QTableWidgetItem('振动速度'))
        self.data_table.setItem(1, 0, QTableWidgetItem('振动角度'))
        self.data_table.setItem(2, 0, QTableWidgetItem('振动位移'))
        self.data_table.setItem(3, 0, QTableWidgetItem('振动频率'))

        # 单位, 第5列
        self.data_table.setItem(0, 4, QTableWidgetItem('mm/s'))
        self.data_table.setItem(1, 4, QTableWidgetItem('°'))
        self.data_table.setItem(2, 4, QTableWidgetItem('μm'))
        self.data_table.setItem(3, 4, QTableWidgetItem('Hz'))

        # 调整列宽
        self.data_table.setColumnWidth(0, 80)  # 参数
        self.data_table.setColumnWidth(1, 60)  # X轴
        self.data_table.setColumnWidth(2, 60)  # Y轴
        self.data_table.setColumnWidth(3, 60)  # Z轴
        self.data_table.setColumnWidth(4, 60)  # 单位
        self.data_table.setColumnWidth(5, 80)  # 状态
        self.data_table.setColumnWidth(6, 80)  # 报警阈值
        
        table_layout.addWidget(self.data_table)

        # 创建统计表格(统计数据,最大值, 最小值, 平均值)
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)  #  X, Y, Z,  和所有参数的平均值
        self.stats_table.setHorizontalHeaderLabels(['参数', '最大值', '最小值', '平均值'])
        self.stats_table.setRowCount(12)  # 4个参数 * 3个轴 = 12行

        # 填充统计表格的参数列(第一列)
        stats_params = [
            '速度X', '速度Y', '速度Z',
            '角度X', '角度Y', '角度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z'
        ]
        for i, param in enumerate(stats_params):
            self.stats_table.setItem(i, 0, QTableWidgetItem(param))

        # 调整统计表格的列宽
        self.stats_table.setColumnWidth(0, 80)  # 参数
        self.stats_table.setColumnWidth(1, 80)  # 最大值
        self.stats_table.setColumnWidth(2, 80)  # 最小值
        self.stats_table.setColumnWidth(3, 80)  # 平均值


        table_layout.addWidget(self.stats_table)

        main_layout.addLayout(table_layout)

    def safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def update_data(self, data_values):
        try:
            # 获取最新数据, 并转换为浮点数, 如果转换失败则使用默认值 0.0
            vib_x = self.safe_float(data_values.get("58"))
            vib_y = self.safe_float(data_values.get("59"))
            vib_z = self.safe_float(data_values.get("60"))
            angle_x = self.safe_float(data_values.get("61"))
            angle_y = self.safe_float(data_values.get("62"))
            angle_z = self.safe_float(data_values.get("63"))
            disp_x = self.safe_float(data_values.get("65"))
            disp_y = self.safe_float(data_values.get("66"))
            disp_z = self.safe_float(data_values.get("67"))
            freq_x = self.safe_float(data_values.get("68"))
            freq_y = self.safe_float(data_values.get("69"))
            freq_z = self.safe_float(data_values.get("70"))


            # 更新时间戳(使用时间间隔)
            current_time = datetime.now().timestamp()
            if self.timestamps:
                time_diff = current_time - self.last_timestamp
                self.timestamps.append(self.timestamps[-1] + time_diff)  # 累加时间间隔
            else:
                self.timestamps.append(0)  # 第一次为0, 时间戳从0开始
            self.last_timestamp = current_time

            # 更新各数据列表
            self.vib_speed_x.append(vib_x)
            self.vib_speed_y.append(vib_y)
            self.vib_speed_z.append(vib_z)
            self.vib_angle_x.append(angle_x)
            self.vib_angle_y.append(angle_y)
            self.vib_angle_z.append(angle_z)
            self.vib_disp_x.append(disp_x)
            self.vib_disp_y.append(disp_y)
            self.vib_disp_z.append(disp_z)
            self.vib_freq_x.append(freq_x)
            self.vib_freq_y.append(freq_y)
            self.vib_freq_z.append(freq_z)

            # 限制数据长度, 如果数据长度超过了设定的最大长度, 则移除最早的数据
            if len(self.timestamps) > self.data_length:
                self.timestamps.pop(0)
                self.vib_speed_x.pop(0)
                self.vib_speed_y.pop(0)
                self.vib_speed_z.pop(0)
                self.vib_angle_x.pop(0)
                self.vib_angle_y.pop(0)
                self.vib_angle_z.pop(0)
                self.vib_disp_x.pop(0)
                self.vib_disp_y.pop(0)
                self.vib_disp_z.pop(0)
                self.vib_freq_x.pop(0)
                self.vib_freq_y.pop(0)
                self.vib_freq_z.pop(0)

            # 更新实时数据表格
            self.update_data_table(vib_x, vib_y, vib_z, angle_x, angle_y, angle_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z)

            # 更新统计数据表格
            self.update_stats_table()

        except Exception as e:
            print(f"Error updating data: {e}")

    def update_data_table(self, vib_x, vib_y, vib_z, angle_x, angle_y, angle_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z):
        """更新实时数据表格"""
        # 设置表格的值, 将获取的X, Y, Z轴的数据更新到表格中
        # 振动速度
        self.data_table.setItem(0, 1, QTableWidgetItem(f"{vib_x:.2f}"))
        self.data_table.setItem(0, 2, QTableWidgetItem(f"{vib_y:.2f}"))
        self.data_table.setItem(0, 3, QTableWidgetItem(f"{vib_z:.2f}"))
        # 振动角度
        self.data_table.setItem(1, 1, QTableWidgetItem(f"{angle_x:.2f}"))
        self.data_table.setItem(1, 2, QTableWidgetItem(f"{angle_y:.2f}"))
        self.data_table.setItem(1, 3, QTableWidgetItem(f"{angle_z:.2f}"))
        # 振动位移
        self.data_table.setItem(2, 1, QTableWidgetItem(f"{disp_x:.2f}"))
        self.data_table.setItem(2, 2, QTableWidgetItem(f"{disp_y:.2f}"))
        self.data_table.setItem(2, 3, QTableWidgetItem(f"{disp_z:.2f}"))
        # 振动频率
        self.data_table.setItem(3, 1, QTableWidgetItem(f"{freq_x:.2f}"))
        self.data_table.setItem(3, 2, QTableWidgetItem(f"{freq_y:.2f}"))
        self.data_table.setItem(3, 3, QTableWidgetItem(f"{freq_z:.2f}"))

        # 设置状态和报警阈值(这里先留空,后续可以根据需求添加逻辑)
        for row in range(4):
            self.data_table.setItem(row, 5, QTableWidgetItem("正常"))  # 状态列
            self.data_table.setItem(row, 6, QTableWidgetItem("-"))  # 报警阈值列

    def update_stats_table(self):
        """更新统计数据表格(最大值、最小值、平均值)"""

        data_series = [
            self.vib_speed_x, self.vib_speed_y, self.vib_speed_z,
            self.vib_angle_x, self.vib_angle_y, self.vib_angle_z,
            self.vib_disp_x, self.vib_disp_y, self.vib_disp_z,
            self.vib_freq_x, self.vib_freq_y, self.vib_freq_z
        ]

        for i, series in enumerate(data_series):
            if series:  # 确保序列不为空
                max_val = max(series)
                min_val = min(series)
                avg_val = sum(series) / len(series)

                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{max_val:.2f}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{min_val:.2f}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{avg_val:.2f}"))
            else:  # 如果数据序列为空,则填入"-"
                self.stats_table.setItem(i, 1, QTableWidgetItem("-"))
                self.stats_table.setItem(i, 2, QTableWidgetItem("-"))
                self.stats_table.setItem(i, 3, QTableWidgetItem("-"))


    def update_plots(self):
        # 更新图表(这部分代码放在定时器中,以更平滑的频率更新)
        self.speed_x_curve.setData(self.timestamps, self.vib_speed_x)
        self.speed_y_curve.setData(self.timestamps, self.vib_speed_y)
        self.speed_z_curve.setData(self.timestamps, self.vib_speed_z)
        self.angle_x_curve.setData(self.timestamps, self.vib_angle_x)
        self.angle_y_curve.setData(self.timestamps, self.vib_angle_y)
        self.angle_z_curve.setData(self.timestamps, self.vib_angle_z)
        self.disp_x_curve.setData(self.timestamps, self.vib_disp_x)
        self.disp_y_curve.setData(self.timestamps, self.vib_disp_y)
        self.disp_z_curve.setData(self.timestamps, self.vib_disp_z)
        self.freq_x_curve.setData(self.timestamps, self.vib_freq_x)
        self.freq_y_curve.setData(self.timestamps, self.vib_freq_y)
        self.freq_z_curve.setData(self.timestamps, self.vib_freq_z)

    def closeEvent(self, event):
        self.data_thread.stop()  # 确保数据采集线程在窗口关闭前停止
        self.device.stopLoopRead()
        self.device.closeDevice()
        super().closeEvent(event)

def main():
    try:
        # 初始化设备
        print("尝试连接设备 COM5, 波特率 230400...")
        device = device_model.DeviceModel("测试设备", "COM5", 230400, 0x50)
        device.openDevice()
        print("设备连接成功!")
        device.startLoopRead()
        print("开始数据轮询...")

        # 创建应用和窗口
        app = QApplication(sys.argv)
        window = VibrationMonitor(device)
        window.show()

        # 运行应用
        sys.exit(app.exec_())

    except Exception as e:
        print(f"错误:{str(e)}")
    finally:
        if 'device' in locals():
            device.stopLoopRead()
            device.closeDevice()

if __name__ == '__main__':
    main()

