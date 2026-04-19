"""
@File       : chart_routes.py
@Date       : 2025-03-01
@Desc       : 提供图表和统计数据的相关 API 端点。


"""

import logging
from http import HTTPStatus

# --- 添加必要的导入 ---
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

# --- 导入服务层 ---
from app.services import chart_service

# --- 导入装饰器和响应工具 ---
from app.utils.decorators import log_request, timing  # 移除 require_roles (如果不需要)
from app.utils.response import bad_request, success

# --- 导入模型枚举（如果需要权限检查）---
# from app.models.enums import UserRole
# --- 导入异常（如果需要特定捕获）---

logger = logging.getLogger(__name__)

# --- Namespace 定义 ---
chart_ns = Namespace('charts', description='图表和统计数据接口', path='/charts')

# --- 输入/输出模型 ---

sales_ranking_item_model = chart_ns.model('SalesRankingItem', {
    'dish_name': fields.String(description='菜品名称'),
    'count': fields.Integer(description='销量或订单次数')
})

sales_ranking_output_model = chart_ns.model('SalesRankingOutput', {
    'ranking': fields.List(fields.Nested(sales_ranking_item_model), description='销售排行列表')
})


# --- 路由 ---
@chart_ns.route('/sales-ranking')
class SalesRanking(Resource):
    method_decorators = [
        log_request,
        timing,
        jwt_required(),
        # require_roles([UserRole.ADMIN.name, UserRole.STAFF.name]) # 根据权限需求启用
    ]

    @chart_ns.doc('get_sales_ranking', security='jsonWebToken')
    @chart_ns.param('limit', '返回排行的数量', type=int, default=10, location='args')
    @chart_ns.response(HTTPStatus.OK, '成功获取销售排行', sales_ranking_output_model)
    @chart_ns.response(HTTPStatus.BAD_REQUEST, '无效的 limit 参数')
    @chart_ns.response(HTTPStatus.UNAUTHORIZED, '需要认证')
    @chart_ns.response(HTTPStatus.FORBIDDEN, '权限不足')
    @chart_ns.response(HTTPStatus.INTERNAL_SERVER_ERROR, '获取排行失败')
    def get(self):
        """获取菜品销量排行榜"""
        try:
            limit = int(request.args.get('limit', 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            # 直接返回错误响应
            return bad_request("limit 参数必须是整数。")
        # --- 如果需要在路由层捕获 ValidationError ---
        # except ValidationError as ve:
        #     return bad_request(ve.message, error_code=ve.error_code)

        logger.info(f"请求销量排行榜，limit={limit}")

        # 调用服务层获取数据 (依赖全局错误处理)
        ranking_data = chart_service.get_sales_ranking(limit=limit)

        return success(message="成功获取销量排行榜", data={"ranking": ranking_data})
