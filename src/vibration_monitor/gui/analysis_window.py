from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QComboBox, QPushButton,
                             QMessageBox, QDoubleSpinBox, QFormLayout, QLineEdit,
                             QTableWidget, QTableWidgetItem, QDialog)
import pyqtgraph as pg
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, butter, filtfilt, iirnotch
from typing import Dict, List, Optional, Union
from ..utils.logger import setup_logger


logger = setup_logger(__name__)


class ThresholdDialog(QDialog):
    """阈值设置对话框"""

    def __init__(self, thresholds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置阈值")
        self.thresholds = thresholds  # 传入默认阈值

        layout = QFormLayout(self)

        self.threshold_edits = {}
        for key, value in self.thresholds.items():
            label = QLabel(f"{key}:")
            edit = QDoubleSpinBox()
            edit.setDecimals(2)
            edit.setRange(0, 100)  # 根据需要设置范围
            edit.setSingleStep(0.1)
            edit.setValue(value)
            self.threshold_edits[key] = edit
            layout.addRow(label, edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    def get_thresholds(self):
        """获取用户设置的阈值"""
        return {key: edit.value() for key, edit in self.threshold_edits.items()}



class AnalysisWindow(QMainWindow):
    """高级数据分析窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级数据分析")
        self.setGeometry(200, 200, 1200, 800)  # 调整窗口大小
        self.main_data_cache: Dict[str, Union[List[float], List[int]]] = {}  # 用于接收主窗口数据, 明确类型
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

        # 特征提取选项卡
        self.feature_tab = QWidget()
        self.tab_widget.addTab(self.feature_tab, "特征提取")
        self.setup_feature_tab()

        # 数据滤波选项卡
        self.filter_tab = QWidget()
        self.tab_widget.addTab(self.filter_tab, "数据滤波")
        self.setup_filter_tab()

        # 趋势预测选项卡 (预留)
        # self.trend_tab = QWidget()
        # self.tab_widget.addTab(self.trend_tab, "趋势预测")
        # self.setup_trend_tab()

        # 下料分析选项卡
        self.feeding_tab = QWidget()
        self.tab_widget.addTab(self.feeding_tab, "下料分析")
        self.setup_feeding_tab()



    def setup_fft_tab(self):
        """设置 FFT 分析选项卡的布局"""
        fft_layout = QVBoxLayout(self.fft_tab)

        # 参数选择和控制面板
        control_layout = QHBoxLayout()

        param_layout = QFormLayout()  # 使用 QFormLayout
        param_label = QLabel("选择参数:")
        self.param_combo = QComboBox()
        self.param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度'
        ])
        param_layout.addRow(param_label, self.param_combo)
        control_layout.addLayout(param_layout)

        fft_layout.addLayout(control_layout)  # 将控制布局添加到主布局

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


    def setup_feature_tab(self):
        """设置特征提取选项卡的布局"""
        feature_layout = QVBoxLayout(self.feature_tab)

        # 参数选择和控制面板
        control_layout = QHBoxLayout()

        param_layout = QFormLayout()
        param_label = QLabel("选择参数:")
        self.feature_param_combo = QComboBox()  # 用于特征提取的参数选择
        self.feature_param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            '温度'  # 如果需要，也可以对温度进行特征提取
        ])
        param_layout.addRow(param_label, self.feature_param_combo)
        control_layout.addLayout(param_layout)

        feature_layout.addLayout(control_layout)

        # 特征显示表格
        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(2)
        self.feature_table.setHorizontalHeaderLabels(['特征', '值'])
        feature_layout.addWidget(self.feature_table)

        # 特征提取按钮
        extract_button = QPushButton("提取特征")
        extract_button.clicked.connect(self.extract_features)
        feature_layout.addWidget(extract_button)

    def setup_filter_tab(self):
        """设置数据滤波选项卡的布局"""
        filter_layout = QVBoxLayout(self.filter_tab)

        # 参数选择、滤波器类型选择和控制面板
        control_layout = QHBoxLayout()

        param_layout = QFormLayout()
        param_label = QLabel("选择参数:")
        self.filter_param_combo = QComboBox()  # 用于滤波的参数选择
        self.filter_param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            # '温度'  # 温度通常不需要滤波
        ])
        param_layout.addRow(param_label, self.filter_param_combo)

        filter_type_label = QLabel("滤波器类型:")
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(['低通', '高通', '带通', '带阻'])
        param_layout.addRow(filter_type_label, self.filter_type_combo)

        control_layout.addLayout(param_layout)

        # 滤波器参数设置
        filter_param_layout = QFormLayout()
        self.cutoff_freq_label = QLabel("截止频率 (Hz):")  # 根据选择的滤波器类型，可能需要调整
        self.cutoff_freq_edit = QDoubleSpinBox()
        self.cutoff_freq_edit.setDecimals(2)  # 设置小数位数
        self.cutoff_freq_edit.setRange(0.1, 1000) #设置最大最小值
        self.cutoff_freq_edit.setSingleStep(0.1) #设置步长
        filter_param_layout.addRow(self.cutoff_freq_label, self.cutoff_freq_edit)

        self.filter_order_label = QLabel("滤波器阶数:")
        self.filter_order_edit = QDoubleSpinBox()
        self.filter_order_edit.setRange(1,10)
        self.filter_order_edit.setSingleStep(1)
        filter_param_layout.addRow(self.filter_order_label,self.filter_order_edit)

        # 带通/带阻滤波器需要两个截止频率
        self.cutoff_freq2_label = QLabel("截止频率2 (Hz):")
        self.cutoff_freq2_edit = QDoubleSpinBox()
        self.cutoff_freq2_edit.setDecimals(2)
        self.cutoff_freq2_edit.setRange(0.1, 1000) #设置最大最小值
        self.cutoff_freq2_edit.setSingleStep(0.1) #设置步长
        filter_param_layout.addRow(self.cutoff_freq2_label, self.cutoff_freq2_edit)

        # 根据滤波器类型显示/隐藏第二个截止频率
        self.filter_type_combo.currentIndexChanged.connect(self.update_filter_ui)
        self.update_filter_ui()  # 初始化时更新一次

        control_layout.addLayout(filter_param_layout)

        filter_layout.addLayout(control_layout)

        # 滤波前后数据对比图
        self.filter_plot = pg.PlotWidget()
        self.filter_plot.setBackground('w')
        self.filter_plot.showGrid(x=True, y=True, alpha=0.3)
        self.filter_plot.setLabel('left', "幅度")
        self.filter_plot.setLabel('bottom', "时间", units='s')
        self.original_curve = self.filter_plot.plot(pen=pg.mkPen('b', width=2))
        self.filtered_curve = self.filter_plot.plot(pen=pg.mkPen('r', width=2))
        self.filter_plot.addLegend()
        filter_layout.addWidget(self.filter_plot)

        # 应用滤波按钮
        apply_filter_button = QPushButton("应用滤波")
        apply_filter_button.clicked.connect(self.apply_filter)
        filter_layout.addWidget(apply_filter_button)

    def setup_feeding_tab(self):
        """设置下料分析选项卡的布局"""
        feeding_layout = QVBoxLayout(self.feeding_tab)

        # 参数选择和控制面板
        control_layout = QHBoxLayout()

        param_layout = QFormLayout()
        param_label = QLabel("选择参数:")
        self.feeding_param_combo = QComboBox()
        self.feeding_param_combo.addItems([
            '加速度X', '加速度Y', '加速度Z',
            '速度X', '速度Y', '速度Z',
            '位移X', '位移Y', '位移Z',
            '频率X', '频率Y', '频率Z',
            # '温度' # 如果需要，也可以分析温度
        ])
        param_layout.addRow(param_label, self.feeding_param_combo)

        # 目标重量
        target_weight_label = QLabel("目标重量 (g):")
        self.target_weight_edit = QDoubleSpinBox()
        self.target_weight_edit.setDecimals(2)
        self.target_weight_edit.setRange(0, 10000)  # 根据实际情况设置范围
        self.target_weight_edit.setSingleStep(1)
        param_layout.addRow(target_weight_label, self.target_weight_edit)
        
        # 允许误差
        tolerance_lable = QLabel("允许误差")
        self.tolerance_edit = QDoubleSpinBox()
        self.tolerance_edit.setDecimals(2)
        self.tolerance_edit.setRange(0.1,10) #根据实际情况设置
        self.tolerance_edit.setSingleStep(0.1)
        param_layout.addRow(tolerance_lable,self.tolerance_edit)


        control_layout.addLayout(param_layout)

        # 阈值设置 (可选, 高级用户)
        threshold_button = QPushButton("设置阈值")
        threshold_button.clicked.connect(self.open_threshold_dialog)
        control_layout.addWidget(threshold_button)

        feeding_layout.addLayout(control_layout)

        # 下料过程图
        self.feeding_plot = pg.PlotWidget()
        self.feeding_plot.setBackground('w')
        self.feeding_plot.showGrid(x=True, y=True, alpha=0.3)
        self.feeding_plot.setLabel('left', "幅度")
        self.feeding_plot.setLabel('bottom', "时间", units='s')
        self.feeding_curve = self.feeding_plot.plot(pen=pg.mkPen('b', width=2))  # 原始数据
        self.feeding_state_curve = self.feeding_plot.plot(
            pen=pg.mkPen('r', width=3))  # 下料阶段 (用不同颜色表示)
        feeding_layout.addWidget(self.feeding_plot)

        # 状态显示
        self.state_label = QLabel("当前状态:  -")
        feeding_layout.addWidget(self.state_label)

        # 分析按钮
        analyze_button = QPushButton("开始下料分析")
        analyze_button.clicked.connect(self.perform_feeding_analysis)
        feeding_layout.addWidget(analyze_button)


    def update_filter_ui(self):
        """根据选择的滤波器类型更新界面"""
        filter_type = self.filter_type_combo.currentText()
        if filter_type in ('带通', '带阻'):
            self.cutoff_freq2_label.show()
            self.cutoff_freq2_edit.show()
        else:
            self.cutoff_freq2_label.hide()
            self.cutoff_freq2_edit.hide()

        if filter_type == '带阻':
            self.cutoff_freq_label.setText("中心频率 (Hz):")
        else:
            self.cutoff_freq_label.setText("截止频率 (Hz):")

    def apply_filter(self):
      """应用滤波器"""
      selected_param = self.filter_param_combo.currentText()
      filter_type = self.filter_type_combo.currentText()
      order = int(self.filter_order_edit.value())
      if filter_type in ('带通','带阻'):
          cutoff_freq = [self.cutoff_freq_edit.value(),self.cutoff_freq2_edit.value()]
      else:
          cutoff_freq = self.cutoff_freq_edit.value()  # 获取截止频率

      time_data = self.main_data_cache.get('timestamps')
      series_data = self.main_data_cache.get(selected_param)

      if (not time_data or not series_data) :
          QMessageBox.warning(self, "警告", "数据不足，无法滤波")
          return

      # 计算采样率
      fs = 1 / (time_data[1] - time_data[0])  # 假设时间戳是等间距的
      if (len(time_data) != len(series_data)):
          QMessageBox.warning(self,"警告","时间数据与信号数据长度不一致")
           # 可以截断较长的列表，或者填充较短的列表，这里选择截断
          min_len = min(len(time_data),len(series_data))
          time_data = time_data[:min_len]
          series_data = series_data[:min_len]
          logger.warning("时间数据与选择的信号数据长度不一致,已自动截断")

      # 归一化频率
      if isinstance(cutoff_freq,list): #带通，带阻
          nyquist = 0.5 * fs
          normalized_cutoff = [f / nyquist for f in cutoff_freq]
      else: #低通，高通
          normalized_cutoff = cutoff_freq / (0.5 * fs)

      try:
          # 设计滤波器
        if filter_type == '低通':
            b, a = butter(order, normalized_cutoff, btype='low', analog=False)
        elif filter_type == '高通':
            b, a = butter(order, normalized_cutoff, btype='high', analog=False)
        elif filter_type == '带通':
            b, a = butter(order, normalized_cutoff, btype='band', analog=False)
        elif filter_type == '带阻':
              # 带阻滤波器使用 iirnotch
              w0 = cutoff_freq / (0.5 * fs)  # 中心频率
              if isinstance(w0,list):
                  w0 = w0[0] #取第一个中心频率
              bw = (cutoff_freq[1]-cutoff_freq[0])/(0.5*fs)  # 带宽
              Q = w0 / bw  # 品质因数.  中心/带宽
              b, a = iirnotch(w0, Q)

          # 应用滤波器
        filtered_data = filtfilt(b, a, series_data)

          # 更新绘图
        self.original_curve.setData(time_data, series_data)
        self.filtered_curve.setData(time_data, filtered_data)
        self.original_curve.getViewBox().autoRange()
        self.filtered_curve.getViewBox().autoRange()

      except Exception as e:
          logger.exception(f"滤波时发生错误: {e}")
          QMessageBox.critical(self, "错误", f"滤波失败: {e}")
    def extract_features(self):
        """提取特征"""
        selected_param = self.feature_param_combo.currentText()
        series_data = self.main_data_cache.get(selected_param)

        if not series_data:
            QMessageBox.warning(self, "警告", "没有数据可供分析")
            return
        if len(series_data) == 0:
            QMessageBox.warning(self, "警告", "没有可用数据")
            return
        try:
            # 特征提取
            features = {}
            features['均值'] = np.mean(series_data)
            features['方差'] = np.var(series_data)
            features['标准差'] = np.std(series_data)
            features['均方根'] = np.sqrt(np.mean(np.square(series_data)))
            features['峰值'] = np.max(np.abs(series_data))  # 峰值 (绝对值的最大值)
            features['峰峰值'] = np.max(series_data) - np.min(series_data)
            features['峭度'] = (
                np.sum((series_data - features['均值']) ** 4) / len(series_data)
            ) / (features['标准差'] ** 4)
            features['偏度'] = (
                np.sum((series_data - features['均值']) ** 3) / len(series_data)
            ) / (features['标准差'] ** 3)


            # 查找峰值 (使用 scipy.signal.find_peaks)
            peaks, _ = find_peaks(np.abs(series_data))  # 只在正值中查找峰值
            if(len(peaks) > 0):
                features['峰值数量'] = len(peaks)
                features['平均峰值间距'] = np.mean(np.diff(peaks)) if len(peaks) > 1 else 0 #平均峰值间距
            else:
                 features['峰值数量'] = 0
                 features['平均峰值间距'] = 0

            # 更新表格
            self.feature_table.setRowCount(len(features))
            for row, (feature_name, feature_value) in enumerate(features.items()):
                self.feature_table.setItem(row, 0, QTableWidgetItem(feature_name))
                self.feature_table.setItem(row, 1, QTableWidgetItem(f"{feature_value:.4f}"))

        except Exception as e:
            logger.exception(f"特征提取时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"特征提取失败: {e}")

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
        if(len(time_data) != len(series_data)):
             QMessageBox.warning(self,"警告","时间数据与信号数据长度不一致")
              # 可以截断较长的列表，或者填充较短的列表，这里选择截断
             min_len = min(len(time_data),len(series_data))
             time_data = time_data[:min_len]
             series_data = series_data[:min_len]
             logger.warning("时间数据与选择的信号数据长度不一致,已自动截断")
        try:
            yf = fft(series_data)
            xf = fftfreq(N, time_data[1] - time_data[0])  # 假设是等间距采样

            # 只取正频率
            xf_pos = xf[:N // 2]
            yf_pos = np.abs(yf[0:N // 2])
            self.fft_curve.setData(xf_pos, yf_pos)
            #自动缩放,调整坐标轴
            self.fft_curve.getViewBox().autoRange()

        except Exception as e:
            logger.exception(f"FFT计算错误: {e}")
            QMessageBox.critical(self, "错误", "FFT 计算失败！")


    def open_threshold_dialog(self):
        """打开阈值设置对话框"""
        dialog = ThresholdDialog(self.thresholds, self)  # thresholds 是一个字典，存储阈值
        if dialog.exec_():
            self.thresholds = dialog.get_thresholds()
            logger.debug(f"用户更新了阈值: {self.thresholds}")


    def perform_feeding_analysis(self):
        """执行下料分析"""
        selected_param = self.feeding_param_combo.currentText()
        target_weight = self.target_weight_edit.value()
        tolerance = self.tolerance_edit.value()
        time_data = self.main_data_cache.get('timestamps')
        series_data = self.main_data_cache.get(selected_param)

        if not time_data or not series_data:
            QMessageBox.warning(self, "警告", "数据不足")
            return
        if len(time_data) == 0 or len(series_data) == 0:
             QMessageBox.warning(self, "警告", "没有可用数据")
             return

        # 初始化状态机和阈值
        state = "Initial"
        # 示例阈值,根据实际情况调整
        if not hasattr(self,"thresholds"):
            self.thresholds = {
                'threshold1': 20,    # 初始 -> 快速下料 (振动幅度)
                'threshold2': 10,    # 初始 -> 快速下料 (振动速度)
                'threshold3': 5,     # 快速下料 - > 慢速下料
                'threshold4': -2,   #快速下料 -> 慢速下料 (振动速度变化率)
                "threshold5" : 50,   # 慢速下料 -> 停止 (估计剩余重量)
                'threshold6': 2,     # 停止下料 -> 稳定 (振动幅度)
                'threshold7': 1,      # 停止下料 -> 稳定  (振动幅度)
                'threshold8': 5,   #补料判断
                'threshold9': 2, #补料判断
            }

        # 存储状态序列，用于绘图
        state_sequence = []

        # 模拟实时数据处理（这里假设数据已经全部加载）
        for i in range(len(time_data)):
            # 提取当前数据点的特征
            current_features = self.extract_feeding_features(series_data, i)

            # 状态机逻辑
            if state == "Initial":
                if (current_features['振动幅度'] > self.thresholds['threshold1'] and
                        current_features['振动速度'] > self.thresholds['threshold2']):
                    state = "FastFeeding"
            elif state == "FastFeeding":
                if (current_features['振动幅度'] < self.thresholds['threshold3'] or
                        current_features["振动速度变化率"] < self.thresholds['threshold4']):
                    state = "SlowFeeding"
            elif state == "SlowFeeding":
              if current_features['估计剩余重量'] <  self.thresholds['threshold5']:
                    state = "StopFeeding"
            elif state == "StopFeeding":
                if (current_features['振动幅度'] < self.thresholds['threshold6'] and
                        current_features['振动速度'] < self.thresholds['threshold7']):
                    state = "Stable"
            elif state == "Stable":
                if current_features['与目标重量偏差'] < -tolerance:
                    state = "Dithering"
            elif state == "Dithering":
               if (current_features['振动幅度'] < self.thresholds['threshold8'] and
                        current_features['振动速度'] < self.thresholds['threshold9']):
                    state = "Stable"

            state_sequence.append(self.state_to_number(state))  # 将状态转换为数字，方便绘图
            self.state_label.setText(f"当前状态: {state}")  # 更新状态显示

            #实时绘制波形
            self.feeding_curve.setData(time_data[:i+1],series_data[:i+1])
            self.feeding_state_curve.setData(time_data[:i+1],state_sequence)
             #自动缩放,调整坐标轴
            self.feeding_curve.getViewBox().autoRange()
            self.feeding_state_curve.getViewBox().autoRange()


    def extract_feeding_features(self, data, index):
      """提取下料分析所需的特征 (单个数据点)
          index: 当前数据点
      """
      # 这里只是一个示例，你需要根据实际情况实现特征提取
      window_size = 10  # 滑动窗口大小,根据实际情况调整.

      # 提取历史数据段
      if index < window_size:
          window_data = data[:index+1]
      else:
          window_data = data[index - window_size + 1:index+1]

      features = {}
      features['振动幅度'] = np.mean(np.abs(window_data))
      features['振动速度'] = np.mean(np.diff(window_data)) if len(window_data) > 1 else 0  # 差分近似速度
      features['振动速度变化率'] = np.mean(np.diff(np.diff(window_data))) if len(window_data) > 2 else 0

      # 估计剩余重量 (非常简化的模型,实际需要一个经验公式)
      features['估计剩余重量'] = (1 - (index / len(data))) *  self.target_weight_edit.value()  # 线性递减
      # 与目标重量偏差
      features["与目标重量偏差"] = features['估计剩余重量'] - self.target_weight_edit.value()


      return features

    def state_to_number(self, state):
        """将状态字符串转换为数字"""
        state_mapping = {
            "Initial": 0,
            "FastFeeding": 1,
            "SlowFeeding": 2,
            "StopFeeding": 3,
            "Stable": 4,
            "Dithering": 5
        }
        return state_mapping.get(state, -1)  # 如果状态未知，返回 -1


    def receive_data_from_main(self, data_cache: Dict[str, List[float]]):
        """接收来自主窗口的数据"""
        self.main_data_cache = data_cache
        logger.debug(f"接收到来自主窗口的数据: {len(data_cache)} 个键")

