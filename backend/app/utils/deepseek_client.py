"""
@File       : deepseek_client.py
@Date       : 2025-03-01
@Description: Provides a configured OpenAI client instance for interacting with the DeepSeek API.
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import logging

# 导入 Flask 当前应用上下文，以便访问配置
from flask import Flask, current_app

# 导入 openai 库，现在使用其类
from openai import OpenAI  # 显式导入 OpenAI 类

from app.utils.error_codes import ErrorCode
from app.utils.exceptions import APIException

logger = logging.getLogger(__name__)

# 不再需要在模块级别加载 .env 或读取/设置全局 openai 属性
# load_dotenv()
# api_key = os.getenv("DEEPSEEK_API_KEY")
# if not api_key: ...
# openai.api_base = ...
# openai.api_key = ...

# 全局变量存储客户端实例 (可选，用于简单的单例模式)
_deepseek_client_instance = None


def get_deepseek_client(app: Flask | None = None) -> OpenAI:
    """
    获取或创建一个配置好的用于 DeepSeek API 的 OpenAI 客户端实例。

    从 Flask 应用配置中读取 API Key 和 Base URL。
    如果配置缺失，会记录错误并抛出 ValueError。

    Args:
        app: (可选) Flask 应用实例。如果未提供，则尝试使用 current_app。

    Returns:
        一个配置好的 openai.OpenAI 客户端实例。

    Raises:
        ValueError: 如果配置中缺少 DEEPSEEK_API_KEY。
        RuntimeError: 如果在 Flask 应用上下文之外且未提供 app 参数。
    """
    global _deepseek_client_instance

    # 优先使用传入的 app，否则使用 current_app
    current_flask_app = app or current_app
    if not current_flask_app:
        raise RuntimeError("无法获取 Flask 应用实例。请在应用上下文中调用或提供 app 参数。")

    # 检查是否已有实例 (简单的单例实现)
    # 注意：在多进程/多线程环境或不同 app 实例下，这个简单的单例可能不适用
    # if _deepseek_client_instance:
    #     return _deepseek_client_instance

    # 从 Flask 应用配置中获取信息
    # 我们在 config.py 中已经设置了从环境变量读取 DEEPSEEK_API_KEY
    api_key = current_flask_app.config.get('DEEPSEEK_API_KEY')
    # 可以将 Base URL 也放入配置
    base_url = current_flask_app.config.get('DEEPSEEK_BASE_URL',
                                            "https://api.deepseek.com")  # 提供默认值

    if not api_key:
        logger.error("配置中未找到 DEEPSEEK_API_KEY。请检查应用配置或环境变量。")
        raise ValueError("缺少 DeepSeek API Key 配置。")

    logger.info(f"正在创建 DeepSeek API 客户端，Base URL: {base_url}")

    try:
        # 使用 OpenAI() 类创建实例，并传入参数
        client_instance = OpenAI(
            api_key=api_key,
            base_url=base_url,
            # 可以添加其他配置，如 timeout, max_retries 等
            # timeout=httpx.Timeout(60.0, connect=5.0)
        )
        # 简单的单例赋值
        # _deepseek_client_instance = client_instance
        # return _deepseek_client_instance
        return client_instance  # 直接返回新实例，避免简单的全局单例问题
    except Exception as ex:
        logger.error(f"创建 OpenAI 客户端实例时出错: {ex}", exc_info=True)
        # 可以重新抛出更具体的异常
        raise APIException("初始化 AI 服务客户端失败。",
                           error_code=ErrorCode.EXTERNAL_SERVICE_ERROR) from ex

# --- 如何在服务层使用 ---
# from app.utils.deepseek_client import get_deepseek_client
# from app.utils.exceptions import APIException
#
# def some_service_function():
#     try:
#         client = get_deepseek_client() # 获取客户端实例
#         response = client.chat.completions.create(...)
#         return response.choices[0].message.content
#     except (ValueError, APIException, openai.APIError) as e:
#          logger.error(f"调用 DeepSeek 服务时出错: {e}")
#          # 处理错误或重新抛出
#          raise BusinessError("AI 服务暂时不可用。") from e
