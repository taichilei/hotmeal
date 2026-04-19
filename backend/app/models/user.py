"""
@File       : user.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 用户模型类，定义用户属性、关系和基础验证。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms
@Version    : 1.0.0，移除服务层逻辑
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy import Enum as DBEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.enums import UserRole, UserStatus
from app.utils.db import db

# 处理循环引用
if TYPE_CHECKING:
    from .chat import Chat
    from .dining_area import DiningArea
    from .order import Order

logger = logging.getLogger(__name__)


class User(db.Model):
    """
    用户模型。
    包含账户信息、密码哈希、角色、状态、时间戳和偏好。
    """
    __tablename__ = 'user'
    __table_args__ = (
        Index('ix_user_account', 'account'),
        Index('ix_user_phone_number', 'phone_number'),
        Index('ix_user_email', 'email'),
        Index('ix_user_status', 'status'),
        Index('ix_user_role', 'role'),
    )

    # --- 使用 Mapped 和 mapped_column ---
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[str] = mapped_column(String(255), nullable=False, unique=True,
                                         comment="登录账号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False,
                                               comment="密码哈希 (Werkzeug)")
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True,
                                                        comment="手机号")  # 调整长度
    username: Mapped[str | None] = mapped_column(String(50), nullable=True,
                                                    comment="昵称/显示名称")  # 调整长度
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                      comment="用户头像URL")
    email: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True,
                                                 comment="邮箱")  # 邮箱通常唯一
    role: Mapped[UserRole] = mapped_column(DBEnum(UserRole, name="user_role_enum"), nullable=False,
                                           default=UserRole.USER,
                                           server_default=UserRole.USER.value, comment="用户角色")
    status: Mapped[UserStatus] = mapped_column(DBEnum(UserStatus, name="user_status_enum"),
                                               nullable=False, default=UserStatus.ACTIVE,
                                               server_default=UserStatus.ACTIVE.value,
                                               comment="用户状态")
    favorite_cuisine: Mapped[str | None] = mapped_column(String(50), nullable=True,
                                                            comment="用户偏好的菜系")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="最后更新时间")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                           comment="删除时间（软删除）")

    # --- 关系定义 ---
    # 注意：如果 User 和 Order/DiningArea/Chat 有双向关系，需要在对方模型中定义 back_populates
    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="dynamic")
    # 一个用户当前可能只占用一个区域
    occupied_area: Mapped[Optional["DiningArea"]] = relationship(back_populates="assigned_user",
                                                                 foreign_keys="DiningArea.assigned_user_id",
                                                                 uselist=False)  # use-list=False 表示一对一或多对一的反向
    chats: Mapped[list["Chat"]] = relationship(back_populates="user", lazy="dynamic")

    # --- 密码处理方法 ---
    def set_password(self, password: str):
        """设置密码，自动进行哈希。"""
        if not password or len(password) < 6:  # 添加基本的密码复杂度要求（示例）
            raise ValueError("密码不能为空且长度至少为 6 位")
        self.password_hash = generate_password_hash(password)
        logger.debug(f"用户 {self.account} 的密码已设置哈希。")

    def check_password(self, password: str) -> bool:
        """校验输入的密码是否与存储的哈希匹配。"""
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # --- 使用 @validates 进行属性验证 ---
    @validates('account')
    def validate_account(self, _key, account_value):
        """
        validate_account 验证账号字段。
        """
        if not account_value or not account_value.strip():
            raise ValueError("account field cannot be empty")
        clean_account = account_value.strip()
        if len(clean_account) > 255:  # 根据列定义调整
            raise ValueError("account 字段长度不能超过 255 个字符")
        return clean_account

    @validates('username')
    def validate_username(self, _key, username_value):
        """
        validate_username 验证昵称字段。
        """
        if username_value and len(username_value.strip()) > 50:
            raise ValueError("username 不能超过50个字符")
        return username_value.strip() if username_value else None

    @validates('email')
    def validate_email(self, _key, email_value):
        """验证邮箱格式。"""
        if email_value:
            clean_email = email_value.strip().lower()
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", clean_email):
                raise ValueError("invalid email format")
            if len(clean_email) > 120:
                raise ValueError("email 字段长度不能超过 120 个字符")
            return clean_email
        return None

    @validates('phone_number')
    def validate_phone_number(self, _key, phone_value):
        """验证手机号格式（支持国际号码，允许 '+' 前缀）"""
        if phone_value:
            clean_phone = phone_value.strip()
            if not re.match(r"^\+?\d{6,20}$", clean_phone):
                raise ValueError("invalid 手机号格式")
            return clean_phone
        return None

    @validates('favorite_cuisine')
    def validate_favorite_cuisine(self, _key, cuisine):
        """验证偏好菜系。"""
        if cuisine and len(cuisine.strip()) > 50:
            raise ValueError("偏好菜系名称不能超过50个字符")
        return cuisine.strip() if cuisine else None

    # --- 辅助方法 ---
    def has_role(self, role: UserRole) -> bool:
        """检查用户是否拥有指定角色。"""
        return self.role == role

    def is_admin(self) -> bool:
        """检查用户是否为管理员。"""
        return self.role == UserRole.ADMIN

    def is_staff(self) -> bool:
        """检查用户是否为员工。"""
        return self.role == UserRole.STAFF

    def is_active(self) -> bool:
        """检查用户是否处于活动状态。"""
        return self.status == UserStatus.ACTIVE and self.deleted_at is None

    def to_dict(self) -> dict[str, Any]:
        """将 User 对象转换为适合 JSON 序列化的字典。"""
        return {
            "user_id": self.user_id,
            "account": self.account,
            "role": self.role.value,  # 使用 .value 获取枚举的字符串值
            "status": self.status.value,
            "phone_number": self.phone_number,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "username": self.username,
            "favorite_cuisine": self.favorite_cuisine,
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.astimezone(
                timezone.utc).isoformat() if self.deleted_at else None,
        }

    # --- 状态修改方法 (不 commit) ---
    def mark_as_deleted(self):
        """标记用户为软删除状态。"""
        if self.deleted_at is None:
            self.deleted_at = datetime.now(timezone.utc)
            self.status = UserStatus.DELETED  # 同时更新状态
            logger.info(f"用户 {self.account} (ID: {self.user_id}) 已标记为软删除。")

    def restore(self):
        """恢复软删除或禁用的用户到活动状态。"""
        if self.deleted_at is not None or self.status == UserStatus.BANNED:
            self.deleted_at = None
            self.status = UserStatus.ACTIVE  # 恢复为活动状态
            logger.info(f"用户 {self.account} (ID: {self.user_id}) 已恢复为活动状态。")

    def ban(self):
        """禁用用户。"""
        if self.status != UserStatus.BANNED:
            self.status = UserStatus.BANNED
            # 软删除标记可以保留，也可以清除，取决于业务逻辑
            # self.deleted_at = None
            logger.info(f"用户 {self.account} (ID: {self.user_id}) 已被禁用。")

    # --- 调试信息表示 ---
    def __repr__(self) -> str:
        # self.role 是 UserRole 枚举类型，.name 返回如 'ADMIN'，用于更清晰的日志输出
        return f"<User(id={self.user_id}, account='{self.account}', role='{self.role.name}')>"
