# -*- coding: utf-8 -*-
"""
@File       : config.py
@Date       : 2025-03-01 
@Description: 应用配置。统一了 JWT 密钥配置。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import os
import sys
import logging
import warnings

from dotenv import load_dotenv
from typing import Dict, Any, Optional  # 导入 Optional

load_dotenv()

logger = logging.getLogger(__name__)


def _get_env_var(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """获取环境变量，如果未设置且没有默认值，记录警告。"""
    value = os.getenv(var_name, default)
    # if value is None: # 移除，因为 validate_config 会处理必需变量
    #     logger.warning(f"环境变量 '{var_name}' 未设置，将使用默认值 '{default}' 或 None。")
    return value


def _get_int_env_var(var_name: str, default: int) -> int:
    """获取整数类型的环境变量，处理转换错误。"""
    value_str = _get_env_var(var_name, str(default))
    try:
        return int(value_str)  # type: ignore
    except (ValueError, TypeError):
        logger.warning(
            f"环境变量 '{var_name}' 的值 '{value_str}' 不是有效的整数。将使用默认值 {default}。")
        # 在 Python 3.9+ 中可以使用 warnings.warn
        # warnings.warn(f"Invalid integer value for env var '{var_name}': '{value_str}'. Using default {default}.", UserWarning)
        return default


def _get_bool_env_var(var_name: str, default: bool = False) -> bool:
    """获取布尔类型的环境变量。"""
    value_str = _get_env_var(var_name, str(default)).lower()
    return value_str in ['true', '1', 't', 'y', 'yes']


def validate_config() -> Dict[str, Any]:
    """验证必需的环境变量。"""
    # --- 调整：SQLite 模式下只需要 SECRET_KEY ---
    required_vars_desc = {
        'SECRET_KEY': 'Flask 应用密钥',  # JWT 会优先使用 JWT_SECRET_KEY 或回退到此
    }

    missing_vars = []

    for var, description in required_vars_desc.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({description})")

    if missing_vars:
        logger.critical("错误：缺少必要的环境变量:")  # 使用 CRITICAL 级别
        logger.critical("\n".join(f"- {var}" for var in missing_vars))
        logger.critical("\n请检查你的 .env 文件或环境配置。应用无法启动。")
        sys.exit(1)  # 缺少关键配置，直接退出

    return {}  # 返回空字典，因为值在 Config 类中获取


# 在应用启动前执行验证
validate_config()


class Config:
    """基础配置类"""
    # --- 从环境变量获取值，并提供类型转换和默认值 ---
    # Flask & Security
    SECRET_KEY = _get_env_var('SECRET_KEY')  # 已验证必需
    # --- 统一 JWT 密钥配置 ---
    JWT_SECRET_KEY = _get_env_var('JWT_SECRET_KEY',
                                  SECRET_KEY)  # 优先环境变量 JWT_SECRET_KEY，否则使用 SECRET_KEY
    DEBUG = False
    TESTING = False

    # Database configuration using _get_env_var helper
    DB_USER = _get_env_var('DB_USER')
    DB_PASSWORD = _get_env_var('DB_PASSWORD')
    DB_HOST = _get_env_var('DB_HOST')
    DB_PORT = _get_env_var('DB_PORT')
    DB_NAME = _get_env_var('DB_NAME')

    # SQLAlchemy configuration with defaults and type conversion
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 提供合理的默认值
    SQLALCHEMY_POOL_SIZE = _get_int_env_var('DB_POOL_SIZE', 10)
    SQLALCHEMY_POOL_TIMEOUT = _get_int_env_var('DB_POOL_TIMEOUT', 30)
    SQLALCHEMY_POOL_RECYCLE = _get_int_env_var('DB_POOL_RECYCLE', 1800)  # 例如 30 分钟
    SQLALCHEMY_ECHO = _get_bool_env_var('SQLALCHEMY_ECHO', False)

    # Build database URI (确保必需变量已存在)
    # 使用 SQLite 数据库用于演示，无需 MySQL
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'hotmeal.db')}"
    logger.info(f"使用 SQLite 数据库: {SQLALCHEMY_DATABASE_URI}")

    # External API configuration
    DEEPSEEK_API_KEY = _get_env_var('DEEPSEEK_API_KEY', '')

    # Logging configuration with defaults
    LOG_LEVEL = _get_env_var('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = _get_env_var('LOG_FILE', 'logs/app.log')  # 默认路径
    LOG_MAX_BYTES = _get_int_env_var('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
    LOG_BACKUP_COUNT = _get_int_env_var('LOG_BACKUP_COUNT', 5)

    # Caching configuration with default
    CACHE_TYPE = _get_env_var('CACHE_TYPE', 'SimpleCache')  # Flask-Caching 默认 SimpleCache

    # --- 推荐系统配置 ---
    RECOMMEND_LIMIT_DEFAULT = _get_int_env_var("RECOMMEND_LIMIT_DEFAULT", 5)
    RECOMMEND_LIMIT_MAX = _get_int_env_var("RECOMMEND_LIMIT_MAX", 20)
    RECOMMEND_STRATEGY_DEFAULT = _get_env_var("RECOMMEND_STRATEGY_DEFAULT", "weighted")
    RECOMMEND_CACHE_SECONDS = _get_int_env_var("RECOMMEND_CACHE_SECONDS", 300)
    RECOMMEND_WEIGHT_USER = float(_get_env_var("RECOMMEND_WEIGHT_USER", "0.4"))
    RECOMMEND_WEIGHT_POPULAR = float(_get_env_var("RECOMMEND_WEIGHT_POPULAR", "0.6"))

    @staticmethod
    def init_app(app):
        """此方法通常用于执行特定于配置的初始化，例如设置日志处理器。"""
        # 基类可以为空，由子类实现具体逻辑
        pass


class DevConfig(Config):
    """开发环境配置"""
    ENV = 'development'  # 设置环境标识
    DEBUG = _get_bool_env_var('DEBUG', True)  # 开发环境默认开启 Debug
    SQLALCHEMY_ECHO = _get_bool_env_var('SQLALCHEMY_ECHO', True)  # 开发环境默认开启 SQL Echo

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print(
            f"--- HotMeal 应用正在以 *开发模式* 运行 (Debug: {cls.DEBUG}, SQL Echo: {cls.SQLALCHEMY_ECHO}) ---")
        # 开发环境不需要额外的日志处理器，Flask 默认的够用


class ProdConfig(Config):
    """生产环境配置"""
    ENV = 'production'
    DEBUG = False  # 生产环境强制关闭 Debug
    TESTING = False
    SQLALCHEMY_ECHO = False  # 生产环境强制关闭 SQL Echo

    # 生产环境可以有不同的连接池设置
    SQLALCHEMY_POOL_SIZE = _get_int_env_var('PROD_DB_POOL_SIZE', 20)  # 生产环境默认值可以更大
    SQLALCHEMY_POOL_RECYCLE = _get_int_env_var('PROD_DB_POOL_RECYCLE', 1200)  # 回收时间可以短一些

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print(f"--- HotMeal 应用正在以 *生产模式* 运行 ---")
        # 生产环境必须有 SECRET_KEY (Config 基类已包含)
        if not cls.SECRET_KEY:
            # 这个断言理论上不会触发，因为 validate_config 检查了
            raise ValueError("生产环境中必须设置 SECRET_KEY！")
        if cls.SECRET_KEY == 'testing-secret-key' or cls.SECRET_KEY == 'dev-key':  # 避免使用弱密钥
            warnings.warn("生产环境使用了不安全的默认 SECRET_KEY！请务必在环境变量中设置强密钥。",
                          UserWarning)

        # 配置生产环境日志记录器 (可以移到 app.utils.logger.py 中根据环境配置)
        import logging
        from logging.handlers import RotatingFileHandler

        # 确保日志目录存在
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 添加文件处理器
        file_handler = RotatingFileHandler(
            filename=cls.LOG_FILE,
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT,
            encoding='utf-8'  # 明确编码
        )
        # 设置日志级别为 INFO 或更高
        log_level_int = getattr(logging, cls.LOG_LEVEL, logging.INFO)  # 获取日志级别对象
        file_handler.setLevel(log_level_int if log_level_int >= logging.INFO else logging.INFO)

        # 设置格式化器
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s in %(module)s: %(message)s"  # 更详细的格式
        )
        file_handler.setFormatter(formatter)

        # 将处理器添加到 app.logger (移除默认处理器以避免重复)
        # for handler in app.logger.handlers[:]:
        #     app.logger.removeHandler(handler)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level_int if log_level_int >= logging.INFO else logging.INFO)
        # 对于 werkzeug 日志，可以单独配置或保持默认
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

        logger.info(f"生产环境日志已配置到文件: {cls.LOG_FILE}")


class TestConfig(Config):
    """测试环境配置"""
    ENV = 'testing'
    TESTING = True  # 明确设置 TESTING
    DEBUG = False  # 测试时通常关闭 Debug
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # 使用内存数据库，速度快且自动清理
    # 或者使用临时文件数据库: "sqlite:///" + os.path.join(basedir, 'test_temp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 测试时连接池可以小一些
    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_POOL_TIMEOUT = 10
    SQLALCHEMY_POOL_RECYCLE = 300
    # 测试时 JWT 密钥可以固定或从环境变量读取
    # JWT_SECRET_KEY 继承自 Config，会使用 os.getenv('JWT_SECRET_KEY', Config.SECRET_KEY)
    # 如果需要测试特定的 JWT 密钥，可以在这里覆盖
    # JWT_SECRET_KEY = 'test-jwt-secret'

    # 测试时通常不需要详细的文件日志，可以将级别设高或输出到控制台
    LOG_LEVEL = "WARNING"
    # LOG_FILE = "test.log" # 如果需要测试日志文件
    CACHE_TYPE = "NullCache"  # 使用 NullCache 禁用缓存

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print(f"--- HotMeal 应用正在以 *测试模式* 运行 ---")


# 配置映射字典
config = {
    "development": DevConfig,
    "production": ProdConfig,
    "testing": TestConfig,
    "default": DevConfig,  # 默认使用开发配置
}
