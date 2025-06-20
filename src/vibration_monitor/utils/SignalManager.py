from PyQt5.QtCore import QObject, pyqtSignal


class SignalManager(QObject):
    StartSignal = pyqtSignal()  # 开始信号
    StopSignal = pyqtSignal()  # 停止信号
    PauseSignal = pyqtSignal()  # 暂停信号


signalManager = SignalManager()
