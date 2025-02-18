from PyQt5.QtCore import QObject

# 自定义基础信号类
class Signal(QObject):

    def __init__(self, *types):
        super().__init__()
        self.types = types
        self._slots = []  # 用于存储连接的槽函数

    def connect(self, slot):
        if not callable(slot):
            raise TypeError("Slot must be callable.")
        if slot not in self._slots:
            self._slots.append(slot)

    def disconnect(self, slot):
        if slot in self._slots:
            self._slots.remove(slot)

    def emit(self, *args):
         # 参数类型检查
        if len(args) != len(self.types):
            raise TypeError(f"Expected {len(self.types)} arguments, got {len(args)}.")
        for i, (arg, expected_type) in enumerate(zip(args, self.types)):
            if not isinstance(arg, expected_type):
                raise TypeError(f"Argument {i+1} has incorrect type (expected {expected_type}, got {type(arg)}).")

        for slot in self._slots:
            slot(*args)

