"""
@File       : chat_routes.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Desc       : 聊天相关的 API 端点。
"""
import logging
from http import HTTPStatus
from typing import cast  # <--- 导入 cast

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required  # 导入所需函数
from flask_restx import Namespace, Resource, fields

# 导入模型和服务
from app.models.enums import MessageType, UserRole  # 导入需要的枚举
from app.services import chat_service  # 导入重构后的服务

# 导入装饰器和响应工具
from app.utils.decorators import (
    log_request,
    require_roles,
    timing,  # 移除 validate_json, login_required
)

# 导入错误码和异常 (供参考)
from app.utils.error_codes import ErrorCode
from app.utils.exceptions import AuthorizationError, ValidationError
from app.utils.response import (  # 导入响应函数
    bad_request,
    created,
    success,
    unauthorized,
)

logger = logging.getLogger(__name__)

# --- Namespace 定义 ---

chat_ns = Namespace('chats', description='聊天交互操作', path='/chats')

# --- 输入/输出模型 ---

# 创建聊天消息 (提问) 的输入模型
chat_ask_model = chat_ns.model('ChatAskInput', {
    'question': fields.String(required=True, description='用户的问题或内容', min_length=1,
                              max_length=255, example='推荐一个清淡的菜'),
    'message_type': fields.String(description='消息类型', enum=[e.name for e in MessageType],
                                  default=MessageType.TEXT.name, example='TEXT'),
    'image_url': fields.String(description='图片 URL (如果消息类型是 IMAGE)',
                               example='http://example.com/image.jpg'),
    'tags': fields.String(description='标签 (逗号分隔)', example='推荐,清淡'),
    'process_sync': fields.Boolean(description='是否立即尝试获取 AI 回复 (默认 True)', default=True)
    # 添加同步处理选项
})

# AI 直接聊天输入模型
ai_chat_model = chat_ns.model('AiChatInput', {
    'message': fields.String(required=True, description='发送给 AI 的消息', min_length=1,
                             example='你好吗？')
})

# AI 直接聊天输出模型
ai_chat_output_model = chat_ns.model('AiChatOutput', {
    'response': fields.String(description='AI 的回复内容')
})

# 聊天记录输出模型 (与 _serialize_chat 对应)
chat_output_model = chat_ns.model('ChatOutput', {
    'chat_id': fields.Integer(description='聊天记录 ID'),
    'user_id': fields.Integer(description='用户 ID'),
    'question': fields.String(description='用户问题/内容'),
    'answer': fields.String(description='AI/人工回复内容', allow_null=True),
    'status': fields.String(description='状态'),
    'created_at': fields.DateTime(description='创建时间 (ISO 格式)'),
    'updated_at': fields.DateTime(description='更新时间 (ISO 格式)'),
    'response_time': fields.Float(description='AI 响应时间 (秒)', allow_null=True),
    'confidence': fields.Float(description='AI 置信度', allow_null=True),
    'source': fields.String(description='回复来源 (AI/人工)', allow_null=True),
    'tags': fields.String(description='标签', allow_null=True),
    'message_type': fields.String(description='消息类型'),
    'response_duration': fields.Float(description='AI 处理时长 (秒)', allow_null=True),
    'image_url': fields.String(description='图片 URL', allow_null=True)
})

# 聊天历史列表输出模型 (包含分页)
chat_history_output_model = chat_ns.model('ChatHistoryOutput', {
    'items': fields.List(fields.Nested(chat_output_model)),
    'page': fields.Integer(description='当前页码'),
    'per_page': fields.Integer(description='每页数量'),
    'total_items': fields.Integer(description='总项目数'),
    'total_pages': fields.Integer(description='总页数')
})


# --- 路由 ---

# 用于直接与 AI 对话的独立接口
@chat_ns.route("/ai_direct")  # 修改路径避免与资源路径冲突
class AiDirectChat(Resource):
    method_decorators = [jwt_required(), log_request, timing]  # 应用于类方法

    @chat_ns.doc('direct_ai_chat', security='jsonWebToken')
    @chat_ns.expect(ai_chat_model, validate=True)
    @chat_ns.response(HTTPStatus.OK, 'AI 回复成功', ai_chat_output_model)
    @chat_ns.response(HTTPStatus.BAD_REQUEST, '输入消息为空')
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.TOO_MANY_REQUESTS, '请求过于频繁')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, 'AI 服务调用失败')
    def post(self):
        """直接调用 AI 模型进行对话 (不保存记录)"""
        data = request.get_json()
        user_message = data.get("message")  # expect 已验证存在

        # 调用服务层的 AI 生成函数（它会处理错误并抛异常）
        ai_response = chat_service.generate_ai_response(user_message)

        return success(message="AI 回复已生成", data={"response": ai_response})


# 聊天资源路由
@chat_ns.route("/")  # 对应 /chats/
class ChatList(Resource):
    method_decorators = [jwt_required(), log_request, timing]  # 应用于类方法

    @chat_ns.doc('create_chat', security='jsonWebToken')
    @chat_ns.expect(chat_ask_model, validate=True)
    @chat_ns.response(HTTPStatus.CREATED, '聊天记录创建成功', chat_output_model)
    @chat_ns.response(HTTPStatus.BAD_REQUEST, '输入参数无效')
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.NOT_FOUND, '用户不存在')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '创建或处理失败')
    def post(self):
        """用户发起新的聊天提问"""
        data = request.get_json()
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。")

        # 将枚举字符串转为枚举类型
        try:
            # 从请求数据获取字符串，默认为 'TEXT'，并转大写
            message_type_str = data.get('message_type', 'TEXT').upper()
            # 通过字符串名称获取枚举成员
            message_type_member = MessageType[message_type_str]
            # --- 使用 cast 明确告知 MyPy 类型 ---
            message_type_arg = cast(MessageType, message_type_member)
        except KeyError:
            # 如果字符串无法匹配任何枚举成员名称，则捕获 KeyError
            return bad_request(f"无效的消息类型: {data.get('message_type')}")

        # 调用服务层创建聊天记录
        new_chat_data = chat_service.create_chat_message(
            user_id=current_user_id,
            question=data.get("question"),
            message_type=message_type_arg,  # <--- 传递经过 cast 的变量
            image_url=data.get("image_url"),
            tags=data.get("tags"),
            process_sync=data.get("process_sync", True)  # 获取同步处理选项
        )

        logger.info(f"用户 {current_user_id} 创建了新的聊天记录: ID={new_chat_data.get('chat_id')}")
        chat_id = new_chat_data.get('chat_id')
        headers = {"Location": f"/chats/{chat_id}"} if chat_id else None
        # 根据 process_sync 返回不同消息？
        message = "聊天记录已创建，正在处理回复..." \
            if not data.get("process_sync", True) else "聊天记录创建并处理成功"
        return created(data=new_chat_data, message=message, headers=headers)

    @chat_ns.doc('get_my_chat_history', security='jsonWebToken')
    @chat_ns.param('page', '页码', type=int, default=1, location='args')
    @chat_ns.param('per_page', '每页数量', type=int, default=20, location='args')
    @chat_ns.response(HTTPStatus.OK, '成功获取聊天记录', chat_history_output_model)
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取记录失败')
    def get(self):
        """获取当前登录用户的聊天记录（分页）"""
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。")

        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            if page <= 0 or per_page <= 0:
                raise ValidationError("页码和每页数量必须是正整数。")
        except ValueError:
            return bad_request("页码和每页数量参数必须是整数。")

        # 调用服务层获取历史记录
        history_data = chat_service.get_chat_history_for_user(
            user_id=current_user_id,
            page=page,
            per_page=per_page
        )

        return success(message="成功获取聊天记录", data=history_data)


@chat_ns.route("/<int:chat_id>")  # 对应 /chats/{chat_id}
@chat_ns.param('chat_id', '聊天记录 ID')
class ChatDetail(Resource):
    method_decorators = [jwt_required(), log_request, timing]

    @chat_ns.doc('get_chat_detail', security='jsonWebToken')
    @chat_ns.response(HTTPStatus.OK, '成功获取聊天详情', chat_output_model)
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.FORBIDDEN, '无权查看此聊天记录')  # 需要权限检查
    @chat_ns.response(HTTPStatus.NOT_FOUND, '聊天记录未找到')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取失败')
    # 添加权限：管理员/员工或记录所有者
    @require_roles(["admin", "staff", "user"])
    def get(self, chat_id):
        """获取指定 ID 的聊天记录详情"""
        try:
            current_user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            return unauthorized("无效的用户身份令牌。")

        # 调用服务层获取详情
        chat_data = chat_service.get_chat_by_id(chat_id)

        # 在路由层或服务层进行权限检查
        if chat_data.get("user_id") != current_user_id:
            # 如果不是自己的记录，需要检查角色
            current_jwt = get_jwt()
            current_user_role = current_jwt.get("role")
            if current_user_role.upper() not in [UserRole.ADMIN.name, UserRole.STAFF.name]:
                raise AuthorizationError("无权查看此聊天记录。",
                                         error_code=ErrorCode.FORBIDDEN.value)

        return success(message="成功获取聊天详情", data=chat_data)


# --- 管理接口 (示例) ---

@chat_ns.route("/pending")  # 对应 /chats/pending
class PendingChatList(Resource):
    method_decorators = [jwt_required(), require_roles(["admin", "staff"]), log_request,
                         timing]  # 仅管理员/员工

    @chat_ns.doc('list_pending_chats', security='jsonWebToken')
    @chat_ns.param('limit', '最大返回数量', type=int, default=100, location='args')
    @chat_ns.response(HTTPStatus.OK, '成功获取待处理列表', [chat_output_model])
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取失败')
    def get(self):
        """获取待处理 (Pending 或 Processing) 的聊天记录列表 (仅管理员/员工)"""
        try:
            limit = int(request.args.get('limit', 100))
            if limit <= 0:
                raise ValidationError("limit 参数必须是正整数。")
        except ValueError:
            return bad_request("limit 参数必须是整数。")

        pending_chats = chat_service.get_pending_or_processing_chats(limit=limit)
        return success(message="成功获取待处理聊天记录", data=pending_chats)


@chat_ns.route("/<int:chat_id>/process")  # 对应 /chats/{chat_id}/process
@chat_ns.param('chat_id', '聊天记录 ID')
class ProcessChat(Resource):
    method_decorators = [jwt_required(), require_roles(["admin", "staff"]), log_request,
                         timing]  # 仅管理员/员工

    @chat_ns.doc('process_chat_answer', security='jsonWebToken')
    @chat_ns.response(HTTPStatus.OK, '聊天记录处理成功', chat_output_model)
    @chat_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chat_ns.response(HTTPStatus.FORBIDDEN, '需要管理员或员工权限')
    @chat_ns.response(HTTPStatus.NOT_FOUND, '聊天记录未找到')
    @chat_ns.response(HTTPStatus.CONFLICT, '聊天记录状态无法处理')
    @chat_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '处理失败')
    def post(self, chat_id):  # 使用 POST 触发处理动作
        """触发对指定聊天记录的 AI 回复处理 (仅管理员/员工)"""
        # 调用服务层处理函数
        processed_chat_data = chat_service.process_single_pending_chat(chat_id)
        logger.info(
            f"管理员/员工触发了对聊天 {chat_id} 的处理，最终状态: {processed_chat_data.get('status')}")
        return success(message="聊天记录处理成功", data=processed_chat_data)

# 移除了旧的 /ask, /answer/{id}, /status/{id}, /history 路由
