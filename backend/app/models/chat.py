"""
File Name:     /app/models/chat.py
Project:       hotmeal
Author:        taichilei
Created:       2025-04-23
Description:   chat model
"""

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as DBEnum  # 导入 func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.enums import ChatStatus, MessageType
from app.utils.db import db

if TYPE_CHECKING:
    from .user import User

logger = logging.getLogger(__name__)


class Chat(db.Model):
    """
    聊天记录模型，映射到数据库的 'menu_chat' 表。
    """
    __tablename__ = 'menu_chat'
    __table_args__ = (
        db.Index('ix_chat_user_id', 'user_id'),
        db.Index('ix_chat_status', 'status'),
        db.Index('ix_chat_created_at', 'created_at'),
    )

    # --- 使用 Mapped 和 mapped_column ---
    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="聊天记录ID")
    # --- user_id 移除 default=-1，保持 nullable=False ---
    user_id: Mapped[int] = mapped_column(Integer,
                                         ForeignKey('user.user_id', name='fk_chat_user_id'),
                                         nullable=False, comment="所属用户ID")
    question: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                    comment="用户提出的问题或内容")  # 长度限制
    answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI或人工回答的内容")
    status: Mapped[ChatStatus] = mapped_column(DBEnum(ChatStatus, name="chat_status_enum"),
                                               nullable=False, default=ChatStatus.PENDING,
                                               comment="聊天状态")
    # --- 使用带时区的 DateTime 和数据库默认值 ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 server_default=func.now(), onupdate=func.now(),
                                                 comment="最后更新时间")
    response_time: Mapped[float | None] = mapped_column(Float, nullable=True,
                                                           comment="AI响应时间（秒）")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True,
                                                        comment="AI回答置信度")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="AI",
                                                  comment="回答来源：AI/人工")
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                comment="标签（逗号分隔）")  # 长度限制
    message_type: Mapped[MessageType] = mapped_column(DBEnum(MessageType, name="message_type_enum"),
                                                      nullable=False, default=MessageType.TEXT,
                                                      comment="消息类型")
    response_duration: Mapped[float | None] = mapped_column(Float, nullable=True,
                                                               comment="生成答案所耗时长（秒）")
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True,
                                                     comment="用户上传的图片链接")  # 长度限制

    # --- 关系定义 ---
    user: Mapped["User"] = relationship(
        backref=db.backref("user_chats", lazy="dynamic"))  # 使用 lazy='dynamic'

    # --- 移除自定义 __init__ ---

    # --- 使用 @validates 进行属性验证 ---
    @validates('question')
    def validate_question_length(self, _key, question):
        """
        验证问题长度。
        """
        if question and len(question) > 255:
            raise ValueError("问题内容不能超过255个字符")
        # 可以添加非空检查，但这通常在创建时由服务层保证
        # if not question:
        #     raise ValueError("问题内容不能为空")
        return question

    @validates('tags')
    def clean_and_validate_tags(self, _key, tags):
        """
        清理并验证标签。
        """
        if tags:
            # 清理并限制长度
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            cleaned_tags = ','.join(tags_list)
            if len(cleaned_tags) > 255:
                # 可以选择截断或抛异常
                logger.warning(f"聊天记录 {self.chat_id} 的标签过长，将被截断。原始: {tags}")
                return cleaned_tags[:255]
                # raise ValueError("标签总长度不能超过255个字符")
            return cleaned_tags
        return None  # 如果传入空字符串或 None，则存储 None

    @validates('image_url')
    def validate_image_url_format(self, _key, url):
        """
        验证图片 URL 格式。
        """
        if url and not re.match(r"^https?://\S+$", url):
            raise ValueError("无效的图片 URL 格式")
        if url and len(url) > 255:
            raise ValueError("图片 URL 不能超过255个字符")
        return url

    # --- 实例方法 ---
    def to_dict(self) -> dict[str, Any]:
        """将 Chat 实例转换为适合 JSON 序列化的字典。"""
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "question": self.question,
            "answer": self.answer,
            "status": self.status.value,  # 返回枚举的字符串值
            "created_at": self.created_at.astimezone(
                timezone.utc).isoformat() if self.created_at else None,
            "updated_at": self.updated_at.astimezone(
                timezone.utc).isoformat() if self.updated_at else None,
            "response_time": self.response_time,
            "confidence": self.confidence,
            "source": self.source,
            "tags": self.tags,
            "message_type": self.message_type.value,  # 返回枚举的字符串值
            "response_duration": self.response_duration,
            "image_url": self.image_url
            # 可以选择性添加用户信息
            # "username": self.user.username if self.user else None
        }

    def __repr__(self):
        return f"<Chat(id={self.chat_id}, user_id={self.user_id}, status='{self.status.name}')>"

    # --- 移除了所有服务层方法 ---
    # create, get_*, save, update, update_status, save_answer, delete
    # 也移除了 validate_question, clean_tags (逻辑移入 @validates 或服务层)
