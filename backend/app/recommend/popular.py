"""
@File       : popular.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2026-04-19)
@Description: 基于流行度（近期订单项数量）的推荐算法实现，适合新用户冷启动场景
"""

import logging

logger = logging.getLogger(__name__)


class PopularRecommender:
    """
    基于流行度的推荐器，按过去 30 天内菜品在订单项中出现的次数进行排名。

    解耦设计：算法不直接访问数据库，由外部传入查询结果。
    """

    @staticmethod
    def normalize_scores(raw_scores: dict[int, float]) -> dict[int, float]:
        """归一化得分，使总和为 1，用于推荐融合加权

        Args:
            raw_scores: {dish_id: raw_score}

        Returns:
            {dish_id: normalized_score}
        """
        total = sum(raw_scores.values()) or 1.0
        return {dish_id: score / total for dish_id, score in raw_scores.items()}

    def get_normalized_popular_scores(
        self,
        raw_scores: dict[int, float],
        limit: int = 10
    ) -> dict[int, float]:
        """获取归一化的热门菜品得分，用于推荐融合

        Args:
            raw_scores: 从数据库查询得到的 {dish_id: order_count}
            limit: 返回数量限制

        Returns:
            归一化得分 {dish_id: score}
        """
        logger.info(f"[融合用] 获取 Top-{limit} 热门菜品归一化打分...")

        if not raw_scores:
            logger.warning("没有热门菜品数据")
            return {}

        sorted_scores = sorted(
            raw_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )[:limit]

        raw_top = {dish_id: float(score) for dish_id, score in sorted_scores}
        return self.normalize_scores(raw_top)
