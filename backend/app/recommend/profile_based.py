"""
@File       : profile_based.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2026-04-19)
@Description: 基于用户画像（偏好菜系）的推荐算法，适合用户偏好明确的冷启动场景
@Copyright  : Copyright © 2025. All rights reserved.
"""
import logging

logger = logging.getLogger(__name__)


class ProfileRecommender:
    """基于用户画像（偏好菜系）推荐菜品，采用混合策略

    解耦设计：算法不直接访问数据库，数据由外部传入。
    """

    @staticmethod
    def recommend_by_profile(
        user_preference: str | None,
        available_dishes: list[tuple[int, float]],
        limit: int = 10
    ) -> dict[int, float]:
        """根据用户的偏好菜系推荐菜品，返回归一化得分

        Args:
            user_preference: 用户偏好菜系名称，可以为 None
            available_dishes: 符合偏好的菜品列表 [(dish_id, sales), ...]
            limit: 返回数量限制

        Returns:
            归一化得分 {dish_id: score}
        """
        if not user_preference:
            logger.info("无法获取用户偏好菜系，无法进行基于画像的推荐。")
            return {}

        if not available_dishes:
            logger.info(f"偏好 '{user_preference}' 没有可用菜品")
            return {}

        logger.info(f"为用户根据偏好 '{user_preference}' 生成推荐...")

        # 按销量降序排序
        sorted_dishes = sorted(
            available_dishes,
            key=lambda item: item[1],
            reverse=True
        )[:limit]

        raw_scores = {dish_id: float(sales) for dish_id, sales in sorted_dishes}
        total = sum(raw_scores.values()) or 1.0
        normalized = {dish_id: score / total for dish_id, score in raw_scores.items()}

        logger.info(f"生成了 {len(normalized)} 条基于画像的推荐（归一化得分）。")
        return normalized
