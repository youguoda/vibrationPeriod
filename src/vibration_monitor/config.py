import configparser
import os

class Config:
    """配置管理类"""

    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()

        # 获取配置文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))  #当前文件目录
        config_path = os.path.join(current_dir, '..', '..',config_file) #项目根目录

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件 '{config_path}' 不存在")

        self.config.read(config_path, encoding='utf-8')

    def get(self, section, key, fallback=None):
        """获取配置值"""
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        return self.config.getint(section, key, fallback=fallback)

    def getfloat(self, section, key, fallback=None):
        return self.config.getfloat(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=None):
        return self.config.getboolean(section, key, fallback=fallback)

    def set(self, section, key, value):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))

    def save(self, config_file='config.ini'):
        """保存配置到文件,支持指定文件名"""
        # 获取配置文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))  #当前文件目录
        config_path = os.path.join(current_dir, '..', '..', config_file) #项目根目录
        with open(config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
