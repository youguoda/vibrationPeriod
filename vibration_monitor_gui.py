import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QGridLayout, QGroupBox, QTableWidget,
                           QTableWidgetItem)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QPalette, QColor, QFont, QBrush
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import device_model
import time


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
                    "65": self.device.get("65"),
                    "66": self.device.get("66"),
                    "67": self.device.get("67"),
                    "68": self.device.get("68"),
                    "69": self.device.get("69"),
                    "70": self.device.get("70"),
                }

                self.data_signal.emit(data_values)
                time.sleep(0.2)  # 控制数据刷新的间隔
            except Exception as e:
                print(f"Data acquisition error: {e}")
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
        self.data_length = 500
        self.timestamps = []

        # 振动速度数据
        self.vib_speed_x = []
        self.vib_speed_y = []
        self.vib_speed_z = []

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
        self.timer.start(50)  # 50毫秒更新一次图表

        #  报警阈值字典 (根据实际情况调整这些值)
        self.thresholds = {
            'speed_x': 20.0, 'speed_y': 20.0, 'speed_z': 25.0,  # 速度阈值
            'disp_x': 100.0, 'disp_y': 100.0, 'disp_z': 150.0, # 位移阈值
            'freq_x': 55.0,  'freq_y': 55.0,  'freq_z': 65.0   # 频率阈值
        }

    def create_plot_widget(self, title, y_label, y_units):
        """创建统一样式的图表部件"""
        plot = pg.PlotWidget(title=title)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)  # 显示网格
        plot.setLabel('left', y_label, units=y_units)  # 设置左侧坐标轴标签和单位
        plot.setLabel('bottom', '时间 (s)')  # 设置下方坐标轴标签
        plot.addLegend()  # 添加图例

        # 设置标题样式
        plot.setTitle(title, size='12pt', color='k')

        # 设置坐标轴样式
        plot.getAxis('bottom').setPen('k')  # 坐标轴颜色
        plot.getAxis('left').setPen('k')
        plot.getAxis('bottom').setTextPen('k')  # 坐标轴文本颜色
        plot.getAxis('left').setTextPen('k')

        return plot

    def init_ui(self):
        self.setWindowTitle('振动监测系统')
        self.setGeometry(100, 100, 1400, 900)  # 调整窗口大小

        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;  /* 浅灰色背景 */
            }
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #cccccc;  /* 较浅的边框颜色 */
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QLabel {
                font-size: 10pt;
                color: #333333;  /* 深灰色字体 */
            }
            QTableWidget {
                font-size: 10pt;
                color: #333333;
                gridline-color: #cccccc;
                border: 1px solid #cccccc;
                alternate-background-color: #f5f5f5; /* 交替行颜色 */
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

        # 第1行第1列: 振动速度图
        speed_group = QGroupBox("振动速度")
        speed_layout = QVBoxLayout()
        self.speed_plot = self.create_plot_widget('', '速度', 'mm/s')
        self.speed_x_curve = self.speed_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.speed_y_curve = self.speed_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.speed_z_curve = self.speed_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        speed_layout.addWidget(self.speed_plot)
        speed_group.setLayout(speed_layout)
        grid_layout.addWidget(speed_group, 0, 0)

        # 第1行第2列: 振动位移图
        disp_group = QGroupBox("振动位移")
        disp_layout = QVBoxLayout()
        self.disp_plot = self.create_plot_widget('', '位移', 'μm')
        self.disp_x_curve = self.disp_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.disp_y_curve = self.disp_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.disp_z_curve = self.disp_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        disp_layout.addWidget(self.disp_plot)
        disp_group.setLayout(disp_layout)
        grid_layout.addWidget(disp_group, 0, 1)

        # 第2行第1列: 振动频率图
        freq_group = QGroupBox("振动频率")
        freq_layout = QVBoxLayout()
        self.freq_plot = self.create_plot_widget('', '频率', 'Hz')
        self.freq_x_curve = self.freq_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.freq_y_curve = self.freq_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.freq_z_curve = self.freq_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        freq_layout.addWidget(self.freq_plot)
        freq_group.setLayout(freq_layout)
        grid_layout.addWidget(freq_group, 1, 0)

        # 将网格布局添加到主布局
        main_layout.addLayout(grid_layout)

        # 创建表格布局
        table_layout = QHBoxLayout()

        # 实时数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['参数', 'X轴', 'Y轴', 'Z轴', '单位', '状态', '报警阈值'])
        self.data_table.setRowCount(3)
        self.data_table.setItem(0, 0, QTableWidgetItem('振动速度'))
        self.data_table.setItem(1, 0, QTableWidgetItem('振动位移'))
        self.data_table.setItem(2, 0, QTableWidgetItem('振动频率'))
        self.data_table.setItem(0, 4, QTableWidgetItem('mm/s'))
        self.data_table.setItem(1, 4, QTableWidgetItem('μm'))
        self.data_table.setItem(2, 4, QTableWidgetItem('Hz'))
		# 调整实时数据表格的列宽
        self.data_table.setColumnWidth(0, 90)   
        self.data_table.setColumnWidth(1, 70)   
        self.data_table.setColumnWidth(2, 70)   
        self.data_table.setColumnWidth(3, 70)   
        self.data_table.setColumnWidth(4, 60)   
        self.data_table.setColumnWidth(5, 85)   
        self.data_table.setColumnWidth(6, 85)
        self.data_table.setAlternatingRowColors(True)  # 开启交替行颜色
        table_layout.addWidget(self.data_table)

        # 统计数据表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(['参数', '最大值', '最小值', '平均值'])
        self.stats_table.setRowCount(9)

        stats_params = [
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z'
        ]
        for i, param in enumerate(stats_params):
            self.stats_table.setItem(i, 0, QTableWidgetItem(param))

        self.stats_table.setColumnWidth(0, 80)
        self.stats_table.setColumnWidth(1, 80)
        self.stats_table.setColumnWidth(2, 80)
        self.stats_table.setColumnWidth(3, 80)
        self.stats_table.setAlternatingRowColors(True)  # 开启交替行颜色
        table_layout.addWidget(self.stats_table)


        # 将表格布局添加到主布局
        main_layout.addLayout(table_layout)


    def safe_float(self, value, default=0.0):
        """安全地将值转换为浮点数,如果转换失败则返回默认值"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def update_data(self, data_values):
        """更新数据"""
        try:
            # 获取数据并转换为浮点数
            vib_x = self.safe_float(data_values.get("58"))
            vib_y = self.safe_float(data_values.get("59"))
            vib_z = self.safe_float(data_values.get("60"))
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
                self.timestamps.append(self.timestamps[-1] + time_diff)  # 累加时间
            else:
                self.timestamps.append(0)  # 第一次为0
            self.last_timestamp = current_time

            # 更新数据列表
            self.vib_speed_x.append(vib_x)
            self.vib_speed_y.append(vib_y)
            self.vib_speed_z.append(vib_z)
            self.vib_disp_x.append(disp_x)
            self.vib_disp_y.append(disp_y)
            self.vib_disp_z.append(disp_z)
            self.vib_freq_x.append(freq_x)
            self.vib_freq_y.append(freq_y)
            self.vib_freq_z.append(freq_z)

            # 限制数据长度
            if len(self.timestamps) > self.data_length:
                self.timestamps.pop(0)
                self.vib_speed_x.pop(0)
                self.vib_speed_y.pop(0)
                self.vib_speed_z.pop(0)
                self.vib_disp_x.pop(0)
                self.vib_disp_y.pop(0)
                self.vib_disp_z.pop(0)
                self.vib_freq_x.pop(0)
                self.vib_freq_y.pop(0)
                self.vib_freq_z.pop(0)

            # 更新实时数据表格和统计数据表格
            self.update_data_table(vib_x, vib_y, vib_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z)
            self.update_stats_table()

        except Exception as e:
            print(f"Error updating data: {e}")

    def update_data_table(self, vib_x, vib_y, vib_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z):
        """更新实时数据表格"""
        # 设置表格的值
        self.data_table.setItem(0, 1, QTableWidgetItem(f"{vib_x:.2f}"))
        self.data_table.setItem(0, 2, QTableWidgetItem(f"{vib_y:.2f}"))
        self.data_table.setItem(0, 3, QTableWidgetItem(f"{vib_z:.2f}"))
        self.data_table.setItem(1, 1, QTableWidgetItem(f"{disp_x:.2f}"))
        self.data_table.setItem(1, 2, QTableWidgetItem(f"{disp_y:.2f}"))
        self.data_table.setItem(1, 3, QTableWidgetItem(f"{disp_z:.2f}"))
        self.data_table.setItem(2, 1, QTableWidgetItem(f"{freq_x:.2f}"))
        self.data_table.setItem(2, 2, QTableWidgetItem(f"{freq_y:.2f}"))
        self.data_table.setItem(2, 3, QTableWidgetItem(f"{freq_z:.2f}"))

        #  报警逻辑
        data = [
            ('speed_x', vib_x), ('speed_y', vib_y), ('speed_z', vib_z),
            ('disp_x', disp_x), ('disp_y', disp_y), ('disp_z', disp_z),
            ('freq_x', freq_x), ('freq_y', freq_y), ('freq_z', freq_z)
        ]

        for row_index in range(3):  # 遍历每一行 (速度、位移、频率)
            for col_index in range(1, 4):  # 遍历每一列 (X、Y、Z)
                data_key, data_value = data[(row_index * 3) + (col_index - 1)]  # 计算对应的数据键和值
                threshold = self.thresholds.get(data_key)  # 获取阈值

                status_item = QTableWidgetItem()  # 创建一个状态项
                if threshold is not None and data_value > threshold:
                    status_item.setText("报警")
                    status_item.setBackground(QBrush(QColor(255, 0, 0)))  # 设置为红色背景
                   # status_item.setForeground(QBrush(QColor(255, 255, 255))) # 将报警文字设置为白色
                else:
                    status_item.setText("正常")
                    # 如果你想在正常状态下也设置背景颜色, 可以取消下面这行注释
                    status_item.setBackground(QBrush(QColor(255, 255, 255)))  # 正常状态,恢复白色背景

                self.data_table.setItem(row_index, 5, status_item) # 设置"状态"列
                self.data_table.setItem(row_index, 6, QTableWidgetItem(str(threshold) if threshold is not None else "-")) # 设置报警阈值

    def update_stats_table(self):
        """更新统计数据表格"""
        data_series = [
            self.vib_speed_x, self.vib_speed_y, self.vib_speed_z,
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
        """更新图表"""
        self.speed_x_curve.setData(self.timestamps, self.vib_speed_x)
        self.speed_y_curve.setData(self.timestamps, self.vib_speed_y)
        self.speed_z_curve.setData(self.timestamps, self.vib_speed_z)
        self.disp_x_curve.setData(self.timestamps, self.vib_disp_x)
        self.disp_y_curve.setData(self.timestamps, self.vib_disp_y)
        self.disp_z_curve.setData(self.timestamps, self.vib_disp_z)
        self.freq_x_curve.setData(self.timestamps, self.vib_freq_x)
        self.freq_y_curve.setData(self.timestamps, self.vib_freq_y)
        self.freq_z_curve.setData(self.timestamps, self.vib_freq_z)

    def closeEvent(self, event):
        """关闭窗口事件"""
        self.data_thread.stop()
        self.device.stopLoopRead()
        self.device.closeDevice()
        super().closeEvent(event)


def main():
    try:
        # 初始化设备 (使用你的设备参数)
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
        print(f"错误: {str(e)}")
    finally:
        if 'device' in locals():  # 确保设备被正确关闭
            device.stopLoopRead()
            device.closeDevice()

if __name__ == '__main__':
    main()
