"""
@File       : recommend_service.py
@Date       : 2025-03-01
@Description: 推荐服务，管理和路由不同的推荐策略。
              适配重构后的推荐器。
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import logging

from app.config import Config
from app.recommend.item_cf import ItemCFRecommender
from app.recommend.popular import PopularRecommender
from app.recommend.profile_based import ProfileRecommender

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    管理和统一不同推荐策略的服务。
    """

    def __init__(self):
        self.popular = PopularRecommender()
        self.collaborative = ItemCFRecommender()
        self.user_based = ProfileRecommender()
        logger.info("RecommendationService 初始化完成。")

    def _fuse_scores(self, user_id, limit, weights):
        from collections import defaultdict
        # profile-based scores
        usercf_scores = self.user_based.recommend_by_profile(user_id, limit)
        # collaborative filtering scores (item similarity)
        itemcf_scores = self.collaborative.recommend_by_item_similarity(user_id, limit)
        # popularity-based scores
        popular_scores = self.popular.get_normalized_popular_scores(limit)

        score_map = defaultdict(float)

        def accumulate_scores(score_dict, weight):
            """
            将 score_dict 中的得分累加到 score_map 中，权重为 weight
            """
            if not score_dict:
                return
            # score_dict should be a dict: dish_id -> score
            for dish_id, score in score_dict.items():
                score_map[dish_id] += weight * score

        accumulate_scores(usercf_scores, weights[0])
        accumulate_scores(itemcf_scores, weights[1])
        accumulate_scores(popular_scores, weights[2])

        sorted_dishes = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        return [dish_id for dish_id, _ in sorted_dishes[:limit]]

    def dish_ids_to_names(self, dish_ids):
        """
        根据 dish_ids 列表获取菜品名称列表。
        """
        from app.services.dish_service import get_dish_by_id
        result = []
        for dish_id in dish_ids:
            try:
                dish = get_dish_by_id(dish_id)
                result.append(dish)
            except Exception as e:
                logger.warning(f"推荐列表中菜品 {dish_id} 获取失败：{e}")
        return result

    # def dish_ids_to_names(self, dish_ids):

    def recommend(self, user_id, limit=None, strategy=None, weights=None):
        """
        推荐菜品给用户。
        :param user_id: 用户 ID
        :param limit: 推荐菜品数量
        :param strategy: 推荐策略，可选 popular、usercf、profile、auto
        :param weights: 融合策略的权重配置（仅 weighted 策略下使用）
        :return: 推荐菜品列表
        """
        if not limit:
            limit = Config.RECOMMEND_LIMIT_DEFAULT
        limit = min(limit, Config.RECOMMEND_LIMIT_MAX)

        if not strategy or strategy == 'auto':
            strategy = Config.RECOMMEND_STRATEGY_DEFAULT

        logger.info(f"推荐请求参数：user_id={user_id}, limit={limit}, strategy={strategy}")

        if strategy == 'popular':
            logger.info("策略指定为 popular，使用热门推荐。")
            score_dict = self.popular.get_normalized_popular_scores(limit)
            logger.debug(f"[popular] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'usercf':
            logger.info("策略指定为 usercf，使用协同过滤推荐。")
            score_dict = self.collaborative.recommend_by_item_similarity(user_id, limit)
            logger.debug(f"[usercf] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'profile':
            logger.info("策略指定为 profile，使用基于画像的冷启动推荐。")
            score_dict = self.user_based.recommend_by_profile(user_id, limit)
            logger.debug(f"[profile] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'profile_based':
            logger.info("策略指定为 profile_based，使用基于画像的冷启动推荐。")
            score_dict = self.user_based.recommend_by_profile(user_id, limit)
            logger.debug(f"[profile_based] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'item_cf_time':
            logger.info("策略指定为 item_cf_time，使用时间衰减协同过滤推荐。")
            score_dict = self.collaborative.recommend_by_item_similarity_with_time_decay(user_id,
                                                                                         limit)
            logger.debug(f"[item_cf_time] 推荐得分字典：{score_dict}")
            dish_ids = list(score_dict.keys())
            return self.dish_ids_to_names(dish_ids)

        elif strategy == 'weighted':
            logger.info("策略指定为 weighted，使用加权融合推荐策略。")
            weights = weights or [
                Config.RECOMMEND_WEIGHT_USER,
                0.0,  # 暂无单独 usercf 与 itemcf 区分时设置为 0
                Config.RECOMMEND_WEIGHT_POPULAR
            ]
            dish_ids = self._fuse_scores(user_id, limit, weights)
            logger.debug(f"[weighted] 推荐融合结果 dish_ids：{dish_ids}")
            return self.dish_ids_to_names(dish_ids)

        logger.info("未知策略或默认策略，使用配置中的默认融合推荐逻辑。")

        weights = [
            Config.RECOMMEND_WEIGHT_USER,
            0.0,  # 暂无单独 usercf 与 itemcf 区分时设置为 0
            Config.RECOMMEND_WEIGHT_POPULAR
        ]

        dish_ids = self._fuse_scores(user_id, limit, weights)
        logger.debug(f"[default-fallback] 推荐融合结果 dish_ids：{dish_ids}")
        return self.dish_ids_to_names(dish_ids)
