"""
@File       : tag_routes.py
@Author     : taichilei
@Date       : 2025-05-28
@Description: 提供标签管理的 API 路由
"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.services.tag_service import (
    create_tag,
    delete_tag,
    get_all_tags,
    get_tag_by_id,
    get_tag_list,
    update_tag,
)

# --- Namespace 定义 ---
# 保持路径为复数形式
tag_ns = Namespace('tags',
                   description='标签管理操作',
                   path='/tags')

# --- Model 定义 ---
tag_create_model = tag_ns.model('TagCreate', {
    'name': fields.String(required=True, description='标签名称')
})

tag_update_model = tag_ns.model('TagUpdate', {
    'name': fields.String(required=True, description='新的标签名称')
})


@tag_ns.route('')
class TagList(Resource):
    @tag_ns.doc('获取标签列表（可分页）')
    # @jwt_required()
    def get(self):
        """
        获取标签列表（支持分页和关键词搜索）
        """
        keyword = request.args.get('keyword', '')
        page = request.args.get('page', type=int)
        page_size = request.args.get('pageSize', type=int)

        if page is None or page_size is None:
            tags = get_all_tags()
            return [tag.to_dict() for tag in tags], 200

        tags, total = get_tag_list(keyword, page, page_size)
        return {
            'list': [tag.to_dict() for tag in tags],
            'total': total
        }, 200

    @tag_ns.doc('创建标签')
    # @jwt_required()
    @tag_ns.expect(tag_create_model)
    def post(self):
        """
        创建标签
        """
        data = request.json
        tag = create_tag(data['name'])
        return tag.to_dict(), 201


# 单个标签的增删改查
@tag_ns.route('/<int:tag_id>')
@tag_ns.param('tag_id', '标签ID')
class TagDetail(Resource):
    @tag_ns.doc('获取指定标签')
    # @jwt_required()
    def get(self, tag_id):
        """
        获取指定标签
        """
        tag = get_tag_by_id(tag_id)
        if tag:
            return tag.to_dict(), 200
        return {'message': '标签不存在'}, 404

    @tag_ns.doc('更新指定标签')
    # @jwt_required()
    @tag_ns.expect(tag_update_model)
    def put(self, tag_id):
        """
        更新指定标签
        """
        data = request.json
        tag = update_tag(tag_id, data['name'])
        if tag:
            return tag.to_dict(), 200
        return {'message': '标签不存在'}, 404

    @tag_ns.doc('删除指定标签')
    # @jwt_required()
    def delete(self, tag_id):
        """
        删除指定标签
        """
        tag = delete_tag(tag_id)
        if tag:
            return {'message': '标签已删除'}, 200
        return {'message': '标签不存在'}, 404
