# 振动监测系统

## 项目简介

振动监测系统是一个基于 Python 开发的工业设备振动数据采集和分析系统。该系统支持实时数据采集、可视化显示、数据分析和报警功能，为工业设备的振动监测和预警提供完整解决方案。

## 主要功能

* 实时数据采集与显示

  * 支持加速度、速度、位移和频率等多维度数据采集
  * 实时数据表格展示
  * 动态曲线可视化
* 数据分析功能

  * 历史数据查看
  * 数据趋势分析
  * 数据导出功能
* 报警监测

  * 可配置的报警阈值
  * 实时报警提示
  * 报警日志记录

## 系统架构

### 核心模块

1. 设备通信模块

    * 支持多种设备协议
    * 可扩展的设备驱动接口
    * 稳定的数据采集机制
2. 图形界面模块

    * 基于 PyQt5 的现代化界面
    * 实时数据展示
    * 交互式配置界面
3. 数据处理模块

    * 数据解析和验证
    * 数据存储管理
    * 数据分析算法

### 技术栈

* Python 3.x
* PyQt5
* pyserial
* pyqtgraph
* configparser

## 安装说明

### 系统要求

* Windows 操作系统
* Python 3.7 或更高版本
* USB 串口支持

### 安装步骤

1. 克隆项目代码

```bash
git clone https://github.com/youguoda/vibrationPeriod.git
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置设备参数
    编辑 `config.ini` 文件，设置设备参数：

```ini
[Device]
device_name = WTVB01
port = COM5
baudrate = 230400
address = 80
```

## 使用说明

### 启动程序

方法一：

```bash
python -m vibration_monitor.main
```

方法二：
在 setup.py 中定义了 entry_points，安装包后会自动生成一个可执行命令行脚本，直接运行即可。

**步骤：**

1. 安装你的包

   （进入setup.py所在目录）：

   ```shell
   pip install -e .
   ```

   * `-e` 表示“开发模式”，修改代码后无需重新安装。

2. 运行命令

   ```shell
   vibration-monitor
   ```

   * 这会自动调用 `vibration_monitor.main:main()` 函数。

| 方法 | 适用场景                   | 命令 |
| ------ | ---------------------------- | ------ |
| **`console_scripts`**     | 正式使用（安装后全局可用） | `vibration-monitor`     |
| **直接运行** **`main.py`**    | 开发调试                   | `python -m vibration_monitor.main`     |

### 基本操作流程

1. 连接设备

    * 确保设备正确连接到计算机
    * 检查串口号配置是否正确
2. 数据采集

    * 点击"开始采集"按钮开始数据采集
    * 实时查看数据变化
    * 观察报警状态
3. 数据分析

    * 打开分析窗口查看历史数据
    * 导出数据进行深入分析

## 项目结构

```
vibration_monitor/
├── src/vibration_monitor/    # 源代码
│   ├── device/              # 设备驱动
│   ├── gui/                 # 图形界面
│   ├── utils/              # 工具类
│   └── main.py             # 程序入口
├── data/                    # 数据文件
├── docs/                    # 文档
├── tests/                   # 测试代码
└── config.ini              # 配置文件
```

## 配置说明

### 设备配置

* device_name: 设备名称
* port: 串口号
* baudrate: 波特率
* address: 设备地址

### 日志配置

* log_level: 日志级别（DEBUG/INFO/WARNING/ERROR）
* log_file: 日志文件路径

### 报警阈值配置

可在界面中设置各项数据的报警阈值

## 开发指南

### 添加新设备支持

1. 在 device 目录下创建新的设备类
2. 继承 DeviceModel 基类
3. 实现必要的接口方法

### 扩展分析功能

1. 在 gui 目录下添加新的分析窗口
2. 实现数据处理逻辑
3. 在主窗口中添加调用入口

## 常见问题

### 1. 设备连接失败

* 检查设备是否正确连接
* 验证串口号配置
* 确认驱动程序安装

### 2. 数据显示异常

* 检查数据采集参数
* 验证设备通信是否正常
* 查看错误日志

## 维护说明

### 日志管理

* 日志文件位于项目根目录
* 定期清理过期日志
* 根据需要调整日志级别

### 数据备份

* 定期备份重要数据
* 维护数据文件结构
* 检查存储空间使用

## 许可证

MIT License

## 联系方式

INNOTIME颖态智能有限公司
