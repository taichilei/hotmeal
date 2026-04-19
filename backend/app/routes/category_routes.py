"""
@File       : category_routes.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Desc       : 分类相关的 API 端点。
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

# 导入重构后的服务层模块
from app.services import category_service

# 导入装饰器和响应工具
from app.utils.decorators import (  # 移除 validate_json
    log_request,
    require_roles,
    timing,
)
from app.utils.response import (  # 导入需要的响应函数
    bad_request,
    created,
    no_content,
    success,
)

logger = logging.getLogger(__name__)

# --- Namespace 定义 ---
# 保持路径为复数形式
category_ns = Namespace('categories',
                        description='分类管理操作',
                        path='/categories')

# --- 输入/输出模型 ---

# 创建分类时的输入模型
category_create_model = category_ns.model('CategoryCreateInput', {
    'name': fields.String(required=True, description='分类名称 (必须唯一)', min_length=1,
                          max_length=50, example='热菜'),
    'description': fields.String(description='分类描述', example='各种炒菜、炖菜等'),
    'img_url': fields.String(description='图片链接 (URL)', required=False, allow_null=True,
                             example='http://example.com/hotdish.jpg'),
    'parent_category_id': fields.Integer(description='父分类 ID (可选, 用于创建子分类)',
                                         required=False, allow_null=True, example=1)
})

# 更新分类时的输入模型 (所有字段可选)
category_update_model = category_ns.model('CategoryUpdateInput', {
    'name': fields.String(description='新分类名称', min_length=1, max_length=50,
                          example='精品热菜'),
    'description': fields.String(description='新分类描述'),
    'img_url': fields.String(description='新图片链接'),
    'parent_category_id': fields.Integer(description='新的父分类 ID (设置 null 表示顶级分类)',
                                         required=False, allow_null=True)
})

# 分类信息的输出模型 (与 _serialize_category 对应)
category_output_model = category_ns.model('CategoryOutput', {
    'category_id': fields.Integer(description='分类 ID'),
    'name': fields.String(description='分类名称'),
    'description': fields.String(description='描述'),
    'img_url': fields.String(description='图片 URL'),
    'parent_category_id': fields.Integer(description='父分类 ID', allow_null=True),
    'subcategories_count': fields.Integer(description='子分类数量'),  # 从序列化函数添加
    'created_at': fields.DateTime(description='创建时间 (ISO 格式)'),
    'updated_at': fields.DateTime(description='更新时间 (ISO 格式)'),
    'deleted_at': fields.DateTime(description='删除时间 (ISO 格式)', allow_null=True)
})


# --- 路由 ---

@category_ns.route("/")  # 对应 /categories/
class CategoryList(Resource):

    @category_ns.doc('create_category', security='jsonWebToken')
    @category_ns.expect(category_create_model, validate=True)  # 使用 expect 进行输入验证
    @category_ns.response(HTTPStatus.CREATED, '分类创建成功', category_output_model)
    @category_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @category_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @category_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @category_ns.response(HTTPStatus.CONFLICT, '分类名称已存在')
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '创建失败')
    @jwt_required()
    @require_roles(["admin"])  # 仅管理员可创建
    @log_request
    @timing
    def post(self):
        """创建新分类 (仅管理员)"""
        data = request.get_json()

        # 调用服务层函数，它会在失败时抛出异常
        new_category_data = category_service.create_category(
            name=data.get("name"),
            description=data.get("description"),
            img_url=data.get("img_url"),
            parent_category_id=data.get("parent_category_id")  # 传递父 ID
        )

        # 服务层成功返回字典数据
        logger.info(
            f"管理员创建分类: ID={new_category_data.get('category_id')}, Name='{new_category_data.get('name')}'")
        return created(data=new_category_data, message="分类创建成功")

    @category_ns.doc('list_categories')
    @category_ns.param('include_deleted', '是否包含已删除的分类 (true/false)', type=bool,
                       default=False, location='args')
    @category_ns.param('parent_id', '按父分类 ID 过滤 (不传表示获取顶级分类)', type=int,
                       location='args')
    @category_ns.response(HTTPStatus.OK, '成功获取分类列表', [category_output_model])  # 返回列表
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取列表失败')
    # 考虑是否需要登录才能查看分类列表？如果需要，添加 @jwt_required()
    # @jwt_required() # 取决于业务需求
    @log_request
    @timing
    def get(self):
        """获取分类列表 (可选按父 ID 过滤，可选包含已删除)"""
        # 获取查询参数
        include_deleted_str = request.args.get('include_deleted', 'false').lower()
        include_deleted = include_deleted_str == 'true'

        parent_id_str = request.args.get('parent_id')
        parent_id = None
        if parent_id_str is not None:  # 注意检查是否为 None，因为 0 是有效 ID
            try:
                parent_id = int(parent_id_str)
            except ValueError:
                return bad_request("parent_id 参数必须是整数。")

        # 调用服务层函数
        categories_data = category_service.get_all_categories(
            include_deleted=include_deleted,
            parent_id=parent_id
        )

        logger.info(f"获取分类列表: {len(categories_data)} 个。"
                    f"{' (含已删除)' if include_deleted else ''}"
                    f"{' Parent ID: ' + str(parent_id) if parent_id is not None else ' (顶级)'}")
        return success(message="成功获取分类列表", data=categories_data)


@category_ns.route("/<int:category_id>")  # 对应 /categories/{category_id}
@category_ns.param('category_id', '分类 ID')
class CategoryDetail(Resource):

    @category_ns.doc('get_category_detail')
    @category_ns.param('include_deleted', '是否包含已删除的分类 (true/false)', type=bool,
                       default=False, location='args')
    @category_ns.response(HTTPStatus.OK, '成功获取分类详情', category_output_model)
    @category_ns.response(HTTPStatus.NOT_FOUND, '分类未找到')
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取详情失败')
    # 考虑是否需要登录？
    # @jwt_required()
    @log_request
    @timing
    def get(self, category_id):
        """获取指定 ID 的分类详情 (可选包含已删除)"""
        include_deleted_str = request.args.get('include_deleted', 'false').lower()
        include_deleted = include_deleted_str == 'true'

        # 服务层函数在未找到时抛出 NotFoundError
        category_data = category_service.get_category_by_id(
            category_id=category_id,
            include_deleted=include_deleted
        )

        logger.info(f"获取分类详情: ID={category_id}, Name='{category_data.get('name')}'")
        return success(message="成功获取分类详情", data=category_data)

    @category_ns.doc('update_category', security='jsonWebToken')
    @category_ns.expect(category_update_model, validate=True)  # 使用 expect 进行输入验证
    @category_ns.response(HTTPStatus.OK, '分类更新成功', category_output_model)
    @category_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @category_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @category_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @category_ns.response(HTTPStatus.NOT_FOUND, '分类未找到')
    @category_ns.response(HTTPStatus.CONFLICT, '分类名称已存在或父分类无效')
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新失败')
    @jwt_required()
    @require_roles(["admin"])  # 仅管理员可更新
    @log_request
    @timing
    def put(self, category_id):
        """更新指定 ID 的分类信息 (仅管理员)"""
        update_data = request.get_json()
        if not update_data:
            return bad_request("请求体不能为空。")

        # 调用服务层函数，它会在失败时抛出异常
        updated_category_data = category_service.update_category(
            category_id=category_id,
            update_data=update_data
        )

        logger.info(f"管理员更新分类: ID={category_id}")
        return success(message="分类更新成功", data=updated_category_data)

    @category_ns.doc('delete_category', security='jsonWebToken')
    @category_ns.param('permanent', '是否永久删除 (true/false)，默认为软删除', type=bool,
                       default=False, location='args')
    @category_ns.response(HTTPStatus.NO_CONTENT, '分类删除成功')
    @category_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @category_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @category_ns.response(HTTPStatus.NOT_FOUND, '分类未找到')
    @category_ns.response(HTTPStatus.CONFLICT, '无法删除，存在子分类或关联数据')
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '删除失败')
    @jwt_required()
    @require_roles(["admin"])  # 仅管理员可删除
    @log_request
    @timing
    def delete(self, category_id):
        """删除指定 ID 的分类 (默认为软删除，可选永久删除，仅管理员)"""
        permanent_str = request.args.get('permanent', 'false').lower()
        permanent = permanent_str == 'true'

        if permanent:
            # 调用永久删除服务
            category_service.delete_category_permanently(category_id)
            logger.info(f"管理员永久删除了分类: ID={category_id}")
            return no_content(message="分类已永久删除")
        else:
            # 调用软删除服务
            category_service.soft_delete_category(category_id)
            logger.info(f"管理员软删除了分类: ID={category_id}")
            return no_content(message="分类已软删除")  # 软删除也返回 204


# --- 额外的管理接口：恢复软删除的分类 ---
@category_ns.route("/<int:category_id>/restore")
@category_ns.param('category_id', '分类 ID')
class RestoreCategory(Resource):

    @category_ns.doc('restore_category', security='jsonWebToken')
    @category_ns.response(HTTPStatus.OK, '分类恢复成功', category_output_model)
    @category_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @category_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @category_ns.response(HTTPStatus.NOT_FOUND, '分类未找到或无需恢复')
    @category_ns.response(HTTPStatus.CONFLICT, '无法恢复（例如父分类已删除）')
    @category_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '恢复失败')
    @jwt_required()
    @require_roles(["admin"])  # 仅管理员可恢复
    @log_request
    @timing
    def post(self, category_id):  # 使用 POST 或 PUT 来执行恢复操作
        """恢复软删除的分类 (仅管理员)"""
        # 调用恢复服务
        restored_category_data = category_service.restore_category(category_id)

        logger.info(f"管理员恢复了分类: ID={category_id}")
        return success(message="分类恢复成功", data=restored_category_data)
