"""
@文件        : __init__.py
@作者         : taichilei
@日期         : 2025-04-23
@描述         : models 模块初始化，导出所有数据模型
"""

from app.utils.db import db

from .category import Category
from .chat import Chat
from .dining_area import DiningArea
from .dish import Dish
from .order import Order
from .order_item import OrderItem
from .tag import Tag
from .user import User

__all__ = ["db", "Dish", "User", "Order", "DiningArea", "Category", "Chat", "OrderItem", "Tag"]
