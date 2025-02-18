from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QComboBox, QPushButton,
                             QMessageBox)
import pyqtgraph as pg
import numpy as np
from scipy.fft import fft, fftfreq
from ..utils.logger import setup_logger

logger = setup_logger(__name__) #日志

class AnalysisWindow(QMainWindow):
    """高级数据分析窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级数据分析")
        self.setGeometry(200, 200, 800, 600)
        self.main_data_cache = {}  # 用于接收主窗口数据
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # FFT 分析选项卡
        self.fft_tab = QWidget()
        self.tab_widget.addTab(self.fft_tab, "FFT 分析")
        self.setup_fft_tab()
        # 趋势预测选项卡 (预留)
        self.trend_tab = QWidget()
        self.tab_widget.addTab(self.trend_tab,"趋势预测")

    def setup_fft_tab(self):
      """设置 FFT 分析选项卡的布局"""
      fft_layout = QVBoxLayout(self.fft_tab)

      # 参数选择
      param_layout = QHBoxLayout()
      param_label = QLabel("选择参数:")
      self.param_combo = QComboBox()
      self.param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度'
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
      self.fft_curve = self.fft_plot.plot(pen=pg.mkPen('b', width=2))
      fft_layout.addWidget(self.fft_plot)

      # 分析按钮
      analyze_button = QPushButton("进行 FFT 分析")
      analyze_button.clicked.connect(self.perform_fft)
      fft_layout.addWidget(analyze_button)

    def perform_fft(self):
      """执行 FFT 分析"""
      selected_param = self.param_combo.currentText()
      logger.debug(f"执行FFT,当前选择: {selected_param}")
      # 检查是否有所需数据
      if selected_param not in self.main_data_cache:
          QMessageBox.warning(self, "警告", "没有选择数据！")
          return

      time_data = self.main_data_cache.get("timestamps")
      series_data = self.main_data_cache.get(selected_param)

      if not time_data or not series_data:
          QMessageBox.warning(self, "警告", "数据不足！")
          return
      # 进行FFT
      N = len(series_data)
      if N == 0:
          QMessageBox.warning(self, "警告", "没有可用数据")
          return

      try:
          yf = fft(series_data)
          xf = fftfreq(N, time_data[1] - time_data[0])

          #只取正频率
          xf_pos = xf[:N//2]
          yf_pos = np.abs(yf[0:N//2])
          self.fft_curve.setData(xf_pos, yf_pos)

      except Exception as e:
          logger.exception(f"FFT计算错误: {e}")
          QMessageBox.critical(self, "错误", "FFT 计算失败！")

    def receive_data_from_main(self, data_cache):
        """接收来自主窗口的数据"""
        self.main_data_cache = data_cache
        logger.debug(f"接收到来自主窗口的数据: {len(data_cache)} 个键")

