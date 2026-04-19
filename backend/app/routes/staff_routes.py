"""
@File       : staff_routes.py
@Author     : taichilei
@Date       : 2025-05-05
@Description: 员工管理相关 API 端点
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields

from app.models.enums import UserRole
from app.services.staff_service import create_staff_user
from app.utils.decorators import log_request, require_roles, timing
from app.utils.response import created, success, unauthorized

logger = logging.getLogger(__name__)
staff_ns = Namespace("staff", description="员工管理接口", path="/staff")

staff_create_model = staff_ns.model('StaffCreate', {
    'account': fields.String(required=True, description='账号'),
    'username': fields.String(required=True, description='用户名'),
    'password': fields.String(description='密码（可选，默认 hotmeal）'),
    'email': fields.String(description='邮箱'),
    'phone_number': fields.String(description='手机号'),
    'favorite_cuisine': fields.String(description='偏好菜系')
})


@staff_ns.route('/users')
class StaffUserCreate(Resource):
    method_decorators = [log_request, timing, jwt_required(), require_roles([UserRole.ADMIN.name])]

    @staff_ns.expect(staff_create_model, validate=True)
    @staff_ns.response(HTTPStatus.CREATED, '员工创建成功')
    def post(self):
        """添加员工用户（STAFF 角色，仅管理员）"""
        data = request.json or {}
        try:
            operator_id = int(get_jwt_identity())
        except Exception:
            return unauthorized("Invalid operator identity in token.")
        new_user_data = create_staff_user(operator_id, data)
        return created(message="Staff user created successfully", data=new_user_data)


@staff_ns.route('/users')
class UserListResource(Resource):
    method_decorators = [log_request, timing, jwt_required(), require_roles([UserRole.ADMIN.name])]

    @staff_ns.doc(params={'role': '按角色过滤（可选，例如 STAFF）'})
    @staff_ns.response(HTTPStatus.OK, '用户列表获取成功')
    def get(self):
        """获取用户列表，可选按角色过滤（仅管理员）"""
        from app.services.user_service import get_all_users, get_users_by_role

        role = request.args.get("role")
        if role:
            users = get_users_by_role(role)
        else:
            users = get_all_users()
        return success(message="User list fetched", data=users)


@staff_ns.route('/users/<int:user_id>')
class StaffUserUpdate(Resource):
    method_decorators = [log_request, timing, jwt_required(), require_roles([UserRole.ADMIN.name])]

    @staff_ns.doc(params={
        'user_id': '要更新的员工用户 ID'
    })
    @staff_ns.response(HTTPStatus.OK, '员工信息更新成功')
    def put(self, user_id):
        """更新员工用户信息（仅管理员）"""
        logger.info(f"Update staff user {user_id} info")
        from app.services.staff_service import update_staff_user

        data = request.json or {}
        try:
            user_data = {
                'account': data.get('account'),
                'username': data.get('username'),
                'password': data.get('password'),
                'email': data.get('email'),
                'phone_number': data.get('phone_number'),
                'favorite_cuisine': data.get('favorite_cuisine'),
                'role': data.get('role')
            }
            updated_user = update_staff_user(
                user_data=user_data,
                user_id=user_id,
                operator_id=int(get_jwt_identity())
            )
            return success(message="Staff user updated successfully", data=updated_user)
        except Exception as e:
            logger.exception("[staff_routes] 更新员工失败")
            from app.utils.response import bad_request
            return bad_request(f"更新失败：{str(e)}")
