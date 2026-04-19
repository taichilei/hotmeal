"""
@File       : chart_service.py
@Date       : 2025-03-01 # 替换为当前日期
@Desc       : 图表和统计数据相关的服务层逻辑。


"""

import logging
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.dish import Dish
from app.models.enums import OrderState
from app.models.order import Order
from app.models.order_item import OrderItem

# 导入数据库实例和模型
from app.utils.db import db
from app.utils.error_codes import ErrorCode

# 导入异常和错误码
from app.utils.exceptions import APIException

logger = logging.getLogger(__name__)


def get_sales_ranking(limit: int = 10) -> list[dict[str, Any]]:
    """
    获取菜品销量排行榜。
    根据菜品在已支付或已完成订单中的总销售数量进行排名。

    Args:
        limit: 返回排行的数量上限。

    Returns:
        包含菜品名称和总销售数量的字典列表。
        例如: [{"dish_name": "宫保鸡丁", "count": 150}, ...]

    Raises:
        APIException: 如果查询数据库时发生错误。
    """
    logger.info(f"开始获取 Top-{limit} 菜品销售排行 (按销售数量)...")
    if limit <= 0:
        logger.warning("请求的 limit 小于等于 0，将使用默认值 10。")
        limit = 10  # 保证 limit 是正数

    try:
        # 定义有效的订单状态
        valid_order_states = [OrderState.PAID, OrderState.COMPLETED]

        # 构建查询语句
        stmt = (
            select(
                Dish.name.label('dish_name'),  # 选择菜品名称
                func.sum(OrderItem.quantity).label('total_quantity')  # 计算总销售数量
            )
            .select_from(OrderItem)  # 从 OrderItem 开始查询
            .join(Dish, OrderItem.dish_id == Dish.dish_id)  # 关联 Dish 获取名称
            .join(Order, OrderItem.order_id == Order.order_id)  # 关联 Order 获取状态
            .where(Order.state.in_(valid_order_states))  # 过滤有效的订单状态
            # 可以根据需要添加时间过滤，例如最近 30 天:
            # .where(Order.state.in_(valid_order_states), Order.created_at >= func.date_sub(func.now(), text("INTERVAL 30 DAY")))
            .group_by(Dish.dish_id, Dish.name)  # 按菜品分组
            .order_by(desc('total_quantity'))  # 按总销量降序
            .limit(limit)  # 限制结果数量
        )

        # 执行查询并将结果转换为字典列表
        results = db.session.execute(stmt).mappings().all()

        # 将结果格式化为 {"dish_name": ..., "count": ...}
        # 注意：SUM(quantity) 返回的可能是 Decimal 或 None (如果没有匹配项)，需要处理
        ranking_data = []
        for row in results:
            quantity = row['total_quantity']
            # 确保 count 是整数
            count = int(quantity) if quantity is not None else 0
            ranking_data.append({"dish_name": row['dish_name'], "count": count})

        logger.info(f"成功获取了 {len(ranking_data)} 条销售排行数据。")
        return ranking_data

    except SQLAlchemyError as db_err:
        logger.error(f"查询销售排行时发生数据库错误: {db_err}", exc_info=True)
        raise APIException("获取销售排行失败，数据库错误。",
                           error_code=ErrorCode.DATABASE_ERROR.value) from db_err
    except Exception as ex:
        logger.error(f"获取销售排行时发生未知错误: {ex}", exc_info=True)
        raise APIException("获取销售排行时发生未知错误。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value) from ex

# 你可以在这里添加其他图表相关的服务函数
