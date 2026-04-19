"""
@File       : redis_client.py
@Author     : ChiLei Tai JOU
@Date       : 2026-04-19
@Description: Redis 客户端封装，单例模式获取连接，提供缓存读写接口，用于缓存推荐算法数据
"""

import json
import logging
from typing import Any

import redis

from app.config import Config

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """
    获取 Redis 客户端单例。
    如果未配置 Redis 连接信息，返回 None。
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = Config._get_env_var('REDIS_URL')
    if not redis_url:
        host = Config._get_env_var('REDIS_HOST', 'localhost')
        port = Config._get_int_env_var('REDIS_PORT', 6379)
        db = Config._get_int_env_var('REDIS_DB', 0)
        password = Config._get_env_var('REDIS_PASSWORD')

        try:
            _redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            _redis_client.ping()
            logger.info("Redis 客户端初始化成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，将不使用缓存")
            _redis_client = None
    else:
        try:
            _redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            _redis_client.ping()
            logger.info("Redis 客户端初始化成功 (from URL)")
        except Exception as e:
            logger.warning(f"Redis 连接失败 (from URL): {e}，将不使用缓存")
            _redis_client = None

    return _redis_client


def get_cache(key: str) -> Any | None:
    """
    从 Redis 获取缓存数据，反序列化为 JSON。
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        data = client.get(key)
        if data is None:
            logger.debug(f"缓存未命中: {key}")
            return None
        logger.debug(f"缓存命中: {key}")
        return json.loads(data)
    except Exception as e:
        logger.error(f"从 Redis 获取缓存失败 {key}: {e}", exc_info=True)
        return None


def set_cache(key: str, value: Any, expire_seconds: int = 0) -> bool:
    """
    将数据序列化后存入 Redis 缓存。
    如果 expire_seconds 为 0，则永久存储。
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        json_data = json.dumps(value)
        if expire_seconds > 0:
            client.setex(key, expire_seconds, json_data)
        else:
            client.set(key, json_data)
        logger.debug(f"缓存已保存: {key}")
        return True
    except Exception as e:
        logger.error(f"保存缓存到 Redis 失败 {key}: {e}", exc_info=True)
        return False


def delete_cache(key: str) -> bool:
    """删除指定缓存"""
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.delete(key)
        logger.debug(f"缓存已删除: {key}")
        return True
    except Exception as e:
        logger.error(f"删除缓存失败 {key}: {e}", exc_info=True)
        return False


def is_redis_available() -> bool:
    """检查 Redis 是否可用"""
    return get_redis_client() is not None
