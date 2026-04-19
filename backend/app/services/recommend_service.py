"""
@File       : recommend_service.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01 (Refactored: 2026-04-19)
@Description: 推荐服务，管理和路由不同的推荐策略。重构：服务层负责数据访问，推荐器只负责算法计算，解耦DB依赖
"""

import logging

from sqlalchemy import text

from app.config import Config
from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.recommend.item_cf import ItemCFRecommender
from app.recommend.popular import PopularRecommender
from app.recommend.profile_based import ProfileRecommender
from app.utils.db import db

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    管理和统一不同推荐策略的服务。

    架构设计：
    - 本服务负责从数据库查询数据
    - 将数据传给推荐器进行计算
    - 推荐器只负责算法，不直接依赖 db
    - 支持多种推荐策略，支持加权融合
    """

    def __init__(self):
        self.popular = PopularRecommender()
        self.collaborative = ItemCFRecommender()
        self.user_based = ProfileRecommender()
        logger.info("RecommendationService 初始化完成。")

    def _fuse_scores(self, user_id, limit, weights):
        from collections import defaultdict

        usercf_scores = self._get_profile_scores(user_id, limit)
        itemcf_scores = self._get_itemcf_scores(user_id, limit)
        popular_scores = self._get_popular_scores(limit)

        score_map = defaultdict(float)

        def accumulate_scores(score_dict, weight):
            if not score_dict:
                return
            for dish_id, score in score_dict.items():
                score_map[dish_id] += weight * score

        accumulate_scores(usercf_scores, weights[0])
        accumulate_scores(itemcf_scores, weights[1])
        accumulate_scores(popular_scores, weights[2])

        sorted_dishes = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        return [dish_id for dish_id, _ in sorted_dishes[:limit]]

    def _get_popular_scores(self, limit):
        """从数据库查询热门菜品得分，传给推荐器计算"""
        try:
            query = text("""
                SELECT oi.dish_id, COUNT(oi.order_item_id) AS order_item_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                WHERE o.created_at >= DATETIME('now', '-30 days')
                GROUP BY oi.dish_id
                ORDER BY order_item_count DESC
                LIMIT :limit
            """)
            results = db.session.execute(query, {"limit": limit}).fetchall()
            raw_scores = {row[0]: float(row[1]) for row in results}
            return self.popular.get_normalized_popular_scores(raw_scores, limit)
        except Exception as ex:
            logger.error(f"[融合用] 获取热门菜品打分出错: {ex}", exc_info=True)
            return {}

    def _get_itemcf_scores(self, user_id, limit):
        """获取 ItemCF 推荐得分

        - 先从数据库查询用户-菜品矩阵
        - 再传给推荐器，推荐器从缓存拿或者重新计算相似度
        """
        user_ordered_dishes = self._get_user_ordered_dishes(user_id)
        if not user_ordered_dishes:
            return {}

        user_dish_matrix = self._get_all_user_dish_matrix()
        dish_similarity = self.collaborative.get_dish_similarity(user_dish_matrix)

        return self.collaborative.recommend_by_item_similarity(
            user_ordered_dishes,
            dish_similarity,
            limit
        )

    def _get_itemcf_scores_with_time_decay(self, user_id, limit):
        """带时间衰减的 ItemCF 推荐"""
        user_ordered_dishes = self._get_user_ordered_dishes(user_id)
        if not user_ordered_dishes:
            return {}

        user_dish_time_map = self._get_user_ordered_dishes_with_time(user_id)
        if not user_dish_time_map:
            return {}

        user_dish_matrix = self._get_all_user_dish_matrix()
        dish_similarity = self.collaborative.get_dish_similarity(user_dish_matrix)

        return self.collaborative.recommend_by_item_similarity_with_time_decay(
            user_ordered_dishes,
            user_dish_time_map,
            dish_similarity,
            limit
        )

    def _get_profile_scores(self, user_id, limit):
        """基于用户画像（偏好菜系）推荐得分

        - 查询用户偏好（显式或推断）
        - 查询符合偏好的可用菜品
        - 传给推荐器计算
        """
        user_preference = self._get_user_preference(user_id)
        if not user_preference:
            return {}

        available_dishes = self._get_available_dishes_by_category(user_preference)
        return self.user_based.recommend_by_profile(
            user_preference,
            available_dishes,
            limit
        )

    def _get_user_preference(self, user_id):
        """获取用户偏好菜系，先查显式，没有再推断"""
        from sqlalchemy import desc, func, select

        stmt = select(User.favorite_cuisine).where(User.user_id == user_id)
        preference = db.session.execute(stmt).scalar_one_or_none()

        if preference is not None:
            logger.debug(f"找到用户 {user_id} 的显式偏好: {preference}")
            return preference

        stmt = (
            select(Category.name, func.count(OrderItem.order_item_id).label('item_count'))
            .join(Order, Order.order_id == OrderItem.order_id)
            .join(Dish, Dish.dish_id == OrderItem.dish_id)
            .join(Category, Category.category_id == Dish.category_id)
            .where(Order.user_id == user_id)
            .group_by(Category.name)
            .order_by(desc('item_count'))
            .limit(1)
        )
        top_category_row = db.session.execute(stmt).first()

        if top_category_row is not None:
            inferred_preference = top_category_row.name
            logger.debug(f"根据历史订单推断出用户 {user_id} 的偏好菜系: {inferred_preference}")
            return inferred_preference

        logger.debug(f"用户 {user_id} 没有足够的订单历史来推断偏好")
        return None

    def _get_available_dishes_by_category(self, category_name):
        """查询指定分类下可用菜品，返回 (dish_id, sales)"""
        from sqlalchemy import select

        stmt = (
            select(Dish.dish_id, Dish.sales)
            .join(Category, Dish.category_id == Category.category_id)
            .where(
                Category.name == category_name,
                Dish.is_available.is_(True)
            )
            .order_by(Dish.sales.desc())
        )
        results = db.session.execute(stmt).fetchall()
        return [(row.dish_id, float(row.sales)) for row in results]

    def _get_user_ordered_dishes(self, user_id):
        """查询用户购买过的菜品 ID 集合"""
        query = text("""
            SELECT DISTINCT oi.dish_id
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.user_id = :user_id
        """)
        result = db.session.execute(query, {"user_id": user_id}).fetchall()
        return {row[0] for row in result}

    def _get_user_ordered_dishes_with_time(self, user_id):
        """查询用户购买过的菜品及首次购买时间"""
        query = text("""
            SELECT oi.dish_id, MIN(o.created_at) AS first_purchase_time
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.user_id = :user_id
            GROUP BY oi.dish_id
        """)
        results = db.session.execute(query, {"user_id": user_id}).fetchall()
        return {row[0]: row[1] for row in results}

    def _get_all_user_dish_matrix(self):
        """查询所有用户的购买记录，构建 user -> {dish_ids} 矩阵"""
        query = text("""
            SELECT o.user_id, oi.dish_id
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
        """)
        results = db.session.execute(query).fetchall()

        user_dish_matrix: dict[int, set[int]] = {}
        for row in results:
            user_id, dish_id = row
            user_dish_matrix.setdefault(user_id, set()).add(dish_id)

        return user_dish_matrix

    def dish_ids_to_names(self, dish_ids):
        """根据 dish_ids 列表获取完整菜品信息"""
        from app.services.dish_service import get_dish_by_id

        result = []
        for dish_id in dish_ids:
            try:
                dish = get_dish_by_id(dish_id)
                result.append(dish)
            except Exception as e:
                logger.warning(f"推荐列表中菜品 {dish_id} 获取失败：{e}")
        return result

    def refresh_itemcf_similarity(self):
        """强制刷新 ItemCF 相似度缓存

        可以在后台定时任务或管理接口调用，更新推荐模型。
        """
        user_dish_matrix = self._get_all_user_dish_matrix()
        return self.collaborative.refresh_similarity(user_dish_matrix)

    def recommend(self, user_id, limit=None, strategy=None, weights=None):
        """
        推荐菜品给用户。
        :param user_id: 用户 ID
        :param limit: 推荐菜品数量
        :param strategy: 推荐策略，可选 popular、usercf、profile、auto
        :param weights: 融合策略的权重配置（仅 weighted 策略下使用）
        :return: 推荐菜品列表（完整对象）
        """
        if not limit:
            limit = Config.RECOMMEND_LIMIT_DEFAULT
        limit = min(limit, Config.RECOMMEND_LIMIT_MAX)

        if not strategy or strategy == 'auto':
            strategy = Config.RECOMMEND_STRATEGY_DEFAULT

        logger.info(f"推荐请求参数：user_id={user_id}, limit={limit}, strategy={strategy}")

        if strategy == 'popular':
            logger.info("策略指定为 popular，使用热门推荐。")
            score_dict = self._get_popular_scores(limit)
            logger.debug(f"[popular] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'usercf':
            logger.info("策略指定为 usercf，使用物品协同过滤推荐。")
            score_dict = self._get_itemcf_scores(user_id, limit)
            logger.debug(f"[usercf] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy in ('profile', 'profile_based'):
            logger.info("策略指定为 profile，使用基于画像的冷启动推荐。")
            score_dict = self._get_profile_scores(user_id, limit)
            logger.debug(f"[profile] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'item_cf_time':
            logger.info("策略指定为 item_cf_time，使用时间衰减协同过滤推荐。")
            score_dict = self._get_itemcf_scores_with_time_decay(user_id, limit)
            logger.debug(f"[item_cf_time] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'weighted':
            logger.info("策略指定为 weighted，使用加权融合推荐策略。")
            weights = weights or [
                Config.RECOMMEND_WEIGHT_USER,
                0.0,
                Config.RECOMMEND_WEIGHT_POPULAR
            ]
            dish_ids = self._fuse_scores(user_id, limit, weights)
            logger.debug(f"[weighted] 推荐融合结果 dish_ids：{dish_ids}")
            return self.dish_ids_to_names(dish_ids)

        logger.info("未知策略或默认策略，使用配置中的默认融合推荐逻辑。")

        weights = [
            Config.RECOMMEND_WEIGHT_USER,
            0.0,
            Config.RECOMMEND_WEIGHT_POPULAR
        ]

        dish_ids = self._fuse_scores(user_id, limit, weights)
        logger.debug(f"[default-fallback] 推荐融合结果 dish_ids：{dish_ids}")
        return self.dish_ids_to_names(dish_ids)
