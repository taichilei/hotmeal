"""
@File       : order_item.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 订单项模型类，表示订单中的每个菜品项。
               价格使用 Decimal 类型存储以保证精度。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import logging
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.utils.db import db

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .dish import Dish
    from .order import Order


class OrderItem(db.Model):
    """
    订单项模型

    Attributes:
        order_item_id: 订单项 ID (主键)
        order_id: 所属订单 ID (外键)
        dish_id: 关联菜品 ID (外键)
        quantity: 菜品数量 (必须 > 0)
        unit_price: 下单时菜品单价快照 (Decimal)
        order: 关联的 Order 对象
        dish: 关联的 Dish 对象
    """
    __tablename__ = 'order_items'

    __table_args__ = (
        db.Index('ix_order_item_order_id', 'order_id'),
        db.Index('ix_order_item_dish_id', 'dish_id'),
    )

    # --- 使用 Mapped 和 mapped_column ---
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="订单项ID")
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey('orders.order_id',
                                                              name='fk_order_item_order_id',
                                                              ondelete="CASCADE"), nullable=False,
                                          comment="所属订单ID")  # 添加 ondelete="CASCADE"?
    dish_id: Mapped[int] = mapped_column(Integer,
                                         ForeignKey('dish.dish_id', name='fk_order_item_dish_id'),
                                         nullable=False,
                                         comment="关联菜品ID")  # 外键通常不应为 NULL，除非菜品允许被硬删除
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="菜品数量")
    # --- 使用 Numeric 存储单价 ---
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False,
                                                comment="下单时菜品单价快照")

    # --- 关系定义 ---
    order: Mapped["Order"] = relationship(back_populates="order_items")
    # lazy='joined' 或 'selectin' 通常比默认的 'select' 好，避免 N+1
    dish: Mapped["Dish"] = relationship(backref=db.backref('order_items', lazy='selectin'),
                                        lazy='joined')

    # --- 移除自定义 __init__ ---

    # --- 属性验证 ---
    @validates('quantity')
    def validate_quantity(self, _key, quantity):
        """
        validate_quantity 验证数量是否有效。
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("数量必须是大于 0 的整数")
        return quantity

    @validates('unit_price')
    def validate_unit_price(self, _key, price):
        """
        validate_unit_price 验证单价是否有效，并转换为 Decimal 类型。
        """
        try:
            price_decimal = Decimal(str(price))  # 确保是 Decimal
        except (TypeError, InvalidOperation):
            raise ValueError("单价必须是有效的数字")
        if price_decimal <= 0:  # 单价通常必须大于 0
            raise ValueError("单价必须大于零")
        return price_decimal

    # --- 实例方法 ---
    def calculate_item_total(self) -> Decimal:
        """计算当前订单项的总价 (数量 * 单价)。"""
        # 确保 self.quantity 和 self.unit_price 是正确的类型
        if self.quantity is None or self.unit_price is None:
            logger.error(f"订单项 {self.order_item_id} 缺少数量或单价，无法计算总价。")
            return Decimal("0.00")
        return Decimal(str(self.quantity)) * self.unit_price  # 确保是 Decimal 运算

    def to_dict(self) -> dict[str, Any]:
        """将订单项对象转换为字典。"""
        # 确保 dish 对象已加载 (lazy='joined' 或服务层预加载)
        dish_name = self.dish.name if self.dish else "未知菜品"
        item_total = self.calculate_item_total()

        return {
            'order_item_id': self.order_item_id,
            'order_id': self.order_id,
            'dish_id': self.dish_id,
            'dish_name': dish_name,
            'quantity': self.quantity,
            # --- unit_price 和 total 返回字符串保证精度 ---
            'unit_price': str(self.unit_price) if self.unit_price is not None else "0.00",
            'total': str(item_total)
        }

    def __repr__(self):
        return f"<OrderItem(id={self.order_item_id}, order_id={self.order_id}, dish_id={self.dish_id}, qty={self.quantity})>"
