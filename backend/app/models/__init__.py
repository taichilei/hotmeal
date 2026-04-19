"""
File Name:     /app/models/__init__.py
Project:       hotmeal
Author:        taichilei
Created:       2025-04-23
Description:   models init
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
