"""
@File       : enums.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 定义项目中使用的所有枚举类型
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms
"""

from enum import Enum


class ChatStatus(Enum):
    """Enum for different chat status in the system."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ANSWERED = "ANSWERED"
    FAILED = "FAILED"


class MessageType(Enum):
    """Enum for different message types in the system."""
    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"


class OrderState(Enum):
    """Enum for different order states in the system."""
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"


class PaymentMethod(Enum):
    """Enum for different payment methods in the system."""
    WECHAT = "WECHAT"
    ALIPAY = "ALIPAY"
    CASH = "CASH"
    CARD = "CARD"
    MEITUAN = "MEITUAN"
    DOUYIN = "DOUYIN"
    JD = "JD"
    OTHER = "OTHER"


class DiningAreaState(Enum):
    """Enum for different dining area states in the system."""
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"


class AreaType(Enum):
    """Enum for different area types in the system."""
    PRIVATE = "PRIVATE"
    TABLE = "TABLE"
    BAR = "BAR"

    @classmethod
    def from_string(cls, value: str) -> "AreaType":
        """将字符串转换为枚举类型，如果无效则抛出异常"""
        area_type = cls.__members__.get(value.upper())  # 获取枚举成员
        if area_type is None:
            raise ValueError(f"Invalid AreaType: {value}")
        return area_type


class UserRole(Enum):
    """Enum for different user roles in the system."""
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    USER = "USER"


class UserStatus(Enum):
    """Enum for different user status in the system."""
    ACTIVE = "ACTIVE"
    BANNED = "BANNED"
    DELETED = "DELETED"
