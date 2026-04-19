"""
@File       : item_cf.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2026-04-19)
@Description: 基于菜品相似度的协同过滤推荐算法，支持 Redis 缓存相似度矩阵和时间衰减优化
"""

import logging
from typing import Any

import numpy as np

from app.config import Config
from app.recommend.time_decay import TimeDecayHelper
from app.utils.redis_client import (
    delete_cache,
    get_cache,
    is_redis_available,
    set_cache,
)

logger = logging.getLogger(__name__)

REDIS_CACHE_KEY = "itemcf:dish_similarity"


class ItemCFRecommender:
    """基于菜品相似度的协同过滤推荐器

    优化：
    1. 使用 Redis 缓存相似度矩阵，避免每次推荐都重新计算
    2. 解耦数据库访问：相似度计算由外部传入用户-菜品购买数据，不直接依赖 db
    如果 Redis 不可用，回退到内存缓存。
    """

    _cached_similarity: dict[int, dict[int, float]] | None = None

    def compute_dish_similarity(self, user_dish_matrix: dict[int, set[int]]) -> dict[int, dict[int, float]]:
        """基于共同购买行为计算菜品相似度矩阵

        Args:
            user_dish_matrix: 用户-菜品购买矩阵 {user_id: {dish_id, ...}, ...}

        Returns:
            相似度字典 {dish_a: {dish_b: similarity, ...}, ...}
        """
        logger.info("开始计算菜品相似度矩阵...")

        if not user_dish_matrix:
            logger.warning("没有有效的用户购买数据来计算相似度。")
            return {}

        dish_similarity: dict[int, dict[int, float]] = {}
        dishes = list({dish for dishes in user_dish_matrix.values() for dish in dishes})
        logger.info(f"共涉及 {len(dishes)} 个不同的菜品进行相似度计算。")

        dish_user_matrix: dict[int, set[int]] = {}
        for user_id, user_dishes in user_dish_matrix.items():
            for dish_id in user_dishes:
                dish_user_matrix.setdefault(dish_id, set()).add(user_id)

        for i, dish_a in enumerate(dishes):
            for j in range(i + 1, len(dishes)):
                dish_b = dishes[j]

                users_a = dish_user_matrix.get(dish_a, set())
                users_b = dish_user_matrix.get(dish_b, set())

                intersection = len(users_a & users_b)
                len_a = len(users_a)
                len_b = len(users_b)

                if intersection > 0 and len_a > 0 and len_b > 0:
                    similarity = intersection / np.sqrt(len_a * len_b)
                else:
                    similarity = 0.0

                if similarity > 0:
                    dish_similarity.setdefault(dish_a, {})[dish_b] = similarity
                    dish_similarity.setdefault(dish_b, {})[dish_a] = similarity

        logger.info("菜品相似度矩阵计算完成。")
        return dish_similarity

    def get_dish_similarity(self, user_dish_matrix: dict[int, set[int]]) -> dict[int, dict[int, float]]:
        """获取菜品相似度矩阵

        优先从 Redis 缓存读取，如果缓存未命中则计算并缓存。
        如果 Redis 不可用，使用内存缓存。

        Args:
            user_dish_matrix: 用户-菜品购买矩阵，缓存未命中时用于重新计算

        Returns:
            相似度字典
        """
        if self._cached_similarity is not None:
            logger.debug("使用内存缓存中的相似度矩阵")
            return self._cached_similarity

        if is_redis_available():
            cached = get_cache(REDIS_CACHE_KEY)
            if cached is not None:
                logger.info("从 Redis 加载相似度矩阵缓存")
                self._cached_similarity = cached
                return cached

        logger.info("缓存未命中，重新计算相似度矩阵")
        similarity = self.compute_dish_similarity(user_dish_matrix)

        if similarity:
            self._cached_similarity = similarity
            if is_redis_available():
                expire = Config.RECOMMEND_CACHE_SECONDS
                set_cache(REDIS_CACHE_KEY, similarity, expire)
                logger.info(f"相似度矩阵已缓存到 Redis，过期时间 {expire} 秒")

        return similarity

    def refresh_similarity(self, user_dish_matrix: dict[int, set[int]]) -> bool:
        """强制刷新相似度矩阵缓存

        重新计算并更新缓存。可在后台任务或管理接口调用。

        Args:
            user_dish_matrix: 最新的用户-菜品购买矩阵

        Returns:
            是否刷新成功
        """
        logger.info("强制刷新相似度矩阵...")
        similarity = self.compute_dish_similarity(user_dish_matrix)

        if not similarity:
            logger.error("刷新相似度矩阵失败：计算结果为空")
            return False

        self._cached_similarity = similarity

        if is_redis_available():
            delete_cache(REDIS_CACHE_KEY)
            expire = Config.RECOMMEND_CACHE_SECONDS
            set_cache(REDIS_CACHE_KEY, similarity, expire)
            logger.info("相似度矩阵已更新到 Redis 缓存")

        logger.info("相似度矩阵刷新完成")
        return True

    def recommend_by_item_similarity(
        self,
        user_ordered_dishes: set[int],
        dish_similarity: dict[int, dict[int, float]],
        limit: int = 10
    ) -> dict[int, float]:
        """根据用户购买历史和物品相似度进行推荐

        Args:
            user_ordered_dishes: 用户已经购买过的菜品 ID 集合
            dish_similarity: 预计算的相似度矩阵
            limit: 返回推荐数量

        Returns:
            推荐得分字典 {dish_id: score}
        """
        logger.info("开始为用户生成协同过滤推荐...")

        if not user_ordered_dishes:
            logger.info("用户没有购买记录，无法进行协同过滤推荐。")
            return {}

        if not dish_similarity:
            logger.warning("无法获取菜品相似度矩阵，推荐失败。")
            return {}

        dish_scores: dict[int, float] = {}

        for purchased_dish in user_ordered_dishes:
            for related_dish, similarity_score in dish_similarity.get(purchased_dish, {}).items():
                if related_dish not in user_ordered_dishes:
                    dish_scores[related_dish] = dish_scores.get(related_dish, 0.0) + similarity_score

        recommended_dishes = sorted(
            dish_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )[:limit]

        logger.info(f"为用户生成了 {len(recommended_dishes)} 条推荐。")

        return {dish_id: round(score, 4) for dish_id, score in recommended_dishes}

    def recommend_by_item_similarity_with_time_decay(
        self,
        user_ordered_dishes: set[int],
        user_dish_time_map: dict[int, Any],
        dish_similarity: dict[int, dict[int, float]],
        limit: int = 10
    ) -> dict[int, float]:
        """使用时间衰减因子对菜品推荐进行加权优化

        Args:
            user_ordered_dishes: 用户已经购买过的菜品 ID 集合
            user_dish_time_map: {dish_id: first_purchase_time, ...}
            dish_similarity: 预计算的相似度矩阵
            limit: 返回推荐数量

        Returns:
            推荐得分字典 {dish_id: score}
        """
        logger.info("[时间衰减] 为用户生成推荐...")

        if not user_ordered_dishes:
            logger.info("用户无购买记录，跳过推荐。")
            return {}

        if not dish_similarity:
            logger.warning("菜品相似度矩阵为空，跳过推荐。")
            return {}

        if not user_dish_time_map:
            logger.warning("用户无有效购买时间数据，跳过推荐。")
            return {}

        t_first = min(user_dish_time_map.values())
        t_last = max(user_dish_time_map.values())
        dish_scores: dict[int, float] = {}

        for purchased_dish in user_ordered_dishes:
            purchase_time = user_dish_time_map.get(purchased_dish)
            if not purchase_time:
                continue
            time_weight = TimeDecayHelper.compute_exponential_decay(
                t_event=purchase_time,
                t_first=t_first,
                t_last=t_last,
                contribution=1.0
            )
            for related_dish, similarity_score in dish_similarity.get(purchased_dish, {}).items():
                if related_dish not in user_ordered_dishes:
                    dish_scores[related_dish] = dish_scores.get(related_dish, 0.0)
                    dish_scores[related_dish] += similarity_score * time_weight

        recommended_dishes = sorted(
            dish_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        logger.info(f"[时间衰减] 为用户推荐了 {len(recommended_dishes)} 道菜品。")

        return {dish_id: round(score, 4) for dish_id, score in recommended_dishes}

    @staticmethod
    def get_user_ordered_dishes_from_db(user_id: int) -> set[int]:
        """从数据库查询用户购买过的菜品（保留这个方法用于兼容，推荐在服务层查询）"""
        from sqlalchemy import text

        from app.utils.db import db

        try:
            query = text("""
                SELECT DISTINCT oi.dish_id
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.user_id = :user_id
            """)
            result = db.session.execute(query, {"user_id": user_id}).fetchall()
            return {row[0] for row in result}
        except Exception as e:
            logger.error(f"查询用户 {user_id} 购买记录时出错: {e}", exc_info=True)
            return set()

    @staticmethod
    def get_user_ordered_dishes_with_time_from_db(user_id: int) -> dict[int, Any]:
        """从数据库查询用户购买过的菜品及首次购买时间（保留这个方法用于兼容）"""
        from sqlalchemy import text

        from app.utils.db import db

        try:
            query = text("""
                SELECT oi.dish_id, MIN(o.created_at) AS first_purchase_time
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.user_id = :user_id
                GROUP BY oi.dish_id
            """)
            results = db.session.execute(query, {"user_id": user_id}).fetchall()
            return {row[0]: row[1] for row in results}
        except Exception as e:
            logger.error(f"查询用户 {user_id} 购买时间时出错: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_all_user_dish_matrix_from_db() -> dict[int, set[int]]:
        """从数据库查询所有用户-菜品购买关系，用于计算相似度（保留这个方法用于兼容）"""
        from sqlalchemy import text

        from app.utils.db import db

        try:
            query = text("""
                SELECT o.user_id, oi.dish_id
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
            """)
            results = db.session.execute(query).fetchall()
            logger.info(f"从数据库获取了 {len(results)} 条用户-菜品购买记录。")

            user_dish_matrix: dict[int, set[int]] = {}
            for row in results:
                user_id, dish_id = row
                user_dish_matrix.setdefault(user_id, set()).add(dish_id)

            return user_dish_matrix
        except Exception as e:
            logger.error(f"查询用户-购买关系时出错: {e}", exc_info=True)
            return {}
