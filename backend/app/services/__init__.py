"""
@File       : __init__.py
@Author     : taichilei
@Date       : 2025-04-29
@Description: services 包初始化 - 导出业务逻辑服务
"""

from .auth_service import (
    authenticate_user,
    refresh_token,
    register_user,
)
from .category_service import (
    create_category,
    delete_category,
    get_category_by_id,
    list_categories,
    update_category,
)
from .chart_service import (
    get_daily_revenue,
    get_order_status_stats,
    get_top_dishes,
    get_user_growth,
)
from .chat_service import (
    ask_ai,
    create_chat,
    get_chat_history,
)
from .dining_area_service import (
    assign_user_to_area,
    create_dining_area,
    delete_dining_area,
    get_dining_area_by_id,
    list_dining_areas,
    release_area,
    update_dining_area,
)
from .dish_service import (
    create_dish,
    delete_dish,
    get_dish_by_id,
    list_dishes,
    set_dish_availability,
    update_dish,
)
from .order_service import (
    create_order,
    get_order_by_id,
    list_all_orders,
    list_orders_by_user,
    update_order_status,
)
from .recommend_service import RecommendationService
from .staff_service import (
    create_staff,
    delete_staff,
    list_staff,
    update_staff,
)
from .tag_service import (
    create_tag,
    delete_tag,
    get_tag_by_id,
    list_tags,
    update_tag,
)
from .user_service import (
    admin_update_user,
    ban_user,
    delete_user,
    get_user_by_account,
    get_user_by_id,
    list_users,
    update_user_profile,
)

__all__ = [
    "authenticate_user",
    "register_user",
    "refresh_token",
    "get_user_by_id",
    "get_user_by_account",
    "list_users",
    "update_user_profile",
    "admin_update_user",
    "delete_user",
    "ban_user",
    "get_dish_by_id",
    "list_dishes",
    "create_dish",
    "update_dish",
    "delete_dish",
    "set_dish_availability",
    "create_order",
    "get_order_by_id",
    "list_orders_by_user",
    "list_all_orders",
    "update_order_status",
    "get_category_by_id",
    "list_categories",
    "create_category",
    "update_category",
    "delete_category",
    "get_tag_by_id",
    "list_tags",
    "create_tag",
    "update_tag",
    "delete_tag",
    "get_dining_area_by_id",
    "list_dining_areas",
    "create_dining_area",
    "update_dining_area",
    "delete_dining_area",
    "assign_user_to_area",
    "release_area",
    "RecommendationService",
    "create_chat",
    "get_chat_history",
    "ask_ai",
    "get_daily_revenue",
    "get_top_dishes",
    "get_order_status_stats",
    "get_user_growth",
    "list_staff",
    "create_staff",
    "update_staff",
    "delete_staff",
]
