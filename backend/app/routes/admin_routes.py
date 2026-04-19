"""
@File       : admin_routes.py
@Date       : 2025-03-01 和版本
@Desc       : 处理管理员专属功能的 API 端点。 # 修正描述

@Version    : 1.0.0
@Copyright  : Copyright © 2025. All rights reserved.
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required  # 导入 jwt_required
from flask_restx import Namespace, Resource, fields

from app.models.enums import UserRole, UserStatus  # 导入 UserRole 枚举
from app.routes.user_routes import user_model
from app.services import user_service
from app.services.user_service import get_all_users

# --- 修正导入路径 ---
from app.utils.decorators import log_request, require_roles, timing  # 导入需要的装饰器
from app.utils.response import bad_request, no_content, success, unauthorized

logger = logging.getLogger(__name__)  # 添加 logger

# --- Namespace 定义 ---
# 可以保持原样，或改为小写 'admin'
admin_ns = Namespace("users", description="管理员专属接口", path='/users')  # 改为小写，路径通常也是小写

admin_user_update_model = admin_ns.model('AdminUserUpdate', {
    'account': fields.String(description='新账号名', max_length=255),
    'password': fields.String(description='新密码 (可选, 将被哈希)', min_length=6),
    'role': fields.String(description='新角色', enum=[role.name for role in UserRole]),
    'email': fields.String(description='新邮箱地址', max_length=120),
    'phone_number': fields.String(description='新手机号', max_length=20),
    'username': fields.String(description='新显示用户名', max_length=50),
    'status': fields.String(description='新状态', enum=[status.name for status in UserStatus]),
    'favorite_cuisine': fields.String(description='偏好的菜系', max_length=50)
})


# --- Admin 专属资源 ---

@admin_ns.route('/users')
class AdminUserList(Resource):
    method_decorators = [jwt_required(), require_roles([UserRole.ADMIN.name]), log_request, timing]

    @admin_ns.doc('admin_list_users', security='jsonWebToken')
    def get(self):
        """列出所有活跃用户 (仅管理员)"""
        all_users_data = get_all_users()
        return success(message="Active users retrieved successfully", data=all_users_data)


# @admin_ns.route('/staff')
# class AdminStaffList(Resource):
#     method_decorators = [jwt_required(), require_roles([UserRole.ADMIN.name]), log_request, timing]
#
#     @admin_ns.doc('admin_list_staff', security='jsonWebToken')
#     def get(self):
#         """列出所有员工角色的用户 (仅限管理员)"""
#         staff_users = get_users_by_role(UserRole.STAFF.name)
#         return success(message="Staff users retrieved successfully", data=staff_users)


@admin_ns.route("/admin")
class AdminPermissionTest(Resource):
    # --- 添加 jwt_required() 并修正 require_roles ---
    # 应用装饰器的顺序通常是：日志 -> 认证 -> 授权 -> 其他
    method_decorators = [
        log_request,
        timing,
        jwt_required(),  # 必须先验证登录
        require_roles([UserRole.ADMIN.name])  # 使用枚举名称
    ]

    @admin_ns.doc('admin_permission_test', security='jsonWebToken')  # 添加文档
    @admin_ns.response(HTTPStatus.OK, '权限验证通过')
    @admin_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @admin_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    def get(self):
        """
        测试管理员权限的接口。
        只有拥有 ADMIN 角色的用户才能访问。
        """
        logger.info("管理员权限测试接口被成功访问。")
        # success 函数默认 error_code 是 0 (ErrorCode.SUCCESS)， message 是 "Operation succeeded"
        # 可以简化调用
        return success(data="Access granted")  # 返回更具体的消息和数据


# ------------------------
# 获取所有员工列表接口 /staff
# ------------------------


# --- Admin 用户详情管理 ---
@admin_ns.route('/users/<int:user_id>')
@admin_ns.param('user_id', '要管理的用户 ID')
class AdminUserDetailResource(Resource):
    method_decorators = [log_request, timing, jwt_required(), require_roles([UserRole.ADMIN.name])]

    @admin_ns.doc('admin_get_user', security='jsonWebToken', tags=['Admin'])
    @admin_ns.response(HTTPStatus.OK, '用户已找到', user_model)
    @admin_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @admin_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @admin_ns.response(HTTPStatus.NOT_FOUND, 'User not found')
    @admin_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取用户失败')
    def get(self, user_id):
        """获取指定用户的详细信息 (仅管理员)"""
        user_data = user_service.get_user_by_id(user_id)
        return success(message="User retrieved successfully", data=user_data)

    @admin_ns.doc('admin_delete_user', security='jsonWebToken', tags=['Admin'])
    @admin_ns.response(HTTPStatus.NO_CONTENT, 'User deleted successfully')
    @admin_ns.response(HTTPStatus.UNAUTHORIZED, 'Authentication required')
    @admin_ns.response(HTTPStatus.FORBIDDEN, 'Admin privileges required')
    @admin_ns.response(HTTPStatus.NOT_FOUND, 'User not found')
    @admin_ns.response(HTTPStatus.CONFLICT, 'Cannot delete user, possibly due to related data')
    @admin_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, 'Deletion failed')
    def delete(self, user_id):
        """Permanently deletes a specific user (hard delete, admin only)"""
        operator_id = 'unknown'
        try:
            op_id_str = get_jwt_identity()
            if op_id_str:
                operator_id = str(op_id_str)
        except Exception as ex:
            logger.warning(
                f"Could not reliably get operator ID for logging deletion of user {user_id}: {ex}")

        user_service.delete_user(user_id)
        logger.info(f"Admin (ID: {operator_id}) permanently deleted user with ID: {user_id}")
        return no_content(message="User permanently deleted.")

    @admin_ns.doc('admin_update_user', security='jsonWebToken', tags=['Admin'])
    @admin_ns.expect(admin_user_update_model, validate=True)
    @admin_ns.response(HTTPStatus.OK, '用户信息更新成功', user_model)
    @admin_ns.response(HTTPStatus.BAD_REQUEST, '无效的输入数据')
    @admin_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @admin_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @admin_ns.response(HTTPStatus.NOT_FOUND, 'User not found')
    @admin_ns.response(HTTPStatus.CONFLICT, '账号/邮箱/手机号冲突')
    @admin_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新失败')
    def put(self, user_id):
        """更新指定用户的信息 (仅管理员)"""
        update_data = request.json
        # 移除 user_id 字段（如果前端未移除）
        if update_data and 'user_id' in update_data:
            update_data = {k: v for k, v in update_data.items() if k != 'user_id'}
        print("[admin_routes] Received update_data:", update_data)
        logger.debug(f"[admin_routes] Received update_data: {update_data}")

        if not update_data:
            return bad_request("Request body cannot be empty.")

        try:
            operator_id = int(get_jwt_identity())

            print(f"[admin_routes] operator_id from JWT: {operator_id}")
        except (ValueError, TypeError):
            return unauthorized("Invalid operator identity in token.")

        if 'role' in update_data and update_data['role']:
            if update_data['role'] not in UserRole._value2member_map_:
                return bad_request(f"Invalid role specified: {update_data['role']}")
        if 'status' in update_data and update_data['status']:
            if update_data['status'] not in UserStatus._value2member_map_:
                return bad_request(f"Invalid status specified: {update_data['status']}")

        updated_user_data = user_service.admin_update_user(
            operator_id=operator_id,
            user_id=user_id,
            update_data=update_data
        )
        return success(message="User information updated successfully", data=updated_user_data)
