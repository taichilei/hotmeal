"""
@File       : order_routes.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Desc       : 订单相关的 API 端点。
@Version    : 1.0.0
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required  # 导入 get_jwt
from flask_restx import Namespace, Resource, fields

# 导入模型枚举，用于权限检查
from app.models.enums import UserRole

# 导入重构后的服务层模块
from app.services import order_service

# 导入装饰器和响应工具
from app.utils.decorators import log_request, require_roles, timing

# 导入错误码和异常 (供参考)
from app.utils.error_codes import ErrorCode
from app.utils.exceptions import AuthorizationError, ValidationError
from app.utils.response import (
    bad_request,
    created,
    no_content,
    server_error,  # 导入需要的响应函数
    success,
    unauthorized,
)

logger = logging.getLogger(__name__)

# --- Namespace 定义 ---
order_ns = Namespace('orders', description='订单管理操作', path='/orders')

# --- 输入/输出模型 ---

# 订单项输入模型 (用于创建订单)
dish_item_input_model = order_ns.model('DishItemInput', {
    'dish_id': fields.Integer(required=True, description='菜品 ID', example=1),
    'quantity': fields.Integer(required=True, description='数量 (必须大于0)', min=1, example=2)
})

# 创建订单的输入模型
order_create_model = order_ns.model('OrderCreateInput', {
    # user_id 通常从 token 获取
    'dish_list': fields.List(fields.Nested(dish_item_input_model), required=True,
                             description='订购的菜品列表 (至少包含一项)'),
    'area_id': fields.Integer(description='用餐区域 ID (可选)', example=1)
})

# 更新订单详情的输入模型 (管理员/员工)
order_update_model = order_ns.model('OrderUpdateInput', {
    'state': fields.String(description='订单状态 (例如: PAID, COMPLETED)', example='PAID'),
    'payment_method': fields.String(description='支付方式 (例如: WECHAT, ALIPAY)',
                                    example='WECHAT'),
    'image_url': fields.String(description='支付凭证图片 URL',
                               example='http://example.com/payment.jpg')
})

# 订单项输出模型 (用于订单详情)
order_item_output_model = order_ns.model('OrderItemOutput', {
    'order_item_id': fields.Integer(description='订单项 ID'),
    'dish_id': fields.Integer(description='菜品 ID'),
    'dish_name': fields.String(description='菜品名称'),
    'quantity': fields.Integer(description='数量'),
    'unit_price': fields.String(description='下单时单价 (字符串)'),
    'total': fields.String(description='该项总价 (字符串)')
})

# 订单输出模型
order_output_model = order_ns.model('OrderOutput', {
    'order_id': fields.Integer(description='订单 ID'),
    'user_id': fields.Integer(description='用户 ID'),
    'area_id': fields.Integer(description='区域 ID', allow_null=True),
    'state': fields.String(description='订单状态'),
    'price': fields.String(description='订单总金额 (字符串)'),
    'payment_method': fields.String(description='支付方式', allow_null=True),
    'image_url': fields.String(description='支付凭证 URL', allow_null=True),
    'created_at': fields.DateTime(description='创建时间 (ISO 格式)'),
    'updated_at': fields.DateTime(description='更新时间 (ISO 格式)'),
    'deleted_at': fields.DateTime(description='删除时间 (ISO 格式)', allow_null=True),
    'order_items': fields.List(fields.Nested(order_item_output_model), description='订单项列表',
                               required=False)
})

# 分页响应模型
pagination_model = order_ns.model('Pagination', {
    'page': fields.Integer(description='当前页码'),
    'per_page': fields.Integer(description='每页数量'),
    'total_items': fields.Integer(description='总项目数'),
    'total_pages': fields.Integer(description='总页数')
})

# 订单列表输出模型 (包含分页)
order_list_output_model = order_ns.model('OrderListOutput', {
    'items': fields.List(fields.Nested(order_output_model)),
    'page': fields.Integer(description='当前页码'),
    'per_page': fields.Integer(description='每页数量'),
    'total_items': fields.Integer(description='总项目数'),
    'total_pages': fields.Integer(description='总页数')
})


# --- 路由 ---



@order_ns.route('/me')
class UserOrderList(Resource):
    """获取当前登录用户的订单列表"""
    method_decorators = [jwt_required(), log_request, timing]

    @order_ns.doc('get_my_orders', security='jsonWebToken')
    @order_ns.param('include_items', '是否包含订单项详情 (true/false)', type=bool, default=False,
                    location='args')
    @order_ns.response(HTTPStatus.OK, '成功获取我的订单列表', [order_output_model])
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取订单失败')
    def get(self):
        """获取当前登录用户的订单列表"""
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。")

        include_items_str = request.args.get('include_items', 'false').lower()
        include_items = include_items_str == 'true'

        orders_data = order_service.get_orders_by_user(
            user_id=current_user_id,
            include_items=include_items
        )
        return success(message="成功获取我的订单列表", data=orders_data)


@order_ns.route("/")
class OrderList(Resource):
    """获取订单列表"""
    method_decorators = [log_request, timing]  # 应用于类中的所有方法

    @order_ns.doc('create_order', security='jsonWebToken')
    @order_ns.expect(order_create_model, validate=True)
    @order_ns.response(HTTPStatus.CREATED, '订单创建成功', order_output_model)
    @order_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效',
                       error_code=ErrorCode.HTTP_BAD_REQUEST)
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证', error_code=ErrorCode.HTTP_UNAUTHORIZED)
    @order_ns.response(HTTPStatus.NOT_FOUND, '用户、区域或菜品未找到',
                       error_code=ErrorCode.HTTP_NOT_FOUND)
    @order_ns.response(HTTPStatus.CONFLICT, '库存不足或菜品不可用',
                       error_code=ErrorCode.HTTP_CONFLICT)
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '创建订单失败',
                       error_code=ErrorCode.HTTP_INTERNAL_SERVER_ERROR)
    @jwt_required()
    def post(self):
        """创建新订单"""
        data = request.get_json()
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。")

        dish_list = data.get("dish_list", [])
        area_id = data.get("area_id")

        new_order_data = order_service.create_order(
            user_id=current_user_id,
            dish_list=dish_list,
            area_id=area_id
        )

        logger.info(f"用户 {current_user_id} 创建订单成功: ID={new_order_data.get('order_id')}")
        order_id = new_order_data.get('order_id')
        headers = {"Location": f"/orders/{order_id}"} if order_id else None
        return created(data=new_order_data, message="订单创建成功", headers=headers)

    @order_ns.doc('list_all_orders', security='jsonWebToken')
    @order_ns.param('page', '页码', type=int, default=1, location='args')
    @order_ns.param('per_page', '每页数量', type=int, default=10, location='args')
    @order_ns.param('include_items', '是否包含订单项详情', type=bool, default=False,
                    location='args')
    @order_ns.response(HTTPStatus.OK, '成功获取订单列表 (分页)', order_list_output_model)
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @order_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取列表失败')
    @jwt_required()
    @require_roles(["admin", "staff"])
    def get(self):
        """获取所有订单的分页列表 (仅管理员/员工)"""
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            if page <= 0 or per_page <= 0:
                raise ValidationError("页码和每页数量必须是正整数。")
        except ValueError:
            return bad_request("页码和每页数量参数必须是整数。")
        except ValidationError as ve:  # 捕获自己抛出的 ValidationError
            return bad_request(ve.message, error_code=ve.error_code)

        include_items_str = request.args.get('include_items', 'false').lower()
        include_items = include_items_str == 'true'

        try:
            logger.info(
                f"📥 list_all_orders called, page={page}, per_page={per_page}, include_items={include_items}")
            paginated_data = order_service.list_all_orders(
                page=page,
                per_page=per_page,
                include_items=include_items
            )
            return success(message="成功获取订单列表", data=paginated_data)
        except Exception as e:
            return server_error(f"获取订单列表失败: {e}",
                                error_code=ErrorCode.HTTP_INTERNAL_SERVER_ERROR)


@order_ns.route("/<int:order_id>")
@order_ns.param('order_id', '订单 ID')
@order_ns.response(HTTPStatus.NOT_FOUND, '订单未找到')
class OrderDetail(Resource):
    """获取订单详情"""
    method_decorators = [jwt_required(), log_request, timing]

    @order_ns.doc('get_order_detail', security='jsonWebToken')
    @order_ns.param('include_items', '是否包含订单项详情', type=bool, default=True, location='args')
    @order_ns.response(HTTPStatus.OK, '成功获取订单详情', order_output_model)
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @order_ns.response(HTTPStatus.FORBIDDEN, '无权查看此订单')
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取失败')
    @require_roles(["admin", "staff", "user"])
    def get(self, order_id):  # order_id 从 URL 传入
        """获取指定 ID 的订单详情 (管理员/员工或订单所有者)"""
        include_items_str = request.args.get('include_items', 'true').lower()
        include_items = include_items_str == 'true'

        order_data = order_service.get_order_by_id(
            order_id=order_id,  # 使用传入的 order_id
            include_items=include_items
        )
        return success(message="成功获取订单详情", data=order_data)

    @order_ns.doc('update_order_details', security='jsonWebToken')
    @order_ns.expect(order_update_model, validate=True)
    @order_ns.response(HTTPStatus.OK, '订单信息更新成功', order_output_model)
    @order_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效或状态转换无效')
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @order_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @order_ns.response(HTTPStatus.NOT_FOUND, '订单未找到')
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新失败')
    @require_roles(["admin", "staff"])
    def put(self, order_id):  # order_id 从 URL 传入
        """更新指定订单的信息 (状态、支付方式等，仅管理员/员工)"""
        update_data = request.get_json()
        if not update_data:
            return bad_request("请求体不能为空。")

        updated_order_data = order_service.update_order_details(
            order_id=order_id,  # 使用传入的 order_id
            update_data=update_data
        )
        logger.info(f"管理员/员工更新了订单 {order_id} 的信息。")
        return success(message="订单信息更新成功", data=updated_order_data)


@order_ns.route("/<int:order_id>/cancel")
@order_ns.param('order_id', '订单 ID')
class CancelOrder(Resource):
    """取消订单"""
    method_decorators = [jwt_required(), log_request, timing]

    @order_ns.doc('cancel_order', security='jsonWebToken')
    @order_ns.response(HTTPStatus.OK, '订单取消成功')
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @order_ns.response(HTTPStatus.FORBIDDEN, '无权取消此订单')
    @order_ns.response(HTTPStatus.NOT_FOUND, '订单未找到')
    @order_ns.response(HTTPStatus.CONFLICT, '订单状态无法取消')
    @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '取消失败')
    @require_roles(["admin", "staff", "user"])
    def put(self, order_id):
        """取消一个待处理的订单 (管理员/员工或订单所有者)"""
        try:
            current_user_id = int(get_jwt_identity())
            current_jwt = get_jwt()
            current_user_role = current_jwt.get("role")
            if not current_user_role:
                raise AuthorizationError("无法获取用户角色信息。")
        except (ValueError, TypeError, AuthorizationError):  # 捕获可能的错误
            # 如果 get_jwt_identity 或 get_jwt 出错，或者角色不存在
            return unauthorized("无效的用户令牌或角色信息。")

        order_service.cancel_order(
            order_id=order_id,
            operator_id=current_user_id,
            operator_role=current_user_role
        )

        logger.info(f"订单 {order_id} 已被用户 {current_user_id} (角色: {current_user_role}) 取消。")
        return success(message="订单取消成功")


@order_ns.route('/<int:order_id>/item/<int:order_item_id>')
@order_ns.param('order_id', '订单 ID')
@order_ns.param('order_item_id', '订单项 ID')
class OrderItemUpdate(Resource):
    """更新订单项"""
    method_decorators = [jwt_required(), log_request, timing]

    @order_ns.doc('update_order_item_quantity', security='jsonWebToken')
    @order_ns.expect(order_ns.model('UpdateOrderItemQuantity', {
        'quantity': fields.Integer(required=True, description='新数量')
    }), validate=True)
    @order_ns.response(HTTPStatus.OK, '订单项数量更新成功')
    @order_ns.response(HTTPStatus.BAD_REQUEST, '参数错误')
    @order_ns.response(HTTPStatus.UNAUTHORIZED, '未授权')
    @order_ns.response(HTTPStatus.FORBIDDEN, '无权修改此订单项')
    @order_ns.response(HTTPStatus.NOT_FOUND, '订单或订单项未找到')
    @order_ns.response(HTTPStatus.CONFLICT, '库存不足或订单状态不允许修改')
    def put(self, order_id, order_item_id):
        """更新指定订单项的数量"""
        data = request.get_json()
        quantity = data.get("quantity")

        if not isinstance(quantity, int) or quantity <= 0:
            return bad_request("无效的数量", error_code=ErrorCode.PARAM_INVALID.value)

        try:
            operator_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。", error_code=ErrorCode.HTTP_UNAUTHORIZED.value)

        updated_order = order_service.update_order_item_quantity(
            order_id=order_id,
            order_item_id=order_item_id,
            quantity=quantity,
            operator_id=operator_id
        )
        return success(message="订单项数量更新成功", data=updated_order)

    @order_ns.route("/<int:order_id>/delete")
    @order_ns.param('order_id', '订单 ID')
    class DeleteOrder(Resource):
        """删除订单"""
        method_decorators = [jwt_required(), log_request, timing]

        @order_ns.doc('delete_order', security='jsonWebToken')
        @order_ns.param('permanent', '是否永久删除 (true/false)，默认为软删除', type=bool,
                        default=False,
                        location='args')
        @order_ns.response(HTTPStatus.NO_CONTENT, '订单删除成功')
        @order_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
        @order_ns.response(HTTPStatus.FORBIDDEN, '无权删除此订单 (硬删除需要管理员)')
        @order_ns.response(HTTPStatus.NOT_FOUND, '订单未找到')
        @order_ns.response(HTTPStatus.CONFLICT, '无法删除，存在依赖或状态不允许')
        @order_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '删除失败')
        def delete(self, order_id):
            """删除订单 (管理员/员工或所有者可软删除, 仅管理员可硬删除)"""
            permanent_str = request.args.get('permanent', 'false').lower()
            permanent = permanent_str == 'true'

            try:
                current_user_id = int(get_jwt_identity())
                current_jwt = get_jwt()
                current_user_role = current_jwt.get("role")
                if not current_user_role:
                    raise AuthorizationError("无法获取用户角色信息。")
            except (ValueError, TypeError, AuthorizationError):
                return unauthorized("无效的用户令牌或角色信息。")

            if permanent:
                # 硬删除权限检查
                if current_user_role.upper() != UserRole.ADMIN.name:
                    # 抛出异常让全局处理器处理
                    raise AuthorizationError("只有管理员才能永久删除订单。",
                                             error_code=ErrorCode.FORBIDDEN.value)
                # 调用硬删除服务
                order_service.delete_order_hard(order_id=order_id)  # 使用传入的 order_id
                logger.info(f"管理员 {current_user_id} 永久删除了订单: ID={order_id}")
                return success(message="订单已永久删除")
            else:
                # 这里假设服务层会检查权限
                order_service.delete_order_soft(
                    order_id=order_id,  # 使用传入的 order_id
                    operator_id=current_user_id,
                    operator_role=current_user_role
                )
                logger.info(
                    f"订单 {order_id} 已被用户 {current_user_id} (角色: {current_user_role}) 软删除。")
                return no_content(message="订单已软删除")
