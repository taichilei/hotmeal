"""
@File       : chat_service.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Desc       : 聊天服务层，处理聊天记录的创建、AI 回复处理和查询。
              适配重构后的 Chat 模型，采用 "失败抛异常，成功返数据"模式。

@Version    : 1.2.1 # 版本更新，修复类型、引用、未使用代码等问题
@Copyright  : Copyright © 2025. All rights reserved.
"""
import logging
import time
from http import HTTPStatus
from typing import Any

import openai
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.models.chat import Chat
from app.models.enums import ChatStatus, MessageType
from app.models.user import User
from app.utils.db import db
from app.utils.deepseek_client import get_deepseek_client

# 导入需要的错误码枚举
from app.utils.error_codes import ErrorCode

# 导入需要的异常类型
from app.utils.exceptions import (
    APIException,
    BusinessError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# --- 辅助函数 ---
def _serialize_chat(chat: Chat) -> dict[str, Any]:
    """内部辅助函数，用于序列化 Chat 对象。"""
    if not isinstance(chat, Chat):
        logger.error(f"尝试序列化非 Chat 对象: {type(chat)}")
        # 或者抛出 TypeError
        raise TypeError("无法序列化非 Chat 对象")
    # 调用模型的 to_dict 方法
    return chat.to_dict()


# --- AI 交互 ---
def generate_ai_response(user_message: str) -> str:
    """
    使用 DeepSeek 生成 AI 回复。
    """
    # --- 在函数开头获取客户端实例 ---
    try:
        local_client = get_deepseek_client()  # 在函数内部调用
    except (RuntimeError, ValueError) as client_err:  # 捕获获取客户端可能发生的错误
        logger.error(f"获取 DeepSeek 客户端失败: {client_err}")
        # 抛出 APIException，表明服务不可用
        raise APIException("AI 服务配置错误或不可用。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from client_err

    if not user_message:
        logger.warning("尝试为用户空消息生成 AI 回复。")
        # 根据业务逻辑决定是返回默认值还是抛错
        # raise ValidationError("消息内容不能为空。", error_code=ErrorCode.PARAM_MISSING.value)
        return "您好，有什么可以帮您？"

    logger.debug(f"向 DeepSeek 发送消息: {user_message[:100]}...")
    try:
        response = local_client.chat.completions.create(  # 使用 local_client
            model="deepseek-chat",
            messages=[{"role": "user", "content": user_message}],
        )

        if response.choices and response.choices[0].message and response.choices[0].message.content:
            ai_reply = response.choices[0].message.content.strip()
            logger.debug(f"收到 DeepSeek 回复: {ai_reply[:100]}...")
            return ai_reply
        else:
            logger.error(f"DeepSeek API 返回了无效的响应结构: {response}")
            # 视为服务器内部错误
            raise APIException("AI 服务返回异常，请稍后重试。",
                               error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)

    except openai.AuthenticationError as auth_err:
        logger.error(f"DeepSeek API 认证失败 (检查 API Key): {auth_err}", exc_info=True)
        raise APIException("AI 服务认证失败。", error_code=ErrorCode.AUTH_ERROR.value) from auth_err
    except openai.RateLimitError as rate_err:
        logger.warning(f"DeepSeek API 请求过于频繁: {rate_err}")
        raise BusinessError("AI 服务请求过于频繁，请稍后再试。",
                            http_status_code=HTTPStatus.TOO_MANY_REQUESTS,
                            error_code=ErrorCode.HTTP_INTERNAL_SERVER_ERROR.value) from rate_err
    except openai.APIConnectionError as conn_err:
        logger.error(f"无法连接到 DeepSeek API: {conn_err}", exc_info=True)
        raise APIException("无法连接 AI 服务。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from conn_err
    except openai.APIError as api_err:
        logger.error(f"DeepSeek API 调用失败: {api_err}", exc_info=True)
        raise APIException("调用 AI 服务时出错。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from api_err
    except Exception as ex:
        logger.error(f"调用 AI 服务时发生未知错误: {ex}", exc_info=True)
        raise APIException("调用 AI 服务时发生未知错误。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from ex


def _process_ai_answer_internal(chat_entry: Chat):
    """处理 AI 回答的内部逻辑 (不进行 commit)。修改传入的 chat_entry 对象。"""
    from app.utils.context_provider import load_admin_context, load_user_context
    if not isinstance(chat_entry, Chat):
        # 这个应该是非常内部的错误
        raise APIException("_process_ai_answer_internal 收到无效参数")

    if not chat_entry.question:
        logger.warning(f"聊天记录 {chat_entry.chat_id} 没有问题内容，无法生成 AI 回复。")
        chat_entry.status = ChatStatus.FAILED
        chat_entry.answer = "错误：缺少问题内容。"
        return  # 标记为失败并返回

    start_time = time.time()
    try:
        # 根据用户身份生成上下文 prompt
        user_role = getattr(chat_entry.user, 'role', 'user') if chat_entry.user else 'user'
        if user_role == 'admin':
            context = load_admin_context()
        else:
            context = load_user_context()
        prompt = f"{context}\n用户问题：{chat_entry.question}"
        ai_answer = generate_ai_response(prompt)
        end_time = time.time()

        chat_entry.answer = ai_answer
        chat_entry.status = ChatStatus.ANSWERED
        chat_entry.response_duration = round(end_time - start_time, 3)
        logger.info(
            f"聊天记录 {chat_entry.chat_id} AI 回复处理成功。耗时: {chat_entry.response_duration}s")

    except (APIException, BusinessError,
            ValidationError) as ai_proc_err:  # 捕获 generate_ai_response 可能抛出的已知异常
        logger.error(f"为聊天 {chat_entry.chat_id} 生成 AI 回复失败: {ai_proc_err}", exc_info=True)
        chat_entry.status = ChatStatus.FAILED
        chat_entry.answer = f"AI 服务错误: {ai_proc_err.message}"  # 记录错误信息
        raise ai_proc_err  # 将异常继续向上抛出，以便事务可以回滚


# --- 创建聊天 ---
def create_chat_message(user_id: int, question: str,
                        message_type: MessageType = MessageType.TEXT,
                        image_url: str | None = None,
                        tags: str | None = None,
                        process_sync: bool = True) -> dict[str, Any]:
    """创建新的聊天记录。可以选择是否同步处理 AI 回复。"""
    # 1. 验证 User ID
    if not db.session.query(User.query.filter_by(user_id=user_id).exists()).scalar():
        raise NotFoundError(f"用户 ID {user_id} 不存在。", error_code=ErrorCode.USER_NOT_FOUND.value)

    # 2. 创建 Chat 实例 (依赖模型验证)
    try:
        initial_status = ChatStatus.PROCESSING if process_sync else ChatStatus.PENDING
        new_chat = Chat(
            user_id=user_id,
            question=question,
            message_type=message_type,
            image_url=image_url,
            tags=tags,
            status=initial_status
        )
    except ValueError as ve:  # 捕获模型验证错误
        raise ValidationError(f"创建聊天记录时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value) from ve

    # 3. 添加到数据库并处理
    try:
        db.session.add(new_chat)
        db.session.flush()  # 获取 chat_id
        chat_id = new_chat.chat_id  # chat_id 在 flush 后应该有值
        if chat_id is None:  # 添加一个运行时检查以防万一
            raise APIException("无法获取新聊天记录的 ID。")
        logger.info(f"用户 {user_id} 的新聊天记录 (ID: {chat_id}) 已初步添加到 session。")

        if process_sync:
            logger.info(f"开始同步处理聊天记录 {chat_id} 的 AI 回复...")
            # 调用内部处理函数，它会在失败时抛出异常并已标记 Chat 对象为 FAILED
            _process_ai_answer_internal(new_chat)

        # 提交事务（无论是 PENDING, ANSWERED 还是 FAILED 状态）
        db.session.commit()
        logger.info(f"聊天记录 (ID: {chat_id}) 创建并处理完成，最终状态: {new_chat.status.name}。")
        return _serialize_chat(new_chat)

    except (NotFoundError, ValidationError, BusinessError, APIException) as known_err:
        db.session.rollback()
        logger.warning(f"创建或处理聊天记录失败 ({type(known_err).__name__}): {known_err}")
        raise known_err  # 重新抛出已知异常
    except SQLAlchemyError as db_err:
        db.session.rollback()
        logger.error(f"创建聊天记录时发生数据库错误: {db_err}", exc_info=True)
        raise APIException("创建聊天记录失败，数据库错误。",
                           error_code=ErrorCode.DATABASE_ERROR.value) from db_err
    except Exception as ex:  # 捕获其他未知错误
        db.session.rollback()
        logger.error(f"创建聊天记录时发生未知错误: {ex}", exc_info=True)
        raise APIException("创建聊天记录时发生未知错误。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from ex


# --- 处理待处理聊天 ---
def process_single_pending_chat(chat_id: int) -> dict[str, Any]:
    """处理单个指定 ID 的聊天记录的 AI 回复。"""
    logger.info(f"尝试处理聊天记录 {chat_id} 的 AI 回复...")
    chat_entry = Chat.query.get(chat_id)

    if not chat_entry:
        raise NotFoundError(f"聊天记录 ID {chat_id} 未找到。",
                            error_code=ErrorCode.CHAT_NOT_FOUND.value)  # 假设已定义 CHAT_NOT_FOUND

    # 检查状态是否适合处理
    allowed_statuses = [ChatStatus.PENDING, ChatStatus.PROCESSING, ChatStatus.FAILED]  # 允许重试 FAILED
    if chat_entry.status not in allowed_statuses:
        logger.warning(f"聊天记录 {chat_id} 的状态为 {chat_entry.status.name}，不适合处理 AI 回复。")
        # 使用通用的业务错误或特定的状态错误
        raise BusinessError(f"聊天记录当前状态 ({chat_entry.status.name}) 无法处理 AI 回复。",
                            error_code=ErrorCode.ORDER_STATE_INVALID.value)  # 复用订单状态错误码或定义新的

    # 更新状态为 PROCESSING (如果当前不是)
    if chat_entry.status != ChatStatus.PROCESSING:
        chat_entry.status = ChatStatus.PROCESSING
        try:
            db.session.commit()
            logger.info(f"聊天记录 {chat_id} 状态更新为 PROCESSING。")
        except SQLAlchemyError as db_upd_err:
            db.session.rollback()
            logger.error(f"更新聊天 {chat_id} 状态为 PROCESSING 时失败: {db_upd_err}",
                         exc_info=True)
            raise APIException("更新聊天状态失败。",
                               error_code=ErrorCode.DATABASE_ERROR.value) from db_upd_err

    # 处理 AI 回复
    try:
        _process_ai_answer_internal(chat_entry)  # 内部会修改 chat_entry 的状态和答案
        db.session.commit()  # 提交最终结果 (ANSWERED 或 FAILED)
        logger.info(f"聊天记录 {chat_id} AI 回复处理完成，最终状态: {chat_entry.status.name}。")
        return _serialize_chat(chat_entry)
    except (APIException, BusinessError, NotFoundError, ValidationError) as known_err:
        # _process_ai_answer_internal 可能抛出这些异常，并且已将状态标记为 FAILED
        db.session.commit()  # 提交 FAILED 状态
        logger.error(f"处理聊天 {chat_id} 的 AI 回复失败: {known_err}", exc_info=True)
        raise known_err  # 重新抛出，让调用方知道失败了
    except SQLAlchemyError as db_proc_err:  # 处理提交最终结果时的数据库错误
        db.session.rollback()
        logger.error(f"提交聊天 {chat_id} 最终状态时失败: {db_proc_err}", exc_info=True)
        raise APIException("处理 AI 回复时数据库错误。",
                           error_code=ErrorCode.DATABASE_ERROR.value) from db_proc_err
    except Exception as ex:  # 处理未知错误
        db.session.rollback()
        logger.error(f"处理聊天 {chat_id} 的 AI 回复过程中发生未知错误: {ex}", exc_info=True)
        # 尝试将状态标记为 FAILED 并提交
        try:
            chat_entry.status = ChatStatus.FAILED
            chat_entry.answer = f"处理时发生未知错误: {ex}"
            db.session.commit()
        except Exception as final_err:
            db.session.rollback()
            logger.error(f"标记聊天 {chat_id} 为 FAILED 状态时再次失败: {final_err}", exc_info=True)
        raise APIException(f"处理 AI 回复时发生未知错误: {ex}",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from ex


# --- 查询聊天记录 ---
# 这些函数看起来是独立的查询逻辑，如果它们只被路由层使用，放在这里是合适的。
# 如果有更复杂的查询或需要被其他服务复用，可以考虑放到专门的查询模块或仓库层。

def get_chat_by_id(chat_id: int) -> dict[str, Any]:
    """根据 ID 获取聊天记录详情。"""
    # 预加载用户信息可以提高序列化效率
    chat = Chat.query.options(joinedload(Chat.user)).get(chat_id)
    if not chat:
        raise NotFoundError(f"聊天记录 ID {chat_id} 未找到。",
                            error_code=ErrorCode.CHAT_NOT_FOUND.value)  # 需要定义 CHAT_NOT_FOUND
    return _serialize_chat(chat)


def get_chat_history_for_user(user_id: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    """获取指定用户的聊天记录分页列表。"""
    if not db.session.query(User.query.filter_by(user_id=user_id).exists()).scalar():
        raise NotFoundError(f"用户 ID {user_id} 不存在。", error_code=ErrorCode.USER_NOT_FOUND.value)

    try:
        query = Chat.query.filter_by(user_id=user_id).order_by(Chat.created_at.desc())
        # 也可以预加载用户信息
        # query = query.options(joinedload(Chat.user))
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        chat_data = [_serialize_chat(chat) for chat in pagination.items]
        result = {
            "items": chat_data,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages
        }
        logger.info(f"成功检索用户 {user_id} 的聊天记录: 第 {page}/{pagination.pages} 页。")
        return result
    except SQLAlchemyError as db_hist_err:
        logger.error(f"获取用户 {user_id} 聊天记录时发生数据库错误: {db_hist_err}", exc_info=True)
        raise APIException("获取聊天记录失败。",
                           error_code=ErrorCode.DATABASE_ERROR.value) from db_hist_err


def get_pending_or_processing_chats(limit: int = 100) -> list[dict[str, Any]]:
    """获取处于 PENDING 或 PROCESSING 状态的聊天记录列表。"""
    try:
        chats = Chat.query.filter(
            Chat.status.in_([ChatStatus.PENDING, ChatStatus.PROCESSING])
        ).order_by(Chat.created_at.asc()).limit(limit).all()
        return [_serialize_chat(chat) for chat in chats]
    except SQLAlchemyError as db_pend_err:
        logger.error(f"获取待处理聊天记录时发生数据库错误: {db_pend_err}", exc_info=True)
        raise APIException("获取待处理聊天记录失败。",
                           error_code=ErrorCode.DATABASE_ERROR.value) from db_pend_err
