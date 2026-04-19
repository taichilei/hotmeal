"""
@File       : recommend_routes.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 菜品推荐相关 API 端点
"""

import logging
from http import HTTPStatus

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields

from app.services.recommend_service import RecommendationService
from app.utils.decorators import log_request, timing
from app.utils.response import success, unauthorized

logger = logging.getLogger(__name__)

recommender = RecommendationService()

# --- Namespace 定义 ---
# 路径改为复数形式 '/recommendations'
recommend_ns = Namespace('recommendations', description='获取菜品推荐的操作',
                         path='/recommendations')

# --- 输出模型 ---
recommendation_item_model = recommend_ns.model('RecommendationItem', {
    'dish_id': fields.Integer(description='推荐的菜品 ID', example=101),
    'score': fields.Float(description='推荐分数 (可能代表相似度、销量或其他指标)', example=0.85),
    'dish_name': fields.String(description='推荐菜品名称', example='宫保鸡丁')
})

recommendation_output_model = recommend_ns.model('RecommendationOutput', {
    'recommendations': fields.List(fields.Nested(recommendation_item_model),
                                   description='推荐的菜品列表')
})


# --- 路由 ---
@recommend_ns.route("/")
class GetRecommendations(Resource):
    # 应用装饰器
    method_decorators = [jwt_required(), log_request, timing]  # 使用 jwt_required

    @recommend_ns.doc('get_recommendations', security='jsonWebToken')  # 添加文档和安全说明
    @recommend_ns.param('limit', '返回的推荐数量上限', type=int, default=10,
                        location='args')  # 文档化 limit 参数
    @recommend_ns.param(
        'strategy',
        "推荐策略，可选值：\n"
        "- auto：系统自动融合多种推荐算法（默认）\n"
        "- popular：仅使用热门推荐\n"
        "- usercf：使用基于用户的协同过滤推荐\n"
        "- profile：基于用户画像推荐（预留）",
        type=str, default='auto', location='args'
    )
    @recommend_ns.param(
        'weights',
        '策略融合权重，仅当 strategy=weighted 时生效。格式为 usercf,itemcf,popular，例如：0.5,0.3,0.2，总和应为1.0',
        type=str, location='args'
    )
    @recommend_ns.response(HTTPStatus.OK, '成功获取推荐列表', recommendation_output_model)
    @recommend_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证或令牌无效')
    @recommend_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取推荐时发生错误')
    @recommend_ns.response(HTTPStatus.BAD_REQUEST, '请求参数错误')
    def get(self):
        """获取当前登录用户的推荐菜品列表"""
        try:
            # --- 使用 get_jwt_identity() 获取用户 ID ---
            current_user_id_str = get_jwt_identity()
            if not current_user_id_str:  # 再次确认身份信息存在
                raise ValueError("JWT identity is missing")
            current_user_id = int(current_user_id_str)  # 转换为整数
        except (ValueError, TypeError):
            logger.warning("无法从 JWT 获取有效的用户 ID。")
            return unauthorized("无效的用户身份令牌。")

        # 获取 limit 参数
        try:
            limit = int(request.args.get('limit', 10))
            if limit <= 0:
                limit = 10  # 如果无效则使用默认值
        except ValueError:
            limit = 10  # 如果参数不是数字则使用默认值

        strategy = request.args.get('strategy', 'auto')

        weights_str = request.args.get('weights')
        weights = None
        if weights_str:
            try:
                weights = list(map(float, weights_str.split(',')))
                if len(weights) != 3 or not abs(sum(weights) - 1.0) < 1e-4:
                    raise ValueError
            except ValueError:
                logger.warning("权重格式错误，应为3个浮点数，总和为1.0，例如 0.5,0.3,0.2")
                return {
                    "message": "权重格式错误，应为3个浮点数，总和为1.0，例如 0.5,0.3,0.2",
                    "error_code": 400
                }, HTTPStatus.BAD_REQUEST

        logger.info(f"用户 {current_user_id} 请求推荐，limit={limit}")

        recommendations_list = recommender.recommend(
            user_id=current_user_id,
            limit=limit,
            strategy=strategy,
            weights=weights
        )

        return success(message="成功获取推荐列表",
                       data={"recommendations": recommendations_list})
