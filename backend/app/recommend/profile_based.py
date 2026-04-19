"""
@File       : profile_based.py
@Date       : 2025-03-01 (Refactored: 2025-03-01)
@Description: 基于用户画像（如偏好菜系）的推荐算法。
              采用混合策略：优先用户显式设置，否则根据历史订单推断。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms
@Version    : 1.0.0
@Copyright  : Copyright © 2025. All rights reserved.
"""
import logging
from typing import cast

from sqlalchemy import desc, func, select

from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.utils.db import db

logger = logging.getLogger(__name__)


class ProfileRecommender:
    """基于用户画像（偏好菜系）推荐菜品，采用混合策略"""

    @staticmethod
    def _get_explicit_preference(user_id: int) -> str | None:
        """尝试获取用户明确设置的偏好菜系。"""
        if not hasattr(User, 'favorite_cuisine'):
            logger.error("User 模型缺少 'favorite_cuisine' 字段。")
            return None
        try:
            stmt = select(User.favorite_cuisine).where(User.user_id == user_id)
            preference = db.session.execute(stmt).scalar_one_or_none()

            if preference is not None:
                logger.debug(f"找到用户 {user_id} 的显式偏好: {preference}")
                # 确保返回的是字符串
                return cast(str, preference)
            return None
        except Exception as ex:
            logger.error(f"查询用户 {user_id} 显式偏好时出错: {ex}", exc_info=True)
            return None

    @staticmethod
    def _infer_preference_from_history(user_id: int) -> str | None:
        """根据用户历史订单推断最常点的菜系。"""
        logger.debug(f"尝试为用户 {user_id} 推断偏好菜系...")
        try:
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

            # 第 56 行附近：显式与 None 比较
            if top_category_row is not None:
                inferred_preference = cast(str, top_category_row.name)
                logger.debug(f"根据历史订单推断出用户 {user_id} 的偏好菜系: {inferred_preference}")
                return inferred_preference
            else:
                logger.debug(f"用户 {user_id} 没有足够的订单历史来推断偏好。")
                return None
        except Exception as ex:
            logger.error(f"根据用户 {user_id} 历史订单推断偏好时出错: {ex}", exc_info=True)
            return None

    def get_user_preference(self, user_id: int) -> str | None:
        """获取用户的最终偏好菜系 (混合策略)。"""
        preference = self._get_explicit_preference(user_id)
        if preference is not None:  # 显式比较
            logger.info(f"使用用户 {user_id} 的显式偏好菜系: {preference}")
            return preference
        else:
            inferred = self._infer_preference_from_history(user_id)
            if inferred is not None:  # 显式比较
                logger.info(f"使用用户 {user_id} 推断出的偏好菜系: {inferred}")
                return inferred
            else:
                logger.info(f"无法确定用户 {user_id} 的偏好菜系。")
                return None

    def recommend_by_profile(self, user_id: int, limit: int = 10) -> dict[int, float]:
        """
        根据用户的偏好菜系推荐菜品，返回归一化得分，用于融合推荐。
        返回格式：{dish_id: score}，score 为销量归一化权重（总和为 1）
        """
        user_preference = self.get_user_preference(user_id)

        if not user_preference:
            logger.info(f"无法获取用户 {user_id} 的偏好菜系，无法进行基于画像的推荐。")
            return {}

        if not hasattr(Dish, 'sales'):
            logger.error("Dish 模型缺少 'sales' 字段，无法按销量推荐。")
            return {}

        logger.info(f"为用户 {user_id} 根据偏好/推断菜系 '{user_preference}' 生成推荐...")
        try:
            stmt = (
                select(Dish.dish_id, Dish.sales)
                .join(Category, Dish.category_id == Category.category_id)
                .where(
                    Category.name == user_preference,
                    Dish.is_available.is_(True)
                )
                .order_by(Dish.sales.desc(), Dish.dish_id.asc())
                .limit(limit)
            )
            results = db.session.execute(stmt).fetchall()

            raw_scores = {cast(int, row[0]): float(row[1]) for row in results}
            total = sum(raw_scores.values()) or 1.0
            normalized = {dish_id: score / total for dish_id, score in raw_scores.items()}

            logger.info(f"为用户 {user_id} 生成了 {len(normalized)} 条基于画像的推荐（归一化得分）。")
            return normalized

        except Exception as ex:
            logger.error(f"根据用户 {user_id} 偏好 '{user_preference}' 推荐时出错: {ex}", exc_info=True)
            return {}
