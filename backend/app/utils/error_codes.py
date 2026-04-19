"""
@File       : error_codes.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 业务错误码枚举定义，为每个错误提供统一的错误码分类和取值
@Version    : 1.2.1 # 版本更新，添加 HTTP 相关错误码值
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """业务错误码枚举"""

    # --- 0: 通用成功 ---

    SUCCESS = 0  # Operation succeeded

    # --- 1xxxx: 通用错误 / 参数错误 ---
    OPERATION_FAILED = 10000  # 通用操作失败
    PARAM_MISSING = 10001  # 参数缺失
    PARAM_INVALID = 10002  # 参数无效 (类型、格式、范围等)
    REQUEST_VALIDATION_FAILED = 10003  # 请求体验证失败 (例如 Flask-RESTX)

    # --- 2xxxx: 用户 / 认证 / 授权 ---
    AUTH_ERROR = 20000  # 通用认证/授权错误 (少用，优先使用下面更具体的)
    USER_NOT_FOUND = 20001  # User not found
    ACCOUNT_EXISTS = 20002  # 账户名已存在
    UNAUTHORIZED = 20003  # 未授权 (认证失败，如无效token、密码错误)
    FORBIDDEN = 20004  # 禁止访问 (权限不足)
    USER_BANNED = 20005  # 用户被禁用
    USER_DELETED = 20006  # 用户已被(软)删除

    # --- 3xxxx: 订单 / 订单项 ---
    ORDER_NOT_FOUND = 30001  # 订单未找到
    ORDER_CREATE_FAILED = 30002  # 订单创建失败 (通用)
    ORDER_STATE_INVALID = 30003  # 订单状态无效或不允许当前操作
    ORDER_DELETE_FAILED = 30004  # 订单删除失败 (通用)
    ORDER_UPDATE_FAILED = 30005  # 订单更新失败 (通用)
    ORDER_ITEM_NOT_FOUND = 30007  # 订单项未找到
    ORDER_ITEM_UPDATE_FAILED = 30008  # 订单项更新失败
    ORDER_CANCEL_FAILED = 30010  # 订单取消失败

    # --- 4xxxx: 菜品 / 分类 ---
    DISH_NOT_FOUND = 40001  # 菜品未找到
    INSUFFICIENT_STOCK = 40002  # 库存不足
    DISH_UNAVAILABLE = 40003  # 菜品不可用/已下架
    DISH_DELETE_FAILED = 40004  # 菜品删除失败
    DISH_UPDATE_FAILED = 40005  # 菜品更新失败

    CATEGORY_NOT_FOUND = 45001  # 分类未找到
    CATEGORY_NAME_EXISTS = 45002  # 分类名称已存在
    CATEGORY_DELETE_FAILED = 45003  # 分类删除失败 (例如有关联)
    CATEGORY_UPDATE_FAILED = 45004  # 分类更新失败

    # --- 5xxxx: 系统 / 数据库 / 外部服务 ---
    INTERNAL_SERVER_ERROR = 50000  # 通用服务器内部错误 (未知错误)
    DATABASE_ERROR = 50001  # 数据库操作错误
    EXTERNAL_SERVICE_ERROR = 50002  # 外部服务调用错误 (通用)
    AI_SERVICE_ERROR = 50003  # AI 服务特定错误

    # --- 6xxxx: 用餐区域 ---
    AREA_NOT_FOUND = 60001  # 用餐区域未找到
    AREA_NAME_EXISTS = 60002  # 区域名称已存在
    AREA_OCCUPIED = 60003  # 区域已被占用 (分配时)
    AREA_IS_FREE = 60004  # 区域已是空闲 (释放时)
    AREA_DELETE_FAILED = 60005  # 区域删除失败
    AREA_ASSIGN_FAILED = 60006  # 区域分配失败
    AREA_RELEASE_FAILED = 60007  # 区域释放失败

    # --- 7xxxx: 聊天 ---
    CHAT_NOT_FOUND = 70001  # 聊天记录未找到
    CHAT_INVALID_STATE = 70002  # 聊天状态无效或不允许当前操作
    CHAT_PROCESSING_FAILED = 70003  # 聊天处理失败

    # --- HTTP 状态码相关的通用错误码 (用于映射 HTTPException) ---
    # 使用 HTTP 状态码 * 100 作为一种约定
    HTTP_BAD_REQUEST = 40000  # 对应 400 Bad Request
    HTTP_UNAUTHORIZED = 40100  # 对应 401 Unauthorized
    HTTP_FORBIDDEN = 40300  # 对应 403 Forbidden
    HTTP_NOT_FOUND = 40400  # 对应 404 Not Found
    HTTP_METHOD_NOT_ALLOWED = 40500  # <--- 定义值
    HTTP_CONFLICT = 40900  # <--- 定义值
    HTTP_UNSUPPORTED_MEDIA_TYPE = 41500  # <--- 定义值
    HTTP_TOO_MANY_REQUESTS = 42900  # <--- 定义值
    HTTP_INTERNAL_SERVER_ERROR = 50000  # 对应 500 Internal Server Error
