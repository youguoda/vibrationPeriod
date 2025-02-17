import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QGridLayout, QGroupBox, QTableWidget,
                           QTableWidgetItem, QPushButton, QMessageBox, QTabWidget,
                           QComboBox) #新增 QTabWidget, QComboBox
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt
from PyQt5.QtGui import QPalette, QColor, QFont, QBrush
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import device_model  # 假设这是你的设备模型
import time
import csv
from scipy.fft import fft, fftfreq # 新增


# DataRecorder 类, 处理CSV文件写入 (保持不变,但会记录加速度)
class DataRecorder:
    def __init__(self, device):
        self.device = device
        self.filename = None
        self.file = None
        self.writer = None
        self.is_recording = False

    def start_recording(self):
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = f'vibration_data_{current_time}.csv'
        try:
            self.file = open(self.filename, 'w', newline='', encoding='utf-8-sig')
            self.writer = csv.writer(self.file)
            # 调整列名
            self.writer.writerow([
                '记录时间', '设备名称',
                '加速度X(g)', '加速度Y(g)', '加速度Z(g)',
                '角速度X(°/s)', '角速度Y(°/s)', '角速度Z(°/s)',
                'X轴振动速度(mm/s)', 'Y轴振动速度(mm/s)', 'Z轴振动速度(mm/s)',
                'X轴振动位移(um)', 'Y轴振动位移(um)', 'Z轴振动位移(um)',
                'X轴振动频率(Hz)', 'Y轴振动频率(Hz)', 'Z轴振动频率(Hz)',
                '温度(°C)'  # 移除片上时间
            ])
            self.is_recording = True
            print(f"开始记录数据到文件: {self.filename}")
            return True
        except Exception as e:
            print(f"创建CSV文件失败: {e}")
            return False

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.file:
                self.file.close()
            self.writer = None
            print(f"数据已保存到文件: {self.filename}")

    def write_data(self, data_values):
        if self.is_recording and self.writer:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            data_row = [
                timestamp,
                self.device.deviceName,
            ] + [str(v) if v is not None else "" for v in data_values]
            try:
                self.writer.writerow(data_row)
                self.file.flush()  # 立即写入文件
            except Exception as e:
                print(f"写入CSV数据失败: {e}")

# --- AnalysisWindow 类 (新的高级分析窗口) ---
class AnalysisWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级数据分析")
        self.setGeometry(200, 200, 800, 600)
        self.main_data_cache = {}  # 用于存储从主窗口传递来的数据
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 1. FFT 分析选项卡
        self.fft_tab = QWidget()
        self.tab_widget.addTab(self.fft_tab, "FFT 分析")
        self.setup_fft_tab()
        
        # 2. 趋势预测选项卡 (预留)
        self.trend_tab = QWidget()
        self.tab_widget.addTab(self.trend_tab, "趋势预测")
        # 在这里添加趋势预测相关的控件和布局

        # 3. 其他分析选项卡 (预留)
        # 可以根据需要添加更多选项卡

    def setup_fft_tab(self):
        fft_layout = QVBoxLayout(self.fft_tab)

        # 参数选择 (例如选择哪个轴、哪个参数进行FFT分析)
        param_layout = QHBoxLayout()
        param_label = QLabel("选择参数:")
        self.param_combo = QComboBox()
        #参数列表与主窗口保持一致
        self.param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度'      # 假设你也需要温度的统计信息,虽然只有一个值
        ])

        param_layout.addWidget(param_label)
        param_layout.addWidget(self.param_combo)
        fft_layout.addLayout(param_layout)


        # FFT 图表
        self.fft_plot = pg.PlotWidget()
        self.fft_plot.setBackground('w')
        self.fft_plot.showGrid(x=True, y=True, alpha=0.3)
        self.fft_plot.setLabel('left', "幅度")
        self.fft_plot.setLabel('bottom', "频率", units='Hz')
        self.fft_curve = self.fft_plot.plot(pen=pg.mkPen('b', width=2))  # 默认蓝色
        fft_layout.addWidget(self.fft_plot)

        # 分析按钮
        analyze_button = QPushButton("进行 FFT 分析")
        analyze_button.clicked.connect(self.perform_fft)
        fft_layout.addWidget(analyze_button)


    def perform_fft(self):
        #选择的数据序列
        selected_param = self.param_combo.currentText()
        if selected_param not in self.main_data_cache:
            QMessageBox.warning(self, "警告", "没有选择数据,请先返回主界面采集")
            return
        time_data = self.main_data_cache.get("timestamps")
        series_data = self.main_data_cache.get(selected_param)

        if not time_data or not series_data:
             QMessageBox.warning(self,"警告","数据不足,请返回主界面采集")
             return

        #进行FFT
        N = len(series_data)
        if N == 0:
            QMessageBox.warning(self, "警告", "没有数据可供分析！")
            return

        yf = fft(series_data)
        xf = fftfreq(N, time_data[1] - time_data[0])

        #只取正频率部分
        xf_pos = xf[:N//2]
        yf_pos = np.abs(yf[0:N//2])

        self.fft_curve.setData(xf_pos,yf_pos)


    def receive_data_from_main(self, data_cache):
        """接收来自主窗口的数据"""
        self.main_data_cache = data_cache
        # 更新参数选择下拉框 (可选)
        # keys = list(data_cache.keys())
        # self.param_combo.clear()
        # self.param_combo.addItems(keys)
class DataSignal(QThread):
    data_signal = pyqtSignal(dict)

    def __init__(self, device):
        super().__init__()
        self.device = device
        self._running = True

    def run(self):
        while self._running:
            try:
                # 获取所有数据 (现在包含加速度)
                data_values = {
                    "52": self.device.get("52"),  # 加速度X
                    "53": self.device.get("53"),  # 加速度Y
                    "54": self.device.get("54"),  # 加速度Z
                    "55": self.device.get("55"),  # 角速度X
                    "56": self.device.get("56"),  # 角速度Y
                    "57": self.device.get("57"),  # 角速度Z
                    "58": self.device.get("58"), #振动速度x
                    "59": self.device.get("59"), #振动速度y
                    "60": self.device.get("60"), #振动速度z
                    "61": self.device.get("61"),
                    "62": self.device.get("62"),
                    "63": self.device.get("63"),
                    "65": self.device.get("65"), #振动位移x
                    "66": self.device.get("66"), #振动位移y
                    "67": self.device.get("67"), #振动位移z
                    "68": self.device.get("68"), #振动频率x
                    "69": self.device.get("69"), #振动频率
                    "70": self.device.get("70"), #振动频率z
                    "64": self.device.get("64"),  # 温度
                }
                self.data_signal.emit(data_values)
                time.sleep(0.2)

            except Exception as e:
                print(f"Data acquisition error: {e}")
                if not self.device.isOpen:
                    print("Device disconnected")
                    break
    def stop(self):
          self._running = False
          self.wait()


# --- VibrationMonitor 类 (修改后的主窗口) ---
class VibrationMonitor(QMainWindow):
    data_to_analysis = pyqtSignal(dict)  # 用于向分析窗口传递数据的信号

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
        # 加速度数据
        self.accel_x = []
        self.accel_y = []
        self.accel_z = []
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
         # 温度数据
        self.temperature_data = []
        # 上次更新时间
        self.last_timestamp = 0

        # 更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # 50毫秒更新一次

        # 记录器
        self.recorder = DataRecorder(self.device)

        #  报警阈值字典(添加加速度阈值)
        self.thresholds = {
            'accel_x': 2.0, 'accel_y': 2.0, 'accel_z': 2.5,
            'speed_x': 20.0, 'speed_y': 20.0, 'speed_z': 25.0,
            'disp_x': 100.0, 'disp_y': 100.0, 'disp_z': 150.0,
            'freq_x': 55.0,  'freq_y': 55.0,  'freq_z': 65.0,
            'temperature':50.0
        }

        # 创建高级分析窗口的实例
        self.analysis_window = AnalysisWindow()
        self.data_to_analysis.connect(self.analysis_window.receive_data_from_main)

    def create_plot_widget(self, title, y_label, y_units):
        plot = pg.PlotWidget(title=title)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setLabel('left', y_label, units=y_units)
        plot.setLabel('bottom', '时间 (s)')
        plot.addLegend()
        plot.setTitle(title, size='12pt', color='k')
        plot.getAxis('bottom').setPen('k')
        plot.getAxis('left').setPen('k')
        plot.getAxis('bottom').setTextPen('k')
        plot.getAxis('left').setTextPen('k')
        return plot

    def init_ui(self):
        self.setWindowTitle('振动监测系统')
        self.setGeometry(100, 100, 1600, 900)

        # 设置应用样式 (保持不变)
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
                border: 1px solid #cccccc;
                alternate-background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #cccccc;
            }
            QPushButton {
                font-size: 10pt;
                color: #333333;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
                # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建网格布局
        grid_layout = QGridLayout()

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

        # 2. 加速度图 (替换原来的振动角度图)
        accel_group = QGroupBox("加速度")
        accel_layout = QVBoxLayout()
        self.accel_plot = self.create_plot_widget('', '加速度', 'g')  # 使用 'g' 作为单位
        self.accel_x_curve = self.accel_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.accel_y_curve = self.accel_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.accel_z_curve = self.accel_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        accel_layout.addWidget(self.accel_plot)
        accel_group.setLayout(accel_layout)
        grid_layout.addWidget(accel_group, 0, 1)  # 放置在原来的角度图位置


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

        # 创建表格和按钮的水平布局
        table_button_layout = QHBoxLayout()

        # 创建表格布局
        table_layout = QHBoxLayout()

        # 创建实时数据表格 (列数和表头改变)
        self.data_table = QTableWidget()
        self.data_table.setMinimumWidth(1100)  # 调整最小宽度
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['参数', 'X轴', 'Y轴', 'Z轴', '单位', '状态', '报警阈值'])
        self.data_table.setRowCount(5)  # 5行数据,添加加速度
        self.data_table.setItem(0, 0, QTableWidgetItem('加速度'))  # 加速度行
        self.data_table.setItem(1, 0, QTableWidgetItem('振动速度'))
        self.data_table.setItem(2, 0, QTableWidgetItem('振动位移'))
        self.data_table.setItem(3, 0, QTableWidgetItem('振动频率'))
        self.data_table.setItem(4, 0, QTableWidgetItem('温度'))
        self.data_table.setItem(0, 4, QTableWidgetItem('g'))    # 加速度单位
        self.data_table.setItem(1, 4, QTableWidgetItem('mm/s'))
        self.data_table.setItem(2, 4, QTableWidgetItem('μm'))
        self.data_table.setItem(3, 4, QTableWidgetItem('Hz'))
        self.data_table.setItem(4, 4, QTableWidgetItem('°C'))  # 温度单位
        self.data_table.setColumnWidth(0, 90)
        self.data_table.setColumnWidth(1, 70)
        self.data_table.setColumnWidth(2, 70)
        self.data_table.setColumnWidth(3, 70)
        self.data_table.setColumnWidth(4, 60)
        self.data_table.setColumnWidth(5, 85)
        self.data_table.setColumnWidth(6, 85)
        self.data_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.data_table)        # 创建统计表格 (行数改变,添加加速度的统计)
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(['参数', '最大值', '最小值', '平均值'])
        self.stats_table.setRowCount(15)  # 5个参数 * 3个轴 = 15 (添加了加速度)

        stats_params = [
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度','',''       # 假设你也需要温度的统计信息,虽然只有一个值
        ]
        for i, param in enumerate(stats_params):
            self.stats_table.setItem(i, 0, QTableWidgetItem(param))

        self.stats_table.setColumnWidth(0, 80)
        self.stats_table.setColumnWidth(1, 80)
        self.stats_table.setColumnWidth(2, 80)
        self.stats_table.setColumnWidth(3, 80)
        self.stats_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.stats_table)

        # 将实时表格和统计表格添加到水平布局
        table_button_layout.addLayout(table_layout)

        # 创建一个垂直布局来放置按钮
        button_layout = QVBoxLayout()

        # 添加开始/停止记录按钮
        self.record_button = QPushButton("开始记录")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)

          # 添加 "高级分析" 按钮
        self.analysis_button = QPushButton("高级分析")
        self.analysis_button.clicked.connect(self.open_analysis_window)
        button_layout.addWidget(self.analysis_button)

        # 添加一个弹性的间隔, 将按钮推到顶部
        button_layout.addStretch()

        # 将按钮布局添加到表格和按钮的水平布局
        table_button_layout.addLayout(button_layout)

        # 将表格和按钮的水平布局添加到主布局
        main_layout.addLayout(table_button_layout)

    def safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def update_data(self, data_values):
      try:
        # 获取加速度数据
        accel_x = self.safe_float(data_values.get("52"))
        accel_y = self.safe_float(data_values.get("53"))
        accel_z = self.safe_float(data_values.get("54"))
        # 获取其他数据
        vib_x = self.safe_float(data_values.get("58"))
        vib_y = self.safe_float(data_values.get("59"))
        vib_z = self.safe_float(data_values.get("60"))

        disp_x = self.safe_float(data_values.get("65"))
        disp_y = self.safe_float(data_values.get("66"))
        disp_z = self.safe_float(data_values.get("67"))
        freq_x = self.safe_float(data_values.get("68"))
        freq_y = self.safe_float(data_values.get("69"))
        freq_z = self.safe_float(data_values.get("70"))
        temp = self.safe_float(data_values.get("64"))  # 温度

        # 更新时间戳
        current_time = datetime.now().timestamp()
        if self.timestamps:
            time_diff = current_time - self.last_timestamp
            self.timestamps.append(self.timestamps[-1] + time_diff)
        else:
            self.timestamps.append(0)
        self.last_timestamp = current_time

        # 如果正在记录数据,则写入CSV
        if self.recorder.is_recording:

            record_data = [
                accel_x, accel_y, accel_z, #加速度
                data_values.get("55"), data_values.get("56"), data_values.get("57"),  # 角速度
                vib_x, vib_y, vib_z,  # 振动速度
                disp_x, disp_y, disp_z,  # 振动位移
                freq_x, freq_y, freq_z,  # 振动频率
                temp  # 温度
            ]
            self.recorder.write_data(record_data)


        # 更新数据列表 (加速度)
        self.accel_x.append(accel_x)
        self.accel_y.append(accel_y)
        self.accel_z.append(accel_z)

        self.vib_speed_x.append(vib_x)
        self.vib_speed_y.append(vib_y)
        self.vib_speed_z.append(vib_z)

        self.vib_disp_x.append(disp_x)
        self.vib_disp_y.append(disp_y)
        self.vib_disp_z.append(disp_z)
        self.vib_freq_x.append(freq_x)
        self.vib_freq_y.append(freq_y)
        self.vib_freq_z.append(freq_z)
        self.temperature_data.append(temp)


         # 限制数据长度
        if len(self.timestamps) > self.data_length:
            self.timestamps.pop(0)
            self.accel_x.pop(0)
            self.accel_y.pop(0)
            self.accel_z.pop(0)
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
        self.update_data_table(accel_x,accel_y,accel_z,vib_x, vib_y, vib_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z,temp)
        self.update_stats_table()

      except Exception as e:
        print(f"Error updating data: {e}")

    def update_data_table(self, accel_x,accel_y,accel_z,vib_x, vib_y, vib_z, disp_x, disp_y, disp_z, freq_x, freq_y, freq_z,temp):
      """更新实时数据表格"""
      # 设置加速度的值
      self.data_table.setItem(0, 1, QTableWidgetItem(f"{accel_x:.2f}"))
      self.data_table.setItem(0, 2, QTableWidgetItem(f"{accel_y:.2f}"))
      self.data_table.setItem(0, 3, QTableWidgetItem(f"{accel_z:.2f}"))
      # 设置表格其他值
      self.data_table.setItem(1, 1, QTableWidgetItem(f"{vib_x:.2f}"))
      self.data_table.setItem(1, 2, QTableWidgetItem(f"{vib_y:.2f}"))
      self.data_table.setItem(1, 3, QTableWidgetItem(f"{vib_z:.2f}"))
      self.data_table.setItem(2, 1, QTableWidgetItem(f"{disp_x:.2f}"))
      self.data_table.setItem(2, 2, QTableWidgetItem(f"{disp_y:.2f}"))
      self.data_table.setItem(2, 3, QTableWidgetItem(f"{disp_z:.2f}"))
      self.data_table.setItem(3, 1, QTableWidgetItem(f"{freq_x:.2f}"))
      self.data_table.setItem(3, 2, QTableWidgetItem(f"{freq_y:.2f}"))
      self.data_table.setItem(3, 3, QTableWidgetItem(f"{freq_z:.2f}"))
      self.data_table.setItem(4, 1, QTableWidgetItem(f"{temp:.2f}")) #温度


        # 报警逻辑 (添加加速度)
      data = [
          ('accel_x', accel_x), ('accel_y', accel_y), ('accel_z', accel_z),
          ('speed_x', vib_x), ('speed_y', vib_y), ('speed_z', vib_z),
          ('disp_x', disp_x), ('disp_y', disp_y), ('disp_z', disp_z),
          ('freq_x', freq_x), ('freq_y', freq_y), ('freq_z', freq_z),
          ('temperature',temp)
      ]

      for row_index in range(5):  # 循环所有行(包括加速度)
        # 温度报警逻辑在循环外单独处理
        if row_index == 4:
          threshold = self.thresholds.get('temperature')
          status_item = QTableWidgetItem()
          # 温度单独处理,只有一列数据
          if threshold is not None and temp > threshold:
              status_item.setText('报警')
              status_item.setBackground(QBrush(QColor(255,0,0)))
          else:
            status_item.setText('正常')
            status_item.setBackground(QBrush(QColor(255,255,255)))
          self.data_table.setItem(4,5,status_item)
          self.data_table.setItem(row_index,6,QTableWidgetItem(str(threshold)if threshold is not None else '-'))
          continue

        # 其他参数报警逻辑
        for col_index in range(1, 4):

            data_key, data_value = data[(row_index * 3) + (col_index - 1)] #计算偏移
            threshold = self.thresholds.get(data_key)

            status_item = QTableWidgetItem()
            if threshold is not None and data_value > threshold:
                status_item.setText("报警")
                status_item.setBackground(QBrush(QColor(255, 0, 0)))
            else:
                status_item.setText("正常")
                status_item.setBackground(QBrush(QColor(255, 255, 255)))

            self.data_table.setItem(row_index, 5, status_item)
            self.data_table.setItem(row_index, 6, QTableWidgetItem(str(threshold) if threshold is not None else "-"))


    def update_stats_table(self):
            data_series = [
                self.accel_x, self.accel_y, self.accel_z,
                self.vib_speed_x, self.vib_speed_y, self.vib_speed_z,
                self.vib_disp_x, self.vib_disp_y, self.vib_disp_z,
                self.vib_freq_x, self.vib_freq_y, self.vib_freq_z,
                self.temperature_data
            ]
            for i, series in enumerate(data_series):
                if series:
                    max_val = max(series)
                    min_val = min(series)
                    avg_val = sum(series) / len(series)
                    self.stats_table.setItem(i,1,QTableWidgetItem(f"{max_val:.2f}"))
                    self.stats_table.setItem(i,2,QTableWidgetItem(f"{min_val:.2f}"))
                    self.stats_table.setItem(i,3,QTableWidgetItem(f"{avg_val:.2f}"))
                else:
                    self.stats_table.setItem(i, 1, QTableWidgetItem("-"))
                    self.stats_table.setItem(i, 2, QTableWidgetItem("-"))
                    self.stats_table.setItem(i, 3, QTableWidgetItem("-"))


    def update_plots(self):
            # 加速度曲线
            self.accel_x_curve.setData(self.timestamps, self.accel_x)
            self.accel_y_curve.setData(self.timestamps, self.accel_y)
            self.accel_z_curve.setData(self.timestamps, self.accel_z)
            # 其他曲线
            self.speed_x_curve.setData(self.timestamps, self.vib_speed_x)
            self.speed_y_curve.setData(self.timestamps, self.vib_speed_y)
            self.speed_z_curve.setData(self.timestamps, self.vib_speed_z)
            self.disp_x_curve.setData(self.timestamps, self.vib_disp_x)
            self.disp_y_curve.setData(self.timestamps, self.vib_disp_y)
            self.disp_z_curve.setData(self.timestamps, self.vib_disp_z)
            self.freq_x_curve.setData(self.timestamps, self.vib_freq_x)
            self.freq_y_curve.setData(self.timestamps, self.vib_freq_y)
            self.freq_z_curve.setData(self.timestamps, self.vib_freq_z)

    def open_analysis_window(self):
        """打开高级分析窗口,并传递数据"""
        data_cache = {
            'timestamps': self.timestamps.copy(),
            '加速度X': self.accel_x.copy(),
            '加速度Y': self.accel_y.copy(),
            '加速度Z': self.accel_z.copy(),
            '速度X': self.vib_speed_x.copy(),
            '速度Y': self.vib_speed_y.copy(),
            '速度Z': self.vib_speed_z.copy(),
            '位移X': self.vib_disp_x.copy(),
            '位移Y': self.vib_disp_y.copy(),
            '位移Z': self.vib_disp_z.copy(),
            '频率X': self.vib_freq_x.copy(),
            '频率Y': self.vib_freq_y.copy(),
            '频率Z': self.vib_freq_z.copy(),
            '温度':self.temperature_data.copy()

        }
        self.data_to_analysis.emit(data_cache)  # 发送数据
        self.analysis_window.show()

    def toggle_recording(self):
        if self.recorder.is_recording:
            reply = QMessageBox.question(self, '停止记录', '确定要停止记录数据吗?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.recorder.stop_recording()
                self.record_button.setText("开始记录")
        else:
            if self.recorder.start_recording():
                self.record_button.setText("停止记录")

    def closeEvent(self, event):
        self.data_thread.stop()
        self.recorder.stop_recording()  # 停止记录
        self.device.stopLoopRead()
        self.device.closeDevice()
        self.analysis_window.close() # 关闭分析窗口
        super().closeEvent(event)
# 其余部分代码与之前相同 (DataRecorder, DataSignal, main 函数) ...

#重用之前的DataRecorder 和 DataSignal 类

def main():
    try:
        # 初始化设备
        print("尝试连接设备 COM5, 波特率 230400...")
        device = device_model.DeviceModel("测试设备", "COM5", 230400, 0x50)  # 示例,请根据你的设备修改
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
        # 确保在程序退出时关闭设备连接和停止轮询
        if 'device' in locals():
            device.stopLoopRead()
            device.closeDevice()

if __name__ == '__main__':
    main()

