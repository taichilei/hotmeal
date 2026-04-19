"""
@File       : order.py
@Author     : taichilei
@Date       : 2025-05-05
@Description: 订单数据模型
"""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as DBEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.enums import OrderState, PaymentMethod
from app.utils.db import db

# 处理 OrderItem 的循环类型提示
if TYPE_CHECKING:
    from .dining_area import DiningArea
    from .order_item import OrderItem
    from .user import User

logger = logging.getLogger(__name__)


class Order(db.Model):
    """
    订单模型类。
    """
    __tablename__ = 'orders'
    __table_args__ = (
        db.Index('ix_order_user_id', 'user_id'),
        db.Index('ix_order_area_id', 'area_id'),
    )

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="订单号（主键）")
    user_id: Mapped[int] = mapped_column(Integer,
                                         ForeignKey('user.user_id', name='fk_order_user_id'),
                                         nullable=False, comment="下单用户ID")
    area_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('dining_area.area_id',
                                                                       name='fk_order_area_id'),
                                                   nullable=True, comment="关联用餐区域ID（可选）")
    state: Mapped[OrderState] = mapped_column(DBEnum(OrderState, name="order_state_enum"),
                                              nullable=False, default=OrderState.PENDING,
                                              comment="订单状态")
    # --- 使用 Numeric 存储价格 ---
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"),
                                           comment="订单总金额")
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        DBEnum(PaymentMethod, name="payment_method_enum"), nullable=True, comment="支付方式")
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                     comment="支付凭证图片URL")  # 调整长度
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="订单创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="订单更新时间")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                           comment="删除时间（软删除）")

    # --- 关系定义 ---
    user: Mapped["User"] = relationship(back_populates="orders")  # 使用 Mapped 和字符串类型提示
    dining_area: Mapped[Optional["DiningArea"]] = relationship(back_populates="orders")
    # `cascade="all, delete-orphan"` 表示删除 Order 时，其关联的 OrderItem 也会被删除
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="order",
                                                          cascade="all, delete-orphan",
                                                          lazy="selectin")  # lazy='selectin' 可以在加载 Order 时高效加载 Items

    # --- 属性验证 ---
    @validates('price')
    def validate_order_price(self, _key, price_value):
        """
        验证服务层设置的总价（通常是计算好的）
        """
        try:
            price_decimal = Decimal(str(price_value))
        except (TypeError, InvalidOperation):
            raise ValueError("订单价格必须是有效的数字") from None
        if price_decimal < 0:
            # 理论上计算的总价不应为负，除非有退款等逻辑
            logger.warning(f"订单 {self.order_id} 的价格被设置为负数: {price_decimal}")
            # raise ValueError("订单总价不能为负数")
        return price_decimal

    @validates('image_url')
    def validate_image_url_format(self, _key, url):
        """
         简单的 URL 格式检查 (允许为空)
        """
        if url and not re.match(r"^https?://\S+$", url):
            raise ValueError("无效的图片 URL 格式")
        # 可以增加长度检查
        if url and len(url) > 255:
            raise ValueError("图片 URL 过长")
        return url

    # --- 实例方法 ---
    def to_dict(self, include_items=True) -> dict[str, Any]:
        """将订单对象转换为字典。"""
        data = {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "area_id": self.area_id,
            "state": self.state.value,  # 返回枚举值
            "price": str(self.price) if self.price is not None else "0.00",  # Decimal 转字符串
            "payment_method": self.payment_method.value if self.payment_method else None,
            "image_url": self.image_url,
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.astimezone(
                timezone.utc).isoformat() if self.deleted_at else None,
        }
        if include_items:
            data["order_items"] = [item.to_dict() for item in
                                   self.order_items] if self.order_items else []
        return data

    def calculate_total_price(self) -> Decimal:
        """根据已加载的订单项计算订单总价。"""
        if not self.order_items:
            return Decimal("0.00")
        # 确保 item.price 返回的是 Decimal
        total = sum(item.calculate_item_total() for item in self.order_items)
        return total if isinstance(total, Decimal) else Decimal(str(total))  # 确保返回 Decimal

    def can_be_canceled(self) -> bool:
        """检查订单当前状态是否允许被取消。"""
        return self.state == OrderState.PENDING

    def mark_as_canceled(self):
        """标记订单为已取消状态 (不 commit)。"""
        if self.can_be_canceled():
            self.state = OrderState.CANCELED
            # updated_at 由 onupdate 自动处理
            # self.updated_at = datetime.now(timezone.utc)
            logger.info(f"订单 {self.order_id} 已标记为 CANCELED。")
            return True  # 表示状态已修改
        logger.warning(f"尝试取消状态为 {self.state.name} 的订单 {self.order_id}。")
        return False  # 表示状态未修改

    def mark_as_deleted(self):
        """标记订单为软删除状态 (设置 deleted_at, 不 commit)。"""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(timezone.utc)
            logger.info(f"订单 {self.order_id} 已标记为软删除。")

    def restore(self):
        """恢复软删除的订单 (清除 deleted_at, 不 commit)。"""
        if self.deleted_at is not None:
            self.deleted_at = None
            logger.info(f"订单 {self.order_id} 已恢复。")

    def __repr__(self):
        return f"<Order(id={self.order_id}, user_id={self.user_id}, state='{self.state.name}')>"
