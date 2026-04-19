"""
@File       : context_provider.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 为 AI 聊天提供不同角色的上下文提供者，加载系统提示词信息
"""
def load_user_context() -> str:
    """
    加载针对普通用户的上下文信息。
    包含菜品、餐厅介绍、时令蔬菜推荐等信息，用于生成 prompt。

    Returns:
        str: 拼接好的上下文信息字符串
    """
    # 这里可以从数据库、配置文件或静态数据加载信息
    # 以下为示例静态数据
    dishes = ["麻婆豆腐", "鱼香肉丝", "宫保鸡丁", "回锅肉"]
    restaurant_intro = "欢迎光临我们的餐厅，环境优雅，服务周到。"
    seasonal_recommendation = "时令推荐：鲜嫩的春笋炒肉。"

    # 针对用户的上下文，拼接所有信息
    context = f"餐厅介绍：{restaurant_intro}\n菜品：{', '.join(dishes)}\n时令推荐：{seasonal_recommendation}"
    return context


def load_admin_context() -> str:
    """
    加载针对管理员的上下文信息。
    管理员可能需要看到更多数据、统计信息或者后台描述，生成的 prompt 信息可以更详细。

    Returns:
        str: 拼接好的上下文信息字符串
    """
    # 示例数据，可根据实际需求调整
    dishes = ["麻婆豆腐", "鱼香肉丝", "宫保鸡丁", "回锅肉"]
    restaurant_intro = "本餐厅成立于2010年，曾获多项美食大奖。"
    seasonal_recommendation = "本季时令蔬菜供应：有机菠菜、鲜香小白菜。"
    inventory_info = "库存：各菜品库存充足，暂无缺货风险。"

    # 针对管理员的上下文信息更全面
    context = (
        f"餐厅介绍：{restaurant_intro}\n"
        f"菜品信息：{', '.join(dishes)}\n"
        f"时令推荐：{seasonal_recommendation}\n"
        f"库存信息：{inventory_info}"
    )
    return context
