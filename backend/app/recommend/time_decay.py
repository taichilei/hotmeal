"""
@file         app/recommend/time_decay.py
@description  （这里写这个模块/脚本的功能简述）
@date         2025-05-18
@author       taichilei
"""

import datetime
import math


class TimeDecayHelper:
    """
    提供推荐系统中常用的时间衰减与贡献度函数，包括：
    - 指数衰减（适用于时间敏感推荐）
    - Sigmoid 贡献度函数（用于用户间评分可信度）
    - 线性衰减（适用于简化模型或对时间线性敏感的场景）
    """
    @staticmethod
    def compute_exponential_decay(t_event, t_first, t_last, contribution=1.0):
        """
        计算时间衰减因子 δ，遵循指数衰减公式：
        δ = e ^ ( -contribution × ((t_event - t_first) / (t_last - t_first)) )

        :param t_event: 当前评分或行为发生时间（datetime 或时间戳）
        :param t_first: 用户最早行为时间（datetime 或时间戳）
        :param t_last: 用户最晚行为时间（datetime 或时间戳）
        :param contribution: 贡献度因子（默认1.0，结合用户相似度使用）
        :return: 时间权重值，范围 (1/e, 1]
        """
        try:
            if isinstance(t_event, datetime.datetime):
                t_event = t_event.timestamp()
                t_first = t_first.timestamp()
                t_last = t_last.timestamp()
            if t_last == t_first:
                return 1.0
            ratio = (t_event - t_first) / (t_last - t_first)
            return math.exp(-contribution * ratio)
        except Exception:
            return 1.0  # 容错处理：无法计算时使用最大权重

    @staticmethod
    def compute_sigmoid_contribution(c_ab, theta=3):
        """
        计算用户 b 对用户 a 的贡献度 sup(a,b)，用于可信评分权重。

        :param c_ab: 用户 a 与 b 的评分共现次数
        :param theta: 贡献可信阈值（默认3），小于阈值时贡献快速衰减
        :return: 贡献度值，范围 (0, 1)
        """
        return 1 / (1 + math.exp(-(c_ab - theta)))

    @staticmethod
    def compute_linear_decay(t_event, t_now, half_life_days=30):
        """
        计算线性时间衰减因子，按时间距离当前时间线性降低。

        :param t_event: 行为发生时间（datetime 或时间戳）
        :param t_now: 当前时间（datetime 或时间戳）
        :param half_life_days: 半衰期（默认30天内线性降至0）
        :return: 权重值，范围 [0, 1]
        """
        try:
            if isinstance(t_event, datetime.datetime):
                t_event = t_event.timestamp()
                t_now = t_now.timestamp()
            delta_days = (t_now - t_event) / 86400  # 秒转天
            decay = max(0.0, 1 - delta_days / half_life_days)
            return decay
        except Exception:
            return 1.0
