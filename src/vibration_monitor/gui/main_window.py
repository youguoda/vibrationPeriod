from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGridLayout, QGroupBox, QTableWidget,
                             QTableWidgetItem, QPushButton, QMessageBox, QFileDialog)  # 添加 QFileDialog
from PyQt5.QtCore import QTimer, Qt, QEvent
from PyQt5.QtGui import QBrush, QColor
import pyqtgraph as pg
import numpy as np
from datetime import datetime
import csv  # 添加 csv 模块导入
from ..device.device_model import DeviceModel  # 导入 DeviceModel 基类
from ..data_recorder import DataRecorder #导入数据记录
from ..utils.data_utils import safe_float
from ..utils.signal import Signal
from .analysis_window import AnalysisWindow #导入分析窗口
from ..config import Config
from ..utils.logger import setup_logger
from ..utils.collector_server import SocketMaster  # 导入 SocketMaster 类
from ..utils.SignalManager import signalManager  # 导入 SocketMaster 类
# 创建一个 logger 实例
logger = setup_logger(__name__)

class VibrationMonitorWindow(QMainWindow):
    """主窗口类"""
     # 自定义信号,用于向分析窗口传递数据
    data_to_analysis = Signal(dict)
    def __init__(self, device: DeviceModel):
        """
        初始化主窗口

        Args:
            device:  DeviceModel 对象
        """
        super().__init__()
        self.device = device
        self.config = Config()  # 加载配置

        # 从配置文件读取阈值
        self.thresholds = {
            'accel_x': self.config.getfloat('Thresholds', 'accel_x', fallback=2.0),
            'accel_y': self.config.getfloat('Thresholds', 'accel_y', fallback=2.0),
            'accel_z': self.config.getfloat('Thresholds', 'accel_z', fallback=2.5),
            'speed_x': self.config.getfloat('Thresholds', 'speed_x', fallback=20.0),
            'speed_y': self.config.getfloat('Thresholds', 'speed_y', fallback=20.0),
            'speed_z': self.config.getfloat('Thresholds', 'speed_z', fallback=25.0),
            'disp_x': self.config.getfloat('Thresholds', 'disp_x', fallback=100.0),
            'disp_y': self.config.getfloat('Thresholds', 'disp_y', fallback=100.0),
            'disp_z': self.config.getfloat('Thresholds', 'disp_z', fallback=150.0),
            'freq_x': self.config.getfloat('Thresholds', 'freq_x', fallback=55.0),
            'freq_y': self.config.getfloat('Thresholds', 'freq_y', fallback=55.0),
            'freq_z': self.config.getfloat('Thresholds', 'freq_z', fallback=65.0),
            'temperature': self.config.getfloat('Thresholds', 'temperature', fallback=50.0)
        }

        self.record_start_time = None  # 添加记录开始时间属性
        self.record_time_label = None  # 添加记录时间显示标签
        self.record_timer = QTimer()  # 添加计时器
        self.record_timer.timeout.connect(self.update_record_time)
        self.init_ui() #界面
         # 数据更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        update_interval = 50  # 更新间隔,为了显示流畅,可以适当调小
        self.update_timer.start(update_interval)
        # print(f"Debug: update_timer started: {self.update_timer.isActive()}")
        # 记录器
        self.recorder = DataRecorder(self.device)
        # 数据缓存
        self.data_length = self.config.getint('Data', 'data_length', fallback=500)
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

           # 创建高级分析窗口的实例
        self.analysis_window = AnalysisWindow()
        self.data_to_analysis.connect(self.analysis_window.receive_data_from_main)
        self.master = None  # 主站连接
        self.set_master_socket()  # 设置主站连接

    def init_ui(self):
        """初始化用户界面"""
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
                font-size: 16pt;
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

        # 振动位移图
        disp_group = QGroupBox("振动位移")
        disp_layout = QVBoxLayout()
        self.disp_plot = self.create_plot_widget('', '位移', 'μm')
        self.disp_x_curve = self.disp_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.disp_y_curve = self.disp_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.disp_z_curve = self.disp_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        disp_layout.addWidget(self.disp_plot)
        disp_group.setLayout(disp_layout)
        grid_layout.addWidget(disp_group, 0, 0)

        # 振动速度图
        speed_group = QGroupBox("振动速度")
        speed_layout = QVBoxLayout()
        self.speed_plot = self.create_plot_widget('', '速度', 'mm/s')
        self.speed_x_curve = self.speed_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.speed_y_curve = self.speed_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.speed_z_curve = self.speed_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        speed_layout.addWidget(self.speed_plot)
        speed_group.setLayout(speed_layout)
        grid_layout.addWidget(speed_group, 0, 1)#

        # 加速度图
        accel_group = QGroupBox("加速度")
        accel_layout = QVBoxLayout()
        self.accel_plot = self.create_plot_widget('', '加速度', 'g')  # 使用 'g' 作为单位
        self.accel_x_curve = self.accel_plot.plot(pen=pg.mkPen('r', width=2), name='X轴')
        self.accel_y_curve = self.accel_plot.plot(pen=pg.mkPen('g', width=2), name='Y轴')
        self.accel_z_curve = self.accel_plot.plot(pen=pg.mkPen('b', width=2), name='Z轴')
        accel_layout.addWidget(self.accel_plot)
        accel_group.setLayout(accel_layout)
        grid_layout.addWidget(accel_group, 1, 0)  # 放置在原来的角度图位置

        # 振动频率图
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

        # 创建实时数据表格
        self.data_table = QTableWidget()
        self.data_table.setMinimumWidth(1100)
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['参数', 'X轴', 'Y轴', 'Z轴', '单位', '状态', '报警阈值'])
        self.data_table.setRowCount(5)  # 5行数据: 加速度、速度、位移、频率、温度
        self.data_table.setItem(0, 0, QTableWidgetItem('加速度'))
        self.data_table.setItem(1, 0, QTableWidgetItem('振动速度'))
        self.data_table.setItem(2, 0, QTableWidgetItem('振动位移'))
        self.data_table.setItem(3, 0, QTableWidgetItem('振动频率'))
        self.data_table.setItem(4, 0, QTableWidgetItem('温度'))
        self.data_table.setItem(0, 4, QTableWidgetItem('g'))
        self.data_table.setItem(1, 4, QTableWidgetItem('mm/s'))
        self.data_table.setItem(2, 4, QTableWidgetItem('μm'))
        self.data_table.setItem(3, 4, QTableWidgetItem('Hz'))
        self.data_table.setItem(4, 4, QTableWidgetItem('°C'))
        # 设置列宽
        self.data_table.setColumnWidth(0, 90)
        self.data_table.setColumnWidth(1, 70)
        self.data_table.setColumnWidth(2, 70)
        self.data_table.setColumnWidth(3, 70)
        self.data_table.setColumnWidth(4, 60)
        self.data_table.setColumnWidth(5, 85)
        self.data_table.setColumnWidth(6, 85)
        self.data_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.data_table)

        # 创建统计表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(['参数', '最大值', '最小值', '平均值'])
        self.stats_table.setRowCount(15)  # 5个参数 * 3个轴 = 15
        stats_params = [
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度','',''       # 温度只有一个值，所以这里填充两个空字符串
        ]
        for i, param in enumerate(stats_params):
            self.stats_table.setItem(i, 0, QTableWidgetItem(param))

        self.stats_table.setColumnWidth(0, 80)
        self.stats_table.setColumnWidth(1, 80)
        self.stats_table.setColumnWidth(2, 80)
        self.stats_table.setColumnWidth(3, 80)

        self.stats_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.stats_table)

        # 将表格添加到布局
        table_button_layout.addLayout(table_layout)

        # 创建按钮布局
        button_layout = QVBoxLayout()
        # 添加记录时间显示标签
        self.record_time_label = QLabel("记录时间: 00:00:00")
        self.record_time_label.setStyleSheet("font-size: 14pt; color: #333333;")
        button_layout.addWidget(self.record_time_label)
        # 添加开始/停止记录按钮
        self.record_button = QPushButton("开始记录")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)
        # 添加高级分析按钮
        self.analysis_button = QPushButton("高级分析")
        self.analysis_button.clicked.connect(self.open_analysis_window)
        button_layout.addWidget(self.analysis_button)
        # 在button_layout中添加导入数据按钮（在高级分析按钮之后）
        self.import_button = QPushButton("导入数据")
        self.import_button.clicked.connect(self.import_data)
        button_layout.addWidget(self.import_button)

        button_layout.addStretch()  # 添加弹性空间

        table_button_layout.addLayout(button_layout)

        # 将表格和按钮的布局添加到主布局
        main_layout.addLayout(table_button_layout)
        self.__init_slot()  # 初始化槽函数

    def __init_slot(self):
        signalManager.StartSignal.connect(self.toggle_recording)
        signalManager.StopSignal.connect(self.toggle_recording)
    
    def create_plot_widget(self, title, y_label, y_units):
        """创建绘图部件"""
        plot = pg.PlotWidget(title=title)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setLabel('left', y_label, units=y_units)
        plot.setLabel('bottom', '时间 (s)')
        plot.addLegend()
        plot.setTitle(title, size='12pt', color='k')  # 使用 HTML 样式
        # 设置坐标轴颜色为黑色
        plot.getAxis('bottom').setPen('k')
        plot.getAxis('left').setPen('k')
        # 设置坐标轴标签颜色
        plot.getAxis('bottom').setTextPen('k')
        plot.getAxis('left').setTextPen('k')
        return plot
    
    def update_record_time(self):
        """更新记录时间显示"""
        if self.record_start_time:
            elapsed = datetime.now() - self.record_start_time
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            seconds = elapsed.seconds % 60
            self.record_time_label.setText(f"记录时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def update_data(self):
        """更新数据 (由定时器触发)"""
        # print("Debug: update_data called") 
        try:
            # 获取数据
            accel_x = safe_float(self.device.get_data("52"))
            # print(f"Debug: accel_x = {accel_x}")
            accel_y = safe_float(self.device.get_data("53"))
            accel_z = safe_float(self.device.get_data("54"))
            vib_x = safe_float(self.device.get_data("58"))
            vib_y = safe_float(self.device.get_data("59"))
            vib_z = safe_float(self.device.get_data("60"))
            disp_x = safe_float(self.device.get_data("65"))
            disp_y = safe_float(self.device.get_data("66"))
            disp_z = safe_float(self.device.get_data("67"))
            freq_x = safe_float(self.device.get_data("68"))
            freq_y = safe_float(self.device.get_data("69"))
            freq_z = safe_float(self.device.get_data("70"))
            temp = safe_float(self.device.get_data("64"))

            # 更新时间戳
            current_time = datetime.now().timestamp()
            if self.timestamps:
                time_diff = current_time - self.last_timestamp
                self.timestamps.append(self.timestamps[-1] + time_diff)
            else:
                self.timestamps.append(0)
            self.last_timestamp = current_time

            # 记录数据 (如果正在记录)
            if self.recorder.is_recording:
              record_data = [
                  accel_x, accel_y, accel_z,  # 加速度
                  self.device.get_data("55"), self.device.get_data("56"), self.device.get_data("57"),  # 角速度
                  vib_x, vib_y, vib_z,  # 振动速度
                  disp_x, disp_y, disp_z,  # 振动位移
                  freq_x, freq_y, freq_z,  # 振动频率
                  temp  # 温度
              ]
              self.recorder.write_data(record_data)

            # 更新数据列表
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
                self.temperature_data.pop(0)  # 温度也pop

            # 更新表格
            self.update_data_table(accel_x, accel_y, accel_z, vib_x, vib_y, vib_z,
                                  disp_x, disp_y, disp_z, freq_x, freq_y, freq_z, temp)
            self.update_stats_table()

            # 更新绘图
            self.update_plots()

        except Exception as e:
                logger.exception(f"更新数据时发生错误: {e}")

    def update_data_table(self, accel_x, accel_y, accel_z, vib_x, vib_y, vib_z,
                          disp_x, disp_y, disp_z, freq_x, freq_y, freq_z, temp):
        """更新实时数据表格"""
        # 设置加速度数据
        self.data_table.setItem(0, 1, QTableWidgetItem(f"{accel_x:.2f}"))
        self.data_table.setItem(0, 2, QTableWidgetItem(f"{accel_y:.2f}"))
        self.data_table.setItem(0, 3, QTableWidgetItem(f"{accel_z:.2f}"))

        # 设置其他数据
        self.data_table.setItem(1, 1, QTableWidgetItem(f"{vib_x:.2f}"))
        self.data_table.setItem(1, 2, QTableWidgetItem(f"{vib_y:.2f}"))
        self.data_table.setItem(1, 3, QTableWidgetItem(f"{vib_z:.2f}"))
        self.data_table.setItem(2, 1, QTableWidgetItem(f"{disp_x:.2f}"))
        self.data_table.setItem(2, 2, QTableWidgetItem(f"{disp_y:.2f}"))
        self.data_table.setItem(2, 3, QTableWidgetItem(f"{disp_z:.2f}"))
        self.data_table.setItem(3, 1, QTableWidgetItem(f"{freq_x:.2f}"))
        self.data_table.setItem(3, 2, QTableWidgetItem(f"{freq_y:.2f}"))
        self.data_table.setItem(3, 3, QTableWidgetItem(f"{freq_z:.2f}"))
        self.data_table.setItem(4, 1, QTableWidgetItem(f"{temp:.2f}"))  # 温度

        # 报警逻辑
        data = [
          ('accel_x', accel_x), ('accel_y', accel_y), ('accel_z', accel_z),
          ('speed_x', vib_x), ('speed_y', vib_y), ('speed_z', vib_z),
          ('disp_x', disp_x), ('disp_y', disp_y), ('disp_z', disp_z),
          ('freq_x', freq_x), ('freq_y', freq_y), ('freq_z', freq_z),
          ('temperature',temp) #温度
        ]

        for row_index in range(5):  # 循环所有行
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
          for col_index in range(1, 4):
              data_key, data_value = data[(row_index * 3) + (col_index -1)] #通过计算偏移量来确定当前读取的元祖
              threshold = self.thresholds.get(data_key)

              status_item = QTableWidgetItem()
              if threshold is not None and data_value > threshold:
                  status_item.setText("报警")
                  status_item.setBackground(QBrush(QColor(255, 0, 0))) #红色
              else:
                  status_item.setText("正常")
                  status_item.setBackground(QBrush(QColor(255,255,255)))#白色
              self.data_table.setItem(row_index, 5, status_item)
              self.data_table.setItem(row_index, 6, QTableWidgetItem(str(threshold) if threshold is not None else "-"))

    def update_stats_table(self):
        """更新统计数据表格"""
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
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{max_val:.2f}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{min_val:.2f}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{avg_val:.2f}"))
            else:
                self.stats_table.setItem(i, 1, QTableWidgetItem("-"))
                self.stats_table.setItem(i, 2, QTableWidgetItem("-"))
                self.stats_table.setItem(i, 3, QTableWidgetItem("-"))

    def update_plots(self):
        """更新绘图"""
        self.accel_x_curve.setData(self.timestamps, self.accel_x)
        self.accel_y_curve.setData(self.timestamps, self.accel_y)
        self.accel_z_curve.setData(self.timestamps, self.accel_z)
        self.speed_x_curve.setData(self.timestamps, self.vib_speed_x)
        self.speed_y_curve.setData(self.timestamps, self.vib_speed_y)
        self.speed_z_curve.setData(self.timestamps, self.vib_speed_z)
        self.disp_x_curve.setData(self.timestamps, self.vib_disp_x)
        self.disp_y_curve.setData(self.timestamps, self.vib_disp_y)
        self.disp_z_curve.setData(self.timestamps, self.vib_disp_z)
        self.freq_x_curve.setData(self.timestamps, self.vib_freq_x)
        self.freq_y_curve.setData(self.timestamps, self.vib_freq_y)
        self.freq_z_curve.setData(self.timestamps, self.vib_freq_z)

    def toggle_recording(self):
    # 切换记录状态
        if self.recorder.is_recording:
            # reply = QMessageBox.question(self, '停止记录', '确定要停止记录数据吗?',
            #                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            # if reply == QMessageBox.Yes:
            self.recorder.stop_recording()
            self.record_button.setText("开始记录")
            self.record_timer.stop()  # 停止计时器
            self.record_start_time = None  # 重置开始时间
            self.record_time_label.setText("记录时间: 00:00:00")  # 重置显示
        else:
            if self.recorder.start_recording():
                self.record_button.setText("停止记录")
                self.record_start_time = datetime.now()  # 设置开始时间
                self.record_timer.start(1000)  # 启动计时器，每秒更新一次

    def open_analysis_window(self):
      """打开高级分析窗口"""

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
      self.data_to_analysis.emit(data_cache) #发送数据
      self.analysis_window.show()

    def set_master_socket(self):
        # 初始化socket主站连接
        def handle_message(msg):
            if msg == 'START':
                print("[采集] 开始采集数据")
                signalManager.StartSignal.emit()
            elif msg == 'STOP':
                print("[采集] 停止采集并分析数据")
                signalManager.StopSignal.emit()
            else:
                print(f"[采集] 收到未知指令: {msg}")
        self.master = SocketMaster(on_message=handle_message)
        self.master.start()
        logger.info("Socket 主站已启动，等待指令...")

    def closeEvent(self, event):
        """窗口关闭事件"""
        logger.info("应用程序正在关闭...")
        reply = QMessageBox.question(self, '退出程序', '确认退出程序吗?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.master.stop()
            self.update_timer.stop()
            self.device.stop_data_acquisition()
            self.device.close_device()
            self.recorder.stop_recording() #确保停止
            self.analysis_window.close() # 关闭分析窗口
            logger.info("应用程序已关闭")
            event.accept()
        else:
            event.ignore()

    def import_data(self):
        """导入并显示CSV数据文件"""
        try:
            # 停止传感器和定时器
            self.update_timer.stop()
            self.device.stop_data_acquisition()
            
            # 打开文件对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择数据文件",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                import pandas as pd
                # 读取CSV文件
                try:
                    df = pd.read_csv(file_path)
                    if '记录时间' not in df.columns or len(df.columns) < 17:
                        raise ValueError("CSV文件格式不正确")
                    
                    # 清空现有数据
                    self.timestamps.clear()
                    self.accel_x.clear()
                    self.accel_y.clear()
                    self.accel_z.clear()
                    self.vib_speed_x.clear()
                    self.vib_speed_y.clear()
                    self.vib_speed_z.clear()
                    self.vib_disp_x.clear()
                    self.vib_disp_y.clear()
                    self.vib_disp_z.clear()
                    self.vib_freq_x.clear()
                    self.vib_freq_y.clear()
                    self.vib_freq_z.clear()
                    self.temperature_data.clear()
                    
                    # 转换时间戳
                    base_time = pd.to_datetime(df['记录时间'].iloc[0])
                    timestamps = pd.to_datetime(df['记录时间'])
                    time_diffs = (timestamps - base_time).dt.total_seconds()
                    
                    # 添加数据
                    self.timestamps.extend(time_diffs.tolist())
                    self.accel_x.extend(df['加速度X(g)'].tolist())
                    self.accel_y.extend(df['加速度Y(g)'].tolist())
                    self.accel_z.extend(df['加速度Z(g)'].tolist())
                    self.vib_speed_x.extend(df['X轴振动速度(mm/s)'].tolist())
                    self.vib_speed_y.extend(df['Y轴振动速度(mm/s)'].tolist())
                    self.vib_speed_z.extend(df['Z轴振动速度(mm/s)'].tolist())
                    self.vib_disp_x.extend(df['X轴振动位移(um)'].tolist())
                    self.vib_disp_y.extend(df['Y轴振动位移(um)'].tolist())
                    self.vib_disp_z.extend(df['Z轴振动位移(um)'].tolist())
                    self.vib_freq_x.extend(df['X轴振动频率(Hz)'].tolist())
                    self.vib_freq_y.extend(df['Y轴振动频率(Hz)'].tolist())
                    self.vib_freq_z.extend(df['Z轴振动频率(Hz)'].tolist())
                    self.temperature_data.extend(df['温度(°C)'].tolist())
                    
                    # 更新显示
                    self.update_data_table(
                        self.accel_x[-1], self.accel_y[-1], self.accel_z[-1],
                        self.vib_speed_x[-1], self.vib_speed_y[-1], self.vib_speed_z[-1],
                        self.vib_disp_x[-1], self.vib_disp_y[-1], self.vib_disp_z[-1],
                        self.vib_freq_x[-1], self.vib_freq_y[-1], self.vib_freq_z[-1],
                        self.temperature_data[-1]
                    )
                    self.update_stats_table()
                    self.update_plots()
                    
                    QMessageBox.information(self, "导入成功", f"已成功导入 {len(df)} 条数据记录！")
                    
                except pd.errors.EmptyDataError:
                    QMessageBox.warning(self, "导入错误", "所选文件为空！")
                except ValueError as ve:
                    QMessageBox.warning(self, "导入错误", str(ve))
                except Exception as e:
                    QMessageBox.critical(self, "导入错误", f"导入数据时发生错误：{str(e)}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败：{str(e)}")
        finally:
            # 重新启动数据采集
            self.device.start_data_acquisition()
            self.update_timer.start()

