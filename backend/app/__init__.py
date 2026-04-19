"""
@File       : __init__.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: Flask 应用的初始化文件（应用工厂）。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restx import Api

from app.config import config
from app.utils.db import db
from app.utils.json_encoder import CustomJSONProvider
from app.utils.response import register_error_handlers

logging.getLogger('flask_cors').level = logging.DEBUG
logger = logging.getLogger("hotmeal")  # 获取 logger 实例

# 在应用工厂外创建扩展实例
cors = CORS()
jwt = JWTManager()
migrate = Migrate()
# API 实例也在这里创建，但在工厂内初始化
api = Api(
    title='HotMeal API',
    version='1.0',
    description='HotMeal API 文档',
    doc='/docs',
    prefix='/api/v1',
    catch_all_http_exceptions=False
)

load_dotenv()


def register_extensions(app: Flask):
    """集中注册 Flask 扩展。"""
    cors.init_app(app, resources={r"/api/v1/.*": {"origins": "*"}}, supports_credentials=True)
    db.init_app(app)  # 初始化 SQLAlchemy
    migrate.init_app(app, db)  # <--- 初始化 Migrate
    jwt.init_app(app)  # 初始化 JWTManager
    api.init_app(app)  # 初始化 Flask-RESTX Api
    # 可以在这里初始化其他扩展，如缓存 Flask-Caching 等


def register_namespaces(api_instance: Api):  # 接收 Api 实例作为参数
    """注册所有 API 命名空间。"""
    # 导入 Namespaces
    from app.routes.admin_routes import admin_ns
    from app.routes.auth_routes import auth_ns
    from app.routes.category_routes import category_ns
    from app.routes.chat_routes import chat_ns
    from app.routes.dining_area_routes import area_ns
    from app.routes.dish_routes import dish_ns
    from app.routes.health import api as health_ns
    from app.routes.order_routes import order_ns
    from app.routes.recommend_routes import recommend_ns
    from app.routes.staff_routes import staff_ns
    from app.routes.tag_routes import tag_ns
    from app.routes.user_routes import user_ns

    # 添加 Namespace 到 Api 实例
    api_instance.add_namespace(health_ns, path='/health')
    api_instance.add_namespace(user_ns, path='/users')
    api_instance.add_namespace(admin_ns, path='/admin')
    api_instance.add_namespace(category_ns, path='/categories')
    api_instance.add_namespace(dish_ns, path='/dishes')
    api_instance.add_namespace(order_ns, path='/orders')
    api_instance.add_namespace(area_ns, path='/dining-areas')
    api_instance.add_namespace(chat_ns, path='/chats')
    api_instance.add_namespace(recommend_ns, path='/recommendations')
    api_instance.add_namespace(auth_ns, path='/auth')
    api_instance.add_namespace(staff_ns, path='/staff')
    api_instance.add_namespace(tag_ns, path='/tags')
    logger.info("所有 API 命名空间注册完成。")


def create_app(config_name: str | None = None) -> Flask:
    """
    应用工厂函数。

    Args:
        config_name: 要使用的配置名称 (例如 'development', 'production', 'testing')。
                     如果为 None，会尝试从 FLASK_CONFIG 环境变量获取，否则默认为 'default'。

    Returns:
        配置好的 Flask 应用实例。
    """
    # 如果未指定 config_name，尝试从环境变量获取，否则使用 default
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    logger.info(f"使用配置 '{config_name}' 创建应用...")

    # --- 从配置对象加载配置 ---
    try:
        app.config.from_object(config[config_name])
        logger.info("配置加载成功。")
    except KeyError:
        logger.error(f"无效的配置名称: '{config_name}'。将使用默认配置。")
        app.config.from_object(config['default'])  # 回退到默认配置

    # 设置自定义 JSON Provider
    app.json_provider_class = CustomJSONProvider
    app.json = app.json_provider_class(app)  # 确保 provider 被应用

    # --- 注册扩展 ---
    register_extensions(app)
    logger.info("Flask 扩展注册完成。")

    # --- 注册 API 命名空间 ---
    register_namespaces(api)

    # --- 注册全局错误处理器 ---
    register_error_handlers(app)
    logger.info("全局错误处理器注册完成。")

    # 可以在这里添加其他应用级别的设置或钩子

    logger.info("Flask 应用实例创建完成。")
    return app
