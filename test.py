import time
import csv
from datetime import datetime
import device_model
import serial

"""
    WTVB01-485示例 Example
"""

# region 常用寄存器地址对照表
"""
hex    dec      describe

0x00    0       保存/重启/恢复
0x04    4       串口波特率

0x1A    26      设备地址

0x3A    58      振动速度x
0x3B    59      振动速度y
0x3C    60      振动速度z

0x3D    61      振动角度x
0x3E    62      振动角度y
0x3F    63      振动角度z

0x40    64      温度

0x41    65      振动位移x
0x42    66      振动位移y
0x43    67      振动位移z

0x44    68      振动频率x
0x45    69      振动频率y
0x46    70      振动频率z

0x63    99      截止频率
0x64    100     截止频率
0x65    101     检测周期

"""
# endregion

# 初始化CSV文件
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'vibration_data_{current_time}.csv'
csv_file = open(csv_filename, 'w', newline='', encoding='utf-8-sig')  # 使用 utf-8-sig 添加 BOM 头
csv_writer = csv.writer(csv_file)
csv_writer.writerow([
    '记录时间', '设备名称', 
    '加速度X(g)', '加速度Y(g)', '加速度Z(g)', 
    '角速度X(°/s)', '角速度Y(°/s)', '角速度Z(°/s)',
    'X轴振动速度(mm/s)', 'Y轴振动速度(mm/s)', 'Z轴振动速度(mm/s)',
    'X轴振动角度(°)', 'Y轴振动角度(°)', 'Z轴振动角度(°)',
    'X轴振动位移(um)', 'Y轴振动位移(um)', 'Z轴振动位移(um)',
    'X轴振动频率(Hz/s)', 'Y轴振动频率(Hz/s)', 'Z轴振动频率(Hz/s)',
    '温度(℃)'
])

# 拿到设备模型
try:
    print(f"尝试连接设备 COM5, 波特率 230400, 地址 50...")
    device = device_model.DeviceModel("测试设备", "COM5", 230400, 0x50)
    # 开启设备
    device.openDevice()
    print("设备连接成功！")
    # 开启轮询
    device.startLoopRead()
    print("开始数据轮询...")
    time.sleep(0.5)

except serial.SerialException as e:
    print(f"\n错误：串口连接失败！")
    print(f"错误详情：{str(e)}")
    print("\n可能的原因：")
    print("1. COM5 端口不存在")
    print("2. 设备未正确连接")
    print("3. 串口被其他程序占用")
    print("4. 没有足够的权限访问串口")
    print("\n请检查：")
    print("1. 设备是否正确连接到电脑")
    print("2. 在设备管理器中确认正确的COM端口号")
    print("3. 关闭可能占用该串口的其他程序")
    exit(1)

except Exception as e:
    print(f"\n错误：设备初始化失败！")
    print(f"错误详情：{str(e)}")
    exit(1)

try:
    print(f"开始记录数据到文件: {csv_filename}")
    print("按Ctrl+C停止记录...")
    
    empty_data_count = 0  # 统计空数据次数
    max_empty_data = 5    # 最大允许的连续空数据次数
    
    while True:
        # 获取当前时间
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 检查设备连接状态
        if not device.isOpen:
            print("\n设备连接已断开，尝试重新连接...")
            try:
                device.openDevice()
                device.startLoopRead()
                print("设备重新连接成功！")
                time.sleep(0.5)  # 等待数据稳定
                continue
            except Exception as e:
                print(f"重新连接失败: {str(e)}")
                break
        
        # 获取所有数据
        data_values = [
            device.get("52"), device.get("53"), device.get("54"),  # 加速度
            device.get("55"), device.get("56"), device.get("57"),  # 角速度
            device.get("58"), device.get("59"), device.get("60"),  # 振动速度
            device.get("61"), device.get("62"), device.get("63"),  # 振动角度
            device.get("65"), device.get("66"), device.get("67"),  # 振动位移
            device.get("68"), device.get("69"), device.get("70"),  # 振动频率
            device.get("64")                                       # 温度
        ]
        
        # 检查是否所有数据都是None
        if all(v is None for v in data_values):
            empty_data_count += 1
            print(f"\r等待数据... ({empty_data_count}/{max_empty_data})", end="")
            
            if empty_data_count >= max_empty_data:
                print("\n警告：连续多次未获取到数据，可能存在通信问题")
                # 记录空数据行，保持时间戳连续性
                data_row = [timestamp, device.deviceName] + [""] * 19
                csv_writer.writerow(data_row)
                empty_data_count = 0  # 重置计数器
            
            time.sleep(0.2)  # 增加等待时间
            continue
        
        # 获取到有效数据，重置计数器
        empty_data_count = 0
        
        # 写入CSV
        data_row = [
            timestamp,                    # 记录时间
            device.deviceName,            # 设备名称
        ] + [str(v) if v is not None else "" for v in data_values]  # 转换None为空字符串
        
        csv_writer.writerow(data_row)
        
        # 实时打印部分关键数据
        temp = data_values[-1]  # 温度是最后一个值
        temp_str = f"{temp}℃" if temp is not None else "N/A"
        print(f"\r时间: {timestamp} | 设备: {device.deviceName} | 温度: {temp_str}", end="")
        
        # 确保数据即时写入文件
        csv_file.flush()
        
        # 休眠150ms，给设备更多时间更新数据
        time.sleep(0.15)

except KeyboardInterrupt:
    print("\n停止记录数据...")
finally:
    # 关闭文件和设备
    csv_file.close()
    device.stopLoopRead()
    device.closeDevice()
    print(f"数据已保存到文件: {csv_filename}")
