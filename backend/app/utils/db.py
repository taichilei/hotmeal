"""
@File       : db.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 提供全局共享的 SQLAlchemy 实例，供应用初始化和模型定义使用
@Version    : 1.0.0，移除 db_session
@Copyright  : Copyright © 2025. All rights reserved.
"""

# 只需导入 SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

# 创建 SQLAlchemy 实例，供应用初始化和模型定义使用
db = SQLAlchemy()

# 不再需要 logger 或其他辅助函数
