"""
@File       : tag_service.py
@Author     : ChiLei Tai JOU
@Date       : 2025-05-28
@Description: 标签服务层，处理标签的创建、查询、更新和删除
"""

from app.models import db
from app.models.tag import Tag


def get_all_tags():
    """
    获取所有标签（无分页，用于表单下拉或非分页场景）
    """
    return Tag.query.all()


def create_tag(name):
    """
    创建标签
    """
    tag = Tag(name=name)
    db.session.add(tag)
    db.session.commit()
    return tag


def get_tag_by_id(tag_id):
    """
    根据标签ID查询标签
    """
    return Tag.query.get(tag_id)


def update_tag(tag_id, new_name):
    """
    根据标签ID修改标签名称
    """
    tag = Tag.query.get(tag_id)
    if tag and tag.name != new_name:
        tag.name = new_name
        db.session.commit()
    elif tag:
        # 强制标记字段已修改，避免被 SQLAlchemy 跳过
        from sqlalchemy.orm.attributes import flag_modified
        tag.name = new_name
        flag_modified(tag, "name")
        db.session.commit()
    return tag


def delete_tag(tag_id):
    """
    根据标签ID删除标签
    """
    tag = Tag.query.get(tag_id)
    if tag:
        db.session.delete(tag)
        db.session.commit()
    return tag


def get_tag_list(keyword=None, page=1, page_size=10):
    """
    获取分页标签列表，支持关键词搜索（用于后台管理界面）
    """
    query = Tag.query
    if keyword:
        query = query.filter(Tag.name.ilike(f'%{keyword}%'))
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    return pagination.items, pagination.total
