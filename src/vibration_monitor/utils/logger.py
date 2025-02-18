import logging
import os
from ..config import Config  # 导入 Config 类, 修正相对导入

# 创建 Config 实例,config.ini应在项目根目录
config = Config()

def setup_logger(name):
    """配置日志记录器"""

    # 从配置文件读取日志级别和文件名
    log_level_str = config.get('Logging', 'log_level', fallback='INFO')
    log_file = config.get('Logging', 'log_file', fallback='vibration_monitor.log')
    # 获取日志级别
    level = _parse_log_level(log_level_str)


    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 确保日志文件路径存在于项目根目录, utils是在src下的第三层级目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(current_dir, '..', '..', '..', log_file)

    # 使用 FileHandler 写入日志文件,并设置为UTF-8编码
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    # 设置日志级别,从配置文件读取
    file_handler.setLevel(level)

    # 使用 StreamHandler 输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)  # 添加到控制台的handler

    return logger

def _parse_log_level(level_str):
    """
    解析日志级别字符串，支持 int 和 str 两种输入。
    """
    level_str = level_str.strip().upper()  # 去除首尾空白并转为大写
        # 先尝试直接从字符串获取级别
    try:
        if level_str in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'):
             return logging.getLevelName(level_str) #这里实质是str->int
    except Exception:
        pass
     # 如果直接获取失败，尝试从可能的数值字符串中获取
    try:
        level = int(level_str)
        if level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
            return level
    except ValueError:
        pass
      # 如果都不是有效级别,返回默认值
    return logging.INFO
