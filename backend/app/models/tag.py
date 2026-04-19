"""
@file         app/models/tag.py
@description  （这里写这个模块/脚本的功能简述）
@date         2025-05-24
@author       taichilei
"""

# app/models/tag.py
from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db import db

# 中间表：多对多关系
dish_tags = Table(
    'dish_tags',
    db.metadata,
    Column('dish_id', Integer, ForeignKey('dish.dish_id', ondelete="CASCADE")),
    Column('tag_id', Integer, ForeignKey('tag.tag_id', ondelete="CASCADE")),
    Index('ix_dish_tag_dish_id', 'dish_id'),
    Index('ix_dish_tag_tag_id', 'tag_id')
)


# Tag 模型
class Tag(db.Model):
    """
    Tag 模型
    """
    __tablename__ = 'tag'
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, comment="标签名称")

    def __repr__(self):
        return f"<Tag {self.name}>"

    def to_dict(self):
        """
        将 Tag 模型转化为字典
        """
        return {
            "tag_id": self.tag_id,
            "name": self.name
        }
