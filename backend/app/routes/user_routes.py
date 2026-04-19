"""
@File       : user_routes.py
@Date       : 2025-03-01
@Desc       : 处理用户相关的 API 端点。
@Version    : 1.0.0
@Copyright  : Copyright © 2025. All rights reserved.

本模块包含与普通用户（注册用户）相关的 API 接口，支持用户注册、登录信息获取与更新、头像设置等操作。
注意：管理员与员工相关接口已移至 admin_routes。
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required  # 导入 jwt_required
from flask_restx import Namespace, Resource, fields

from app.models.enums import UserRole
from app.services import user_service
from app.services.user_service import update_user_avatar
from app.utils.decorators import log_request, timing
from app.utils.response import bad_request, created, success, unauthorized

logger = logging.getLogger(__name__)

# --- Namespace Definition ---
user_ns = Namespace('users',
                    description='用户注册、认证和管理操作',
                    path='/users')

# --- 输入/输出模型 ---

register_model = user_ns.model('UserRegister', {
    'account': fields.String(required=True, description='用户账号名 (必须唯一)',
                             example='john_doe'),
    'password': fields.String(required=True, description='用户密码', example='StrongPwd!123',
                              min_length=6),  # 添加最小长度
    'role': fields.String(description='用户角色 (USER 或 ADMIN)', example='USER', default='USER',
                          enum=[role.name for role in UserRole if role != UserRole.STAFF])
})

login_model = user_ns.model('UserLogin', {
    'account': fields.String(required=True, description='用户账号名', example='john_doe'),
    'password': fields.String(required=True, description='用户密码', example='StrongPwd!123')
})

profile_update_model = user_ns.model('ProfileUpdate', {
    'username': fields.String(description='新用户名', example='Johnny Doe', max_length=50),
    'email': fields.String(description='新邮箱地址', example='john.doe.new@example.com',
                           max_length=120),
    'phone_number': fields.String(description='新手机号', example='+8613800138000', max_length=20),
    'favorite_cuisine': fields.String(description='偏好的菜系 (可选, 清空传 null 或空字符串)',
                                      example='川菜', max_length=50),
    # 'password': fields.String(description='新密码 (可选)', min_length=6) # 如果允许在此更新密码
})

# --- UserOutput 模型添加 favorite_cuisine ---
user_model = user_ns.model('UserOutput', {
    'user_id': fields.Integer(description='用户 ID'),
    'account': fields.String(description='用户账号名'),
    'role': fields.String(description='用户角色'),
    'status': fields.String(description='用户状态'),
    'phone_number': fields.String(description='手机号', allow_null=True),
    'email': fields.String(description='邮箱地址', allow_null=True),
    'username': fields.String(description='显示用户名', allow_null=True),
    'favorite_cuisine': fields.String(description='偏好菜系', allow_null=True),  # <--- 添加
    'created_at': fields.DateTime(description='创建时间 (ISO 格式)'),
    'updated_at': fields.DateTime(description='最后更新时间 (ISO 格式)'),
    # 'deleted_at': fields.DateTime(description='删除时间 (ISO 格式)', allow_null=True) # 按需添加
})

token_model = user_ns.model('Token', {
    'token': fields.String(description='JWT 访问令牌')
})


# --- Routes ---

# --- User Routes ---
@user_ns.route('/register')
class UserRegister(Resource):
    """用户注册接口"""

    @user_ns.doc('register_user', security=None, tags=['User'])
    @user_ns.expect(register_model, validate=True)
    @user_ns.response(HTTPStatus.CREATED, '用户注册成功', token_model)
    @user_ns.response(HTTPStatus.BAD_REQUEST, '无效的输入数据')
    @user_ns.response(HTTPStatus.CONFLICT, '账号名已存在')
    @user_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '注册失败')
    def post(self):
        """用户注册"""
        data = request.json

        # 调用服务层进行用户注册
        user_id = user_service.create_user(data)
        if user_id:
            # 生成 JWT 访问令牌
            access_token = user_service.generate_token(user_id)
            return created(message="User registered successfully", data={"token": access_token})
        else:
            return bad_request(
                message="Invalid input data. Please check required fields and format.")


@user_ns.route('/me')
class UserProfile(Resource):
    """当前用户个人资料接口"""
    method_decorators = [jwt_required(), log_request, timing]

    @user_ns.doc('get_own_profile', security='jsonWebToken', tags=['User'])
    @user_ns.response(HTTPStatus.OK, '成功获取个人资料', user_model)
    @user_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @user_ns.response(HTTPStatus.NOT_FOUND, 'User not found')
    @user_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取个人资料失败')
    def get(self):
        """获取当前登录用户的个人资料"""
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("Invalid user identity in token.")  # 使用英文消息

        user_data = user_service.get_user_by_id(current_user_id)
        return success(message="Profile retrieved successfully", data=user_data)  # 使用英文消息

    @user_ns.doc('update_own_profile', security='jsonWebToken', tags=['User'])
    @user_ns.expect(profile_update_model, validate=True)
    @user_ns.response(HTTPStatus.OK, '个人资料更新成功', user_model)
    @user_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @user_ns.response(HTTPStatus.BAD_REQUEST, '无效的输入数据')
    @user_ns.response(HTTPStatus.NOT_FOUND, 'User not found')
    @user_ns.response(HTTPStatus.CONFLICT, '邮箱/手机号/用户名冲突')
    @user_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新个人资料失败')
    def put(self):
        """更新当前登录用户的个人资料"""
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("Invalid user identity in token.")

        data = request.json
        # 从 data 中提取允许更新的字段
        update_data = {
            "username": data.get("username"),
            "email": data.get("email"),
            "phone_number": data.get("phone_number"),
            "favorite_cuisine": data.get("favorite_cuisine"),
            # "password": data.get("password") # 如果允许密码更新
        }
        update_data_filtered = {k: v for k, v in update_data.items() if v is not None}

        if not update_data_filtered:
            # 即使没有提供数据，也返回当前信息和成功状态码 (200 OK)
            current_user_data = user_service.get_user_by_id(current_user_id)
            return success(message="No profile information provided to update.",
                           data=current_user_data)  # 使用英文消息

        updated_user_data = user_service.update_user_profile(
            user_id=current_user_id,
            update_data=update_data_filtered
        )
        return success(message="Profile updated successfully", data=updated_user_data)  # 使用英文消息


# --- Avatar Routes ---
@user_ns.route('/me/avatar')
class UpdateUserAvatar(Resource):
    """当前用户头像更新接口"""
    method_decorators = [jwt_required(), log_request, timing]

    @user_ns.doc('update_own_avatar', security='jsonWebToken', tags=['User'])
    @user_ns.expect(user_ns.model('AvatarUpdate', {
        'avatar_url': fields.String(
            required=True,
            description='头像图片 URL，建议为 MinIO 上传返回的访问地址',
            example='http://localhost:9000/avatars/avatar/abc123.jpg'
        )
    }), validate=True)
    @user_ns.response(HTTPStatus.OK, '头像更新成功，返回新头像链接', model=fields.Raw)
    @user_ns.response(HTTPStatus.BAD_REQUEST, '头像链接无效')
    @user_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @user_ns.response(HTTPStatus.NOT_FOUND, '用户不存在')
    @user_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新失败')
    def put(self):
        """更新当前登录用户的头像 URL（需先上传图片）"""
        user_id = get_jwt_identity()
        data = request.get_json()
        avatar_url = data.get("avatar_url")

        updated_url = update_user_avatar(user_id, avatar_url)
        return success(
            message="Avatar updated successfully",
            data={"avatar_url": updated_url}
        )
