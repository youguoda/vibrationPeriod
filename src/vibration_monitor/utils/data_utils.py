def safe_float(value, default=0.0):
    """安全地将值转换为浮点数，如果转换失败则返回默认值"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
