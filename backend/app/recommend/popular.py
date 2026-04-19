"""
@File       : popular.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 基于流行度（近期订单项数量）的推荐算法实现。
              已适配 Flask-SQLAlchemy session 并修正查询逻辑。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms
"""

import logging
from typing import Any

from sqlalchemy import text

from app.utils.db import db

logger = logging.getLogger(__name__)


class PopularRecommender:
    """
    基于流行度的推荐器，按过去 30 天内菜品在订单项中出现的次数进行排名。
    """
    @staticmethod
    def get_popular_dishes(limit=10) -> list[dict[str, Any]]:
        """
        返回过去 30 天内最受欢迎（按订单项数量）的 Top-N 菜品，包含菜品名称与销量。

        用途：
        - 主要用于前端展示，如首页 Banner 区域、热销榜单等视觉模块。
        - 包含 dish_name 和 score，便于 UI 渲染展示。
        """
        logger.info(f"开始获取 Top-{limit} 热门菜品...")
        try:
            # 为提升推荐模块聚合查询性能，此处使用原生 SQL 而非 ORM 查询
            # --- 重写查询逻辑：统计 order_items 中 dish_id 的出现次数，并联表查询菜品名称 ---
            query = text("""
                SELECT
                    oi.dish_id,
                    d.name AS dish_name,
                    COUNT(oi.order_item_id) AS order_item_count
                FROM
                    order_items oi
                JOIN
                    orders o ON oi.order_id = o.order_id
                JOIN
                    dish d ON oi.dish_id = d.dish_id
                WHERE
                    o.created_at >= DATETIME('now', '-30 days')
                -- 注意：此处使用 SQLite 兼容写法，生产环境下如使用 MySQL，需恢复为 DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY
                    oi.dish_id, d.name
                ORDER BY
                    order_item_count DESC,
                    oi.dish_id ASC
                LIMIT :limit
            """)
            results = db.session.execute(query, {"limit": limit}).fetchall()

            # 返回结果，score 代表订单项数量，附带菜品名称
            recommendations = [
                {"dish_id": row[0], "dish_name": row[1], "score": row[2]} for row in results
            ]
            logger.info(f"成功获取了 {len(recommendations)} 条热门菜品推荐。")
            return recommendations

        except Exception as ex:
            logger.error(f"获取热门菜品时出错: {ex}", exc_info=True)
            return []  # 出错时返回空列表

    @staticmethod
    def get_popular_scores(limit=10) -> dict[int, float]:
        """
        返回过去 30 天内最受欢迎的菜品及其得分映射。
        用途：
        - 用于后端推荐融合排序，如在 weighted 策略中参与打分加权。
        - 返回格式为 {dish_id: score}，适合推荐模块内部排序与融合逻辑。
        - 不用于前端直接展示。
        """
        logger.info(f"[融合用] 获取 Top-{limit} 热门菜品打分...")
        try:
            # 为提升推荐模块聚合查询性能，此处使用原生 SQL 而非 ORM 查询
            query = text("""
                SELECT
                    oi.dish_id,
                    COUNT(oi.order_item_id) AS order_item_count
                FROM
                    order_items oi
                JOIN
                    orders o ON oi.order_id = o.order_id
                WHERE
                    o.created_at >= DATETIME('now', '-30 days')
                -- 注意：此处使用 SQLite 兼容写法，生产环境下如使用 MySQL，需恢复为 DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY
                    oi.dish_id
                ORDER BY
                    order_item_count DESC,
                    oi.dish_id ASC
                LIMIT :limit
            """)
            results = db.session.execute(query, {"limit": limit}).fetchall()
            return {row[0]: float(row[1]) for row in results}
        except Exception as ex:
            logger.error(f"[融合用] 获取热门菜品打分出错: {ex}", exc_info=True)
            return {}

    @staticmethod
    def get_normalized_popular_scores(limit=10) -> dict[int, float]:
        """
        返回归一化的热门菜品得分（销量归一化，总和为 1），用于推荐融合中的相对热度分数。

        用途：
        - 推荐融合时，将销量映射为“热度权重”参与加权排序。
        - 符合 softmax-style attention 机制思想：每个菜品在推荐池中的竞争概率。
        - 适合作为服务层融合策略的热度分数来源。
        """
        logger.info(f"[融合用] 获取 Top-{limit} 热门菜品归一化打分...")
        try:
            query = text("""
                SELECT
                    oi.dish_id,
                    COUNT(oi.order_item_id) AS order_item_count
                FROM
                    order_items oi
                JOIN
                    orders o ON oi.order_id = o.order_id
                WHERE
                    o.created_at >= DATETIME('now', '-30 days')
                -- 注意：此处使用 SQLite 兼容写法，生产环境下如使用 MySQL，需恢复为 DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY
                    oi.dish_id
                ORDER BY
                    order_item_count DESC,
                    oi.dish_id ASC
                LIMIT :limit
            """)
            results = db.session.execute(query, {"limit": limit}).fetchall()
            raw_scores = {row[0]: float(row[1]) for row in results}
            total = sum(raw_scores.values()) or 1.0
            return {dish_id: score / total for dish_id, score in raw_scores.items()}
        except Exception as ex:
            logger.error(f"[融合用] 获取热门菜品归一化打分出错: {ex}", exc_info=True)
            return {}
