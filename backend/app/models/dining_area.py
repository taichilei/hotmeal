"""
@File       : dining_area.py
@Author     : taichilei
@Date       : 2025-04-23
@Description: 用餐区域数据模型
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as DBEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.enums import AreaType, DiningAreaState
from app.utils.db import db

# 处理循环类型提示
if TYPE_CHECKING:
    from .order import Order
    from .user import User

logger = logging.getLogger(__name__)


class DiningArea(db.Model):
    """
    用餐区域模型，代表餐厅中的桌位或包间。
    """
    __tablename__ = 'dining_area'
    __table_args__ = (
        db.Index('ix_dining_area_name', 'area_name'),  # 添加索引
        db.Index('ix_dining_area_type', 'area_type'),
        db.Index('ix_dining_area_state', 'state'),
    )

    # --- 使用 Mapped 和 mapped_column ---
    area_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,
                                         comment="区域ID")
    area_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True,
                                           comment="区域名称")  # 名称通常需要唯一
    state: Mapped[DiningAreaState] = mapped_column(
        DBEnum(DiningAreaState, name="dining_area_state_enum"), nullable=False,
        default=DiningAreaState.FREE, comment="区域状态：FREE空闲/OCCUPIED占用")
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True,
                                                        comment="区域最大容纳人数")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0,
                                             comment="区域使用次数")
    # 外键关联到 User 模型
    assigned_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('user.user_id',
                                                                                name='fk_dining_area_user_id'),
                                                            nullable=True, comment="当前占用用户ID")
    area_type: Mapped[AreaType] = mapped_column(DBEnum(AreaType, name="area_type_enum"),
                                                nullable=False, default=AreaType.TABLE,
                                                comment="区域类型")
    # 使用带时区的 DateTime 和 server_default
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="创建时间")
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                          comment="上一次使用时间")
    # updated_at 通常也需要
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="最后更新时间")

    # --- 关系定义 ---
    # 当前占用该区域的用户 (一对多关系的反向)
    assigned_user: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_user_id],
                                                           backref="assigned_areas")  # 使用 assigned_user 区分 User 的其他关系
    # 该区域发生过的所有订单 (一对多关系)
    orders: Mapped[list["Order"]] = relationship(back_populates="dining_area",
                                                 lazy="dynamic")

    # --- 使用 @validates 进行属性验证 ---
    @validates('area_name')
    def validate_area_name(self, _key, name):
        """
        validate_area_name 验证区域名称
        """
        if not name or not name.strip():
            raise ValueError("区域名称不能为空")
        clean_name = name.strip()
        if len(clean_name) > 50:
            raise ValueError("区域名称不能超过50个字符")
        # 唯一性检查应在服务层或依赖数据库约束
        return clean_name

    @validates('max_capacity')
    def validate_max_capacity(self, _key, capacity):
        """
        允许 capacity 为 None
        """
        #
        if capacity is not None:
            if not isinstance(capacity, int) or capacity <= 0:
                raise ValueError("最大容量必须是正整数")
        return capacity

    # assigned_user_id 的验证（用户是否存在）应在服务层进行

    # --- 实例方法 ---
    def to_dict(self) -> dict[str, Any]:
        """将用餐区域对象转换为字典。"""
        return {
            "area_id": self.area_id,
            "area_name": self.area_name,
            "state": self.state.value,
            "area_type": self.area_type.value,
            "max_capacity": self.max_capacity,
            "usage_count": self.usage_count,
            "assigned_user_id": self.assigned_user_id,
            # 格式化时间戳为 ISO 格式 (带 UTC 时区)
            "last_used": self.last_used.astimezone(
                timezone.utc).isoformat() if self.last_used else None,
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            # 可以选择性添加关联信息，如占用用户名
            "assigned_username": self.assigned_user.username if self.assigned_user else None
        }

    def mark_as_occupied(self, user_id: int):
        """标记区域为占用状态 (不 commit)。"""
        if self.state == DiningAreaState.FREE:
            self.state = DiningAreaState.OCCUPIED
            self.assigned_user_id = user_id
            self.usage_count += 1
            self.last_used = datetime.now(timezone.utc)  # 使用 UTC 时间
            logger.info(
                f"区域 {self.area_id} ('{self.area_name}') 已标记为 OCCUPIED，分配给用户 {user_id}。")
            return True
        else:
            logger.warning(
                f"尝试占用状态不为 FREE 的区域 {self.area_id} (当前状态: {self.state.name})。")
            return False

    def mark_as_free(self):
        """标记区域为空闲状态 (不 commit)。"""
        if self.state == DiningAreaState.OCCUPIED:
            original_user_id = self.assigned_user_id
            self.state = DiningAreaState.FREE
            self.assigned_user_id = None
            # usage_count 和 last_used 在分配时更新
            # self.last_used = datetime.now(timezone.utc) # 如果释放也算使用的话
            logger.info(
                f"区域 {self.area_id} ('{self.area_name}') 已标记为 FREE (原用户 ID: {original_user_id})。")
            return True
        else:
            logger.info(f"区域 {self.area_id} ('{self.area_name}') 已是 FREE 状态，无需释放。")
            return True  # 幂等性

    def __repr__(self) -> str:
        return f"<DiningArea(area_id={self.area_id}, area_name='{self.area_name}', state={self.state.name})>"

    # --- 移除了所有服务层方法 ---
    # create_area, get_*, save_to_db, get_free_areas, assign_area, release_area, delete_area
