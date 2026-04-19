"""
File Name:     /app/models/dish.py
Project:       hotmeal
Author:        taichilei
Created:       2025-04-23
Description:   dish model
"""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship, validates

from app.models.tag import Tag, dish_tags
from app.utils.db import db

if TYPE_CHECKING:
    from app.models.category import Category

logger = logging.getLogger(__name__)


# --- 将所有定义放在类内部 ---
class Dish(db.Model):
    """
    菜品模型类，映射到数据库的 'dish' 表。
    统一使用 'name' 作为属性名和列名。
    价格和评分使用 Decimal 类型。
    """
    __tablename__ = 'dish'
    __table_args__ = (
        Index('ix_dish_name', 'name'),  # 索引使用列名 'name'
        Index('ix_dish_category_id', 'category_id'),
        Index('ix_dish_is_available', 'is_available'),
    )

    # --- 使用 Mapped 和 mapped_column ---
    dish_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="菜品主键 ID")
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="菜品名称")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"),
                                           comment="菜品价格")
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="库存数量")
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                     comment="菜品图片链接")
    sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已售数量")
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("0.00"),
                                            comment="菜品评分 (0.00-5.00)")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                       comment="菜品描述")
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('category.category_id',
                                                                           name='fk_dish_category_id',
                                                                           ondelete="SET NULL"),
                                                       nullable=True, comment="所属分类ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="最后更新时间")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                               comment="是否上架")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                           comment="删除时间（软删除）")


    # --- 关系定义 ---
    # --- 直接使用 relationship 和 backref (从 sqlalchemy.orm 导入) ---
    category: Mapped[Optional["Category"]] = relationship("Category",
                                                          backref=backref("dishes", lazy="dynamic"))
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=dish_tags,
        backref=backref("dishes", lazy="dynamic")
    )

    @validates('name')
    def validate_name(self, _key, name_value):
        """
        validate_name 验证菜品名称是否有效。
        """
        if not name_value or not name_value.strip():
            raise ValueError("菜品名称不能为空")
        clean_name = name_value.strip()
        if len(clean_name) > 50:
            raise ValueError("菜品名称不能超过50个字符")
        return clean_name

    @validates('price')
    def validate_price(self, _key, price_value):
        """
        validate_price 验证价格是否有效。
        """
        try:
            price_decimal = Decimal(str(price_value))
        except (TypeError, InvalidOperation):
            raise ValueError("价格必须是有效的数字")
        if price_decimal < 0:
            raise ValueError("价格不能为负数")
        return price_decimal

    @validates('stock')
    def validate_stock(self, _key, stock_value):
        """
        validate_stock 验证库存是否有效。
        """
        if not isinstance(stock_value, int) or stock_value < 0:
            raise ValueError("库存必须是非负整数")
        return stock_value

    @validates('rating')
    def validate_rating(self, _key, rating_value):
        """
        validate_rating 验证评分是否有效。
        """
        if rating_value is None:
            return Decimal("0.00")
        try:
            rating_decimal = Decimal(str(rating_value))
        except (TypeError, InvalidOperation):
            raise ValueError("评分必须是有效的数字")
        if not (Decimal("0.00") <= rating_decimal <= Decimal("5.00")):
            raise ValueError("评分必须在 0.00 到 5.00 之间")
        return rating_decimal

    @validates('sales')
    def validate_sales(self, _key, sales_value):
        """
        validate_sales 验证销量是否有效。
        """
        if not isinstance(sales_value, int) or sales_value < 0:
            raise ValueError("销量必须是非负整数")
        return sales_value

    @validates('image_url')
    def validate_image_url(self, _key, url):
        """
        validate_image_url 验证图片 URL 是否有效。
        """
        if url and not re.match(r"^https?://\S+$", url):
            raise ValueError("无效的图片 URL 格式")
        if url and len(url) > 255:
            raise ValueError("图片 URL 不能超过255个字符")
        return url

    # --- 实例方法 ---
    def __repr__(self):
        return f"<Dish {self.name} (ID: {self.dish_id}, Price: {self.price:.2f}, Stock: {self.stock})>"

    def to_dict(self, include_category_name: bool = True) -> dict[str, Any]:
        """将菜品对象转换为适合 JSON 序列化的字典。"""
        data = {
            "dish_id": self.dish_id,
            "name": self.name,
            "price": str(self.price) if self.price is not None else "0.00",
            "stock": self.stock,
            "image_url": self.image_url,
            "sales": self.sales,
            "rating": str(self.rating) if self.rating is not None else "0.00",
            "description": self.description,
            "category_id": self.category_id,
            "is_available": self.is_available,
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.astimezone(
                timezone.utc).isoformat() if self.deleted_at else None,
        }
        data["tags"] = [tag.name for tag in self.tags] if self.tags else []
        if include_category_name:
            category_obj = self.category  # 触发加载 (如果需要)
            data["category_name"] = category_obj.name if category_obj else None
        return data

    def mark_as_deleted(self):
        """标记菜品为软删除状态 (设置 deleted_at 并下架，不 commit)。"""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(timezone.utc)
            self.is_available = False
            logger.info(f"菜品 {self.dish_id} ('{self.name}') 已标记为软删除。")

    def mark_as_available(self, available: bool):
        """设置菜品的上架/下架状态 (不 commit)。"""
        if self.is_available is not available:
            self.is_available = available
            if available and self.deleted_at is not None:
                logger.warning(f"菜品 {self.dish_id} ('{self.name}') 重新上架，但仍有软删除标记。")
                # self.deleted_at = None # 可选：如果上架意味着恢复软删除
            # updated_at 由 onupdate 自动处理
            logger.info(f"菜品 {self.dish_id} ('{self.name}') 的可用状态已设置为 {available}。")
