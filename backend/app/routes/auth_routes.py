"""
@File       : auth_routes.py
@Author     : taichilei
@Date       : 2025-04-26
@Description: 用户认证相关 API 端点
"""

import logging
from http import HTTPStatus

from flask import request

# --- Auth Routes ---
from flask_restx import Namespace as NewNamespace
from flask_restx import Resource, fields

from app.services.auth_service import AuthService
from app.utils.decorators import log_request, timing
from app.utils.response import success

auth_ns = NewNamespace('auth', description='认证相关操作', path='/auth')
logger = logging.getLogger(__name__)

login_model = auth_ns.model('UserLogin', {
    'account': fields.String(required=True, description='用户账号名', example='john_doe'),
    'password': fields.String(required=True, description='用户密码', example='StrongPwd!123')
})

token_model = auth_ns.model('Token', {
    'token': fields.String(description='JWT 访问令牌')
})


@auth_ns.route('/token')
class AuthToken(Resource):
    method_decorators = [log_request, timing]

    @auth_ns.doc('generate_token')
    @auth_ns.expect(login_model, validate=True)
    @auth_ns.response(HTTPStatus.OK, '登录成功', token_model)
    @auth_ns.response(HTTPStatus.UNAUTHORIZED, '无效的账号或密码')
    @auth_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '登录失败')
    def post(self):
        """用户登录并生成访问令牌"""
        data = request.json
        account = data.get("account")
        password = data.get("password")

        user = AuthService.authenticate(account, password)
        access_token = AuthService.generate_token(user)

        logger.info(f"用户登录成功: account={account}")
        return success(message="Login successful", data={
            "token": access_token,
            "user": user.to_dict()
        })
