"""
@File       : dining_area_routes.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 用餐区域相关的 API 端点。
"""

import logging
from http import HTTPStatus
from typing import cast

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

# 导入模型和服务
from app.models.enums import AreaType, DiningAreaState
from app.services import dining_area_service

# 导入装饰器和响应工具
from app.utils.decorators import log_request, require_roles, timing
from app.utils.response import bad_request, created, no_content, success

# 导入错误码和异常 (供参考)

logger = logging.getLogger(__name__)

# --- Namespace 定义 ---
# 路径使用复数形式，并调整描述
area_ns = Namespace('dining-areas', description='用餐区域管理操作', path='/dining-areas')  # 复数形式

# --- 输入/输出模型 ---

# 创建用餐区域的输入模型
area_create_model = area_ns.model('DiningAreaCreateInput', {
    'area_name': fields.String(required=True, description='区域名称 (必须唯一)', min_length=1,
                               max_length=50, example='A1包间'),
    'max_capacity': fields.Integer(description='最大容量 (正整数)', example=10, min=1),
    # 改为可选，服务层处理 None
    'area_type': fields.String(required=True, description='区域类型',
                               enum=[e.name for e in AreaType], example='PRIVATE'),
    # 'state': fields.String(description='初始状态', enum=[e.name for e in DiningAreaState], default=DiningAreaState.FREE.name) # state 通常由系统管理，不需客户端指定
})

# 更新用餐区域的输入模型 (管理员)
area_update_model = area_ns.model('DiningAreaUpdateInput', {
    'area_name': fields.String(description='新区域名称', min_length=1, max_length=50,
                               example='豪华包间'),
    'max_capacity': fields.Integer(description='新最大容量 (正整数)', min=1, example=12),
    'area_type': fields.String(description='新区域类型', enum=[e.name for e in AreaType],
                               example='PRIVATE'),
    # 'state': fields.String(description='新状态', enum=[e.name for e in DiningAreaState]) # 状态通常不由直接更新接口修改
})

# 分配区域的输入模型
area_assign_model = area_ns.model('DiningAreaAssignInput', {
    'user_id': fields.Integer(required=True, description='要分配给的用户 ID', example=101)
})

# 用餐区域信息的输出模型 (与服务层的序列化一致)
area_output_model = area_ns.model('DiningAreaOutput', {
    'area_id': fields.Integer(description='区域 ID'),
    'area_name': fields.String(description='区域名称'),
    'state': fields.String(description='当前状态'),
    'area_type': fields.String(description='区域类型'),
    'max_capacity': fields.Integer(description='最大容量', allow_null=True),
    'usage_count': fields.Integer(description='使用次数'),
    'assigned_user_id': fields.Integer(description='当前占用用户 ID', allow_null=True),
    'assigned_username': fields.String(description='当前占用用户名', allow_null=True),  # 从序列化函数添加
    'last_used': fields.DateTime(description='上次使用时间 (ISO 格式)', allow_null=True),
    'created_at': fields.DateTime(description='创建时间 (ISO 格式)'),
    'updated_at': fields.DateTime(description='更新时间 (ISO 格式)')
})


# --- 路由 ---

@area_ns.route("/")  # 对应 /dining-areas/
class DiningAreaList(Resource):
    method_decorators = [log_request, timing]  # 应用于类中的所有方法

    @area_ns.doc('create_dining_area', security='jsonWebToken')
    @area_ns.expect(area_create_model, validate=True)
    @area_ns.response(HTTPStatus.CREATED, '用餐区域创建成功', area_output_model)
    @area_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @area_ns.response(HTTPStatus.CONFLICT, '区域名称已存在')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '创建失败')
    @jwt_required()
    @require_roles(["admin"])  # 仅管理员可创建
    def post(self):
        """创建新的用餐区域 (仅管理员)"""
        data = request.get_json()

        logger.debug(f"接收到的 JSON 数据: {data}")

        # 将 area_type 字符串转换为枚举并进行类型转换
        try:
            area_type_str = data['area_type'].upper()
            area_type_member = AreaType[area_type_str]
            area_type_arg = cast(AreaType, area_type_member)
        except (KeyError, AttributeError, ValueError):
            logger.warning(f"非法区域类型参数: {data.get('area_type')}")
            return bad_request(f"无效的区域类型: {data.get('area_type')}")

        # 调用服务层函数 (它会进行更详细的验证并抛出异常)
        new_area_data = dining_area_service.create_dining_area(
            area_name=data.get("area_name"),
            max_capacity=data.get("max_capacity"),  # 服务层处理 None 和验证
            area_type=area_type_arg  # <--- 传递 cast 后的变量
            # state 通常默认为 FREE，不需要客户端传入
        )

        logger.info(
            f"管理员创建用餐区域: ID={new_area_data.get('area_id')}, Name='{new_area_data.get('area_name')}'")
        return created(data=new_area_data, message="用餐区域创建成功")

    @area_ns.doc('list_dining_areas')
    @area_ns.param('area_type', '按区域类型过滤 (PRIVATE, TABLE, BAR)', type=str, location='args')
    @area_ns.param('state', '按状态过滤 (FREE, OCCUPIED)', type=str, location='args')
    @area_ns.response(HTTPStatus.OK, '成功获取用餐区域列表', [area_output_model])  # 返回列表
    @area_ns.response(HTTPStatus.BAD_REQUEST, '无效的过滤参数')
    # 考虑是否需要登录查看？
    # @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取列表失败')
    # @jwt_required() # 如果需要登录
    # @require_roles(["admin", "staff"]) # 如果只有特定角色能看列表
    def get(self):
        """获取用餐区域列表 (可选按类型和状态过滤)"""
        area_type_str = request.args.get('area_type')
        state_str = request.args.get('state')

        area_type = None
        if area_type_str:
            try:
                area_type = AreaType[area_type_str.upper()]
            except KeyError:
                return bad_request(f"无效的区域类型过滤参数: {area_type_str}")

        state = None
        if state_str:
            try:
                state = DiningAreaState[state_str.upper()]
            except KeyError:
                return bad_request(f"无效的状态过滤参数: {state_str}")

        # 调用服务层函数
        areas_data = dining_area_service.fetch_dining_areas(area_type=area_type, state=state)

        return success(message="成功获取用餐区域列表", data=areas_data)


@area_ns.route("/<int:area_id>")  # 对应 /dining-areas/{area_id}
@area_ns.param('area_id', '用餐区域 ID')
@area_ns.response(HTTPStatus.NOT_FOUND, '用餐区域未找到')
class DiningAreaDetail(Resource):
    method_decorators = [jwt_required(), require_roles(["admin"]), log_request, timing]  # 默认管理员权限

    @jwt_required()
    @area_ns.doc('get_dining_area_detail', security='jsonWebToken')
    @area_ns.response(HTTPStatus.OK, '成功获取用餐区域详情', area_output_model)
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取失败')
    def get(self, area_id):
        """获取指定 ID 的用餐区域详情 (仅管理员)"""
        # 服务层找不到会抛 NotFoundError
        area_data = dining_area_service.get_dining_area(area_id)
        return success(message="成功获取用餐区域详情", data=area_data)

    @area_ns.doc('update_dining_area', security='jsonWebToken')
    @area_ns.expect(area_update_model, validate=True)
    @area_ns.response(HTTPStatus.OK, '用餐区域更新成功', area_output_model)
    @area_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @area_ns.response(HTTPStatus.NOT_FOUND, '用餐区域未找到')
    @area_ns.response(HTTPStatus.CONFLICT, '名称冲突')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '更新失败')
    @jwt_required()  # 添加身份验证装饰器
    def put(self, area_id):
        """更新指定 ID 的用餐区域信息 (仅管理员)"""
        update_data = request.get_json()
        if not update_data:
            return bad_request("请求体不能为空。")

        # 服务层会处理验证和更新逻辑，失败抛异常
        updated_area_data = dining_area_service.update_dining_area(
            area_id=area_id,
            update_data=update_data
        )
        logger.info(f"管理员更新了用餐区域: ID={area_id}")
        return success(message="用餐区域更新成功", data=updated_area_data)

    @area_ns.doc('delete_dining_area', security='jsonWebToken')
    @area_ns.response(HTTPStatus.NO_CONTENT, '用餐区域删除成功')
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员权限')
    @area_ns.response(HTTPStatus.NOT_FOUND, '用餐区域未找到')
    @area_ns.response(HTTPStatus.CONFLICT, '区域被占用或有关联数据，无法删除')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '删除失败')
    @jwt_required()  # 添加身份验证装饰器
    def delete(self, area_id):
        """永久删除指定 ID 的用餐区域 (仅管理员)"""
        # 服务层会处理删除逻辑和检查，失败抛异常
        dining_area_service.delete_dining_area(area_id)
        logger.info(f"管理员删除了用餐区域: ID={area_id}")
        return no_content(message="用餐区域删除成功")


# --- 分配和释放接口 ---

@area_ns.route("/<int:area_id>/assign")  # 使用 assign 作为动作路径
@area_ns.param('area_id', '用餐区域 ID')
class AssignDiningArea(Resource):
    method_decorators = [jwt_required(), require_roles(["admin", "staff"]), log_request,
                         timing]  # 假设管理员或员工可以分配

    @area_ns.doc('assign_dining_area', security='jsonWebToken')
    @area_ns.expect(area_assign_model, validate=True)
    @area_ns.response(HTTPStatus.OK, '用餐区域分配成功', area_output_model)  # 返回更新后的区域信息
    @area_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @area_ns.response(HTTPStatus.NOT_FOUND, '区域或User not found')
    @area_ns.response(HTTPStatus.CONFLICT, '区域已被占用')
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '分配失败')
    def post(self, area_id):  # 使用 POST 表示执行动作
        """将空闲区域分配给指定用户 (仅管理员/员工)"""
        data = request.get_json()
        user_id = data.get('user_id')  # expect 确保存在

        # 服务层处理分配逻辑和错误
        assigned_area_data = dining_area_service.assign_dining_area(
            area_id=area_id,
            user_id=user_id
        )
        logger.info(f"区域 {area_id} 已分配给用户 {user_id}")
        return success(message="用餐区域分配成功", data=assigned_area_data)


@area_ns.route("/<int:area_id>/release")  # 使用 release 作为动作路径
@area_ns.param('area_id', '用餐区域 ID')
class ReleaseDiningArea(Resource):
    method_decorators = [jwt_required(), require_roles(["admin", "staff"]), log_request,
                         timing]  # 假设管理员或员工可以释放

    @area_ns.doc('release_dining_area', security='jsonWebToken')
    @area_ns.response(HTTPStatus.OK, '用餐区域释放成功', area_output_model)  # 返回更新后的区域信息
    @area_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @area_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @area_ns.response(HTTPStatus.NOT_FOUND, '区域未找到')
    # @area_ns.response(HTTPStatus.CONFLICT, '区域已经是空闲状态') # 服务层可能直接返回成功 (幂等)
    @area_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '释放失败')
    def post(self, area_id):  # 使用 POST 表示执行动作
        """释放一个占用的用餐区域 (仅管理员/员工)"""
        # 服务层处理释放逻辑和错误
        released_area_data = dining_area_service.release_dining_area(area_id)
        logger.info(f"区域 {area_id} 已被释放。")
        return success(message="用餐区域释放成功", data=released_area_data)

# 移除了旧的 /add, /list, /use, /free, /update 路由
