"""
@File       : order_service.py
@Author     : ChiLei Tai JOU
@Date       : 2025-05-05
@Description: 订单服务层，处理订单的创建、查询、更新、取消和删除逻辑，采用 "失败抛异常，成功返数据"模式
"""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app.models import DiningArea, Dish, Order, OrderItem, User
from app.models.enums import OrderState, PaymentMethod, UserRole
from app.utils.db import db
from app.utils.error_codes import ErrorCode
from app.utils.exceptions import (
    APIException,
    AuthorizationError,
    BusinessError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# --- 辅助函数 ---
def _serialize_order(order: Order, include_items: bool = True) -> dict[str, Any]:
    """序列化 Order 对象。"""
    if not isinstance(order, Order):
        logger.error(f"尝试序列化非 Order 对象: {type(order)}")
        return {}
    # null 检查，避免 user 或 dining_area 为 None 时抛异常
    if include_items and not hasattr(order, "order_items"):
        logger.warning(f"订单 {order.order_id} 缺少订单项字段 'order_items'，无法展开。")
    return {
        "order_id": order.order_id,
        "user": {
            "user_id": order.user.user_id,
            "username": order.user.username
        } if order.user else None,
        "area": {
            "area_id": order.dining_area.area_id,
            "area_name": order.dining_area.area_name
        } if order.dining_area else None,
        "state": order.state.name,
        "price": float(order.price),
        "payment_method": order.payment_method.name if order.payment_method else None,
        "image_url": order.image_url,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "deleted_at": order.deleted_at.isoformat() if order.deleted_at else None,
        "items": [item.to_dict() for item in
                  getattr(order, "order_items", [])] if include_items and hasattr(order,
                                                                                  "order_items") else []
    }


# --- 创建订单 ---
def create_order(user_id: int,
                 dish_list: list[dict[str, Any]],
                 area_id: int | None) -> dict[str, Any]:
    """
    创建新订单并添加菜品信息。

    Args:
        user_id: 用户 ID。
        dish_list: 包含 'dish_id' 和 'quantity' 的字典列表。
        area_id: 用餐区域 ID (可选)。

    Returns:
        成功时返回新创建订单的信息字典 (包含订单项)。

    Raises:
        NotFoundError: 如果用户、区域或某个菜品未找到。
        ValidationError: 如果 dish_list 为空或 quantity 无效。
        BusinessError: 如果菜品不可用或库存不足。
        APIException: 如果发生数据库错误。
    """
    # 1. 输入验证
    if not dish_list:
        raise BusinessError("订单中的菜品列表不能为空。", error_code=ErrorCode.PARAM_INVALID.value)

    # 检查用户和区域是否存在
    if not User.query.get(user_id):
        raise NotFoundError(f"用户 ID {user_id} 不存在。", error_code=ErrorCode.USER_NOT_FOUND.value)
    if area_id is not None and not DiningArea.query.get(area_id):
        raise NotFoundError(f"用餐区域 ID {area_id} 不存在。",
                            error_code=ErrorCode.HTTP_NOT_FOUND.value)  # 需要定义 AREA_NOT_FOUND

    # 2. 检查菜品并计算初始价格 (在一个事务中完成)
    try:
        items_to_create = []
        dishes_to_update_stock = {}  # 存储需要更新库存的菜品及其减少量

        for item_data in dish_list:
            dish_id = item_data.get('dish_id')
            quantity = item_data.get('quantity')

            if not isinstance(dish_id, int) or not isinstance(quantity, int):
                raise ValidationError(
                    f"菜品列表项必须包含有效的 dish_id (整数) 和 quantity (整数)。无效项: {item_data}",
                    error_code=ErrorCode.PARAM_INVALID.value)
            if quantity <= 0:
                raise ValidationError(f"菜品 ID {dish_id} 的数量必须大于 0。",
                                      error_code=ErrorCode.PARAM_INVALID.value)

            dish = Dish.query.get(dish_id)
            if not dish:
                raise BusinessError(f"菜品 ID {dish_id} 未找到。",
                                    error_code=ErrorCode.DISH_NOT_FOUND.value)
            if not dish.is_available:
                raise BusinessError(f"菜品 '{dish.name}' 当前不可用。",
                                    error_code=ErrorCode.DISH_UNAVAILABLE.value)
            if dish.stock < quantity:
                raise BusinessError(
                    f"菜品 '{dish.name}' 库存不足 (需要 {quantity}, 仅剩 {dish.stock})。",
                    error_code=ErrorCode.INSUFFICIENT_STOCK.value)

            # 准备 OrderItem 数据 (使用 Decimal 价格)
            items_to_create.append({
                "dish_id": dish.dish_id,
                "quantity": quantity,
                "unit_price": dish.price  # 从 Dish 模型获取 Decimal 价格
            })
            # 记录库存扣减量
            dishes_to_update_stock[dish] = dishes_to_update_stock.get(dish, 0) + quantity

        # 3. 创建 Order 和 OrderItem，并更新库存 (在同一个事务中)
        # 计算初始总价 (Decimal)
        total_price = sum(item['unit_price'] * item['quantity'] for item in items_to_create)

        order = Order(
            user_id=user_id,
            area_id=area_id,
            state=OrderState.PENDING,
            price=total_price  # 设置计算好的 Decimal 总价
            # created_at 和 updated_at 由数据库默认值或 onupdate 处理
        )
        db.session.add(order)
        db.session.flush()  # 需要先 flush 获取 order.order_id

        order_item_objects = []
        for item_data in items_to_create:
            order_item = OrderItem(
                order_id=order.order_id,  # 使用 flush 后获取的 ID
                dish_id=item_data['dish_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']  # 使用 Decimal
            )
            order_item_objects.append(order_item)
        db.session.add_all(order_item_objects)

        # 扣减库存
        for dish, quantity_to_reduce in dishes_to_update_stock.items():
            # 再次检查库存避免并发问题（或者使用数据库锁）
            # if dish.stock < quantity_to_reduce: # 在循环外统一检查可能更好
            #     raise BusinessError(...)
            dish.stock -= quantity_to_reduce
            logger.info(
                f"菜品 '{dish.name}' (ID: {dish.dish_id}) 库存扣减 {quantity_to_reduce}，剩余 {dish.stock}。")

        # 提交整个事务
        db.session.commit()

        logger.info(f"订单 (ID: {order.order_id}) 创建成功，总价: {order.price:.2f}。")
        # 返回序列化后的订单信息 (包含订单项)
        # 需要重新加载 order_items，因为它们是在 commit 后才完全关联的
        # 或者直接构建返回字典
        return _serialize_order(order, include_items=True)  # 尝试序列化

    except (NotFoundError, ValidationError, BusinessError) as e:
        db.session.rollback()  # 业务逻辑错误也需要回滚
        logger.warning(f"创建订单失败 ({type(e).__name__}): {e}")
        raise e  # 重新抛出，让全局处理器处理
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"创建订单时发生数据库错误: {e}", exc_info=True)
        raise APIException("创建订单失败，数据库错误。", error_code=ErrorCode.DATABASE_ERROR.value)
    except Exception as e:  # 捕获其他意外错误
        db.session.rollback()
        logger.error(f"创建订单时发生未知错误: {e}", exc_info=True)
        raise APIException("创建订单时发生未知错误。",
                           error_code=ErrorCode.INTERNAL_SERVER_ERROR.value)


# --- 查询订单 ---
def get_order_by_id(order_id: int, include_items: bool = True) -> dict[str, Any]:
    """
    根据订单 ID 获取订单信息，可选是否包含订单项。

    Args:
        order_id: 订单 ID。
        include_items: 是否包含订单项详情。

    Returns:
        包含订单信息的字典。

    Raises:
        NotFoundError: 如果订单未找到。
    """
    query = Order.query
    if include_items:
        # 预加载订单项及其关联的菜品信息
        query = query.options(selectinload(Order.order_items).joinedload(OrderItem.dish))
    # 预加载用户信息和区域信息（如果序列化需要）
    query = query.options(joinedload(Order.user), joinedload(Order.dining_area))

    order = query.get(order_id)
    if not order:
        logger.warning(f"尝试获取不存在的订单: order_id={order_id}")
        raise NotFoundError(f"ID 为 {order_id} 的订单未找到。",
                            error_code=ErrorCode.ORDER_NOT_FOUND.value)

    logger.info(f"成功检索到订单: ID={order_id}")
    return _serialize_order(order, include_items=include_items)


def get_orders_by_user(user_id: int, include_items: bool = False) -> list[dict[str, Any]]:
    """
    获取指定用户的所有订单列表，可选是否包含订单项。

    Args:
        user_id: 用户 ID。
        include_items: 是否包含每个订单的订单项详情。

    Returns:
        包含订单信息字典的列表。

    Raises:
        NotFoundError: 如果用户不存在。
        APIException: 如果发生数据库错误。
    """
    # 检查用户是否存在
    if not User.query.get(user_id):
        raise NotFoundError(f"用户 ID {user_id} 不存在。", error_code=ErrorCode.USER_NOT_FOUND.value)

    try:
        query = Order.query.filter_by(user_id=user_id)
        if include_items:
            query = query.options(selectinload(Order.order_items).joinedload(OrderItem.dish))
        # 按创建时间降序排列
        orders = query.order_by(Order.created_at.desc()).all()

        order_list = [_serialize_order(order, include_items=include_items) for order in orders]
        logger.info(f"成功检索到用户 {user_id} 的 {len(order_list)} 个订单。")
        return order_list
    except SQLAlchemyError as e:
        logger.error(f"获取用户 {user_id} 订单列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取用户订单列表失败。", error_code=ErrorCode.DATABASE_ERROR.value)


def list_all_orders(page: int = 1,
                    per_page: int = 10,
                    include_items: bool = False) -> dict[str, Any]:
    """
    获取所有订单的分页列表 (通常用于管理后台)，可选包含订单项。

    Args:
        page: 页码 (从 1 开始)。
        per_page: 每页数量。
        include_items: 是否包含订单项。

    Returns:
        包含订单列表和分页信息的字典:
        {
            "items": [...],
            "page": int,
            "per_page": int,
            "total_items": int,
            "total_pages": int
        }

    Raises:
        APIException: 如果发生数据库错误。
    """
    logger.debug(f"调用 list_all_orders: page={page}, per_page={per_page}, include_items={include_items}")
    try:
        query = Order.query
        if include_items:
            query = query.options(selectinload(Order.order_items).joinedload(OrderItem.dish))
        # 预加载用户信息和区域信息
        query = query.options(joinedload(Order.user), joinedload(Order.dining_area))

        # 添加排序，例如按创建时间降序
        query = query.order_by(Order.created_at.desc())

        # 使用 paginate 进行分页
        pagination = query.paginate(page=page, per_page=per_page,
                                    error_out=False)  # error_out=False 避免页码超出范围时抛异常
        logger.debug(f"分页结果: 当前页={page}, 每页={per_page}, 总数={pagination.total}, 总页数={pagination.pages}")

        orders_data = [_serialize_order(order, include_items=include_items) for order in
                       pagination.items]
        logger.debug(f"序列化订单数量: {len(orders_data)}")

        result = {
            "items": orders_data,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages
        }
        logger.info(f"成功检索订单列表: 第 {page}/{pagination.pages} 页，共 {pagination.total} 条。")
        return result
    except SQLAlchemyError as e:
        logger.error(f"获取订单分页列表时发生数据库错误: {e}", exc_info=True)
        raise APIException("获取订单列表失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 更新订单 ---
def update_order_details(order_id: int, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    更新订单的详细信息 (例如状态、支付方式、凭证 URL)。

    Args:
        order_id: 要更新的订单 ID。
        update_data: 包含待更新字段和值的字典。允许字段: 'state', 'payment_method', 'image_url'。

    Returns:
        成功时返回更新后的订单信息字典。

    Raises:
        NotFoundError: 如果订单未找到。
        ValidationError: 如果状态或支付方式无效，或 URL 格式错误。
        BusinessError: 如果状态转换无效。
        APIException: 如果发生数据库错误。
    """
    order = Order.query.get(order_id)
    if not order:
        raise NotFoundError(f"ID 为 {order_id} 的订单未找到。",
                            error_code=ErrorCode.ORDER_NOT_FOUND.value)

    # 不允许修改已删除的订单
    if order.deleted_at is not None:
        raise BusinessError("不能修改已删除的订单。", error_code=ErrorCode.HTTP_CONFLICT.value)

    updated = False
    processed_data = {k: v for k, v in update_data.items() if v is not None}  # 忽略 None

    allowed_fields = ['state', 'payment_method', 'image_url']

    try:
        for key, value in processed_data.items():
            if key not in allowed_fields:
                logger.warning(f"尝试更新订单 {order_id} 不支持的字段: {key}")
                continue

            current_value = getattr(order, key)

            if key == 'state':
                try:
                    new_state = OrderState(value)  # 尝试从值创建枚举
                    # 检查状态转换是否有效 (业务逻辑)
                    # 例如：不能从 COMPLETED 或 CANCELED 变回 PENDING 或 PAID
                    if order.state in [OrderState.COMPLETED,
                                       OrderState.CANCELED] and new_state != order.state:
                        raise BusinessError(
                            f"不能将状态从 {order.state.name} 更改为 {new_state.name}。",
                            error_code=ErrorCode.ORDER_STATE_INVALID.value)
                    # 例如：只能从 PENDING 变为 PAID 或 CANCELED (这个逻辑在模型的 can_be_canceled 和 mark_as_canceled 中有部分体现)
                    if order.state == OrderState.PENDING and new_state not in [OrderState.PAID,
                                                                               OrderState.CANCELED,
                                                                               OrderState.PENDING]:
                        raise BusinessError(f"不能将状态从 PENDING 直接更改为 {new_state.name}。",
                                            error_code=ErrorCode.ORDER_STATE_INVALID.value)

                    if current_value != new_state:
                        order.state = new_state
                        updated = True
                except ValueError:  # 无效的枚举值
                    raise ValidationError(f"无效的订单状态值: {value}",
                                          error_code=ErrorCode.PARAM_INVALID.value)
            elif key == 'payment_method':
                try:
                    new_payment_method = PaymentMethod(value) if value else None
                    if current_value != new_payment_method:
                        order.payment_method = new_payment_method
                        updated = True
                except ValueError:
                    raise ValidationError(f"无效的支付方式值: {value}",
                                          error_code=ErrorCode.PARAM_INVALID.value)
            elif key == 'image_url':
                # 模型的 @validates 会检查格式和长度
                if current_value != value:
                    order.image_url = value  # 触发验证
                    updated = True

            if updated:
                logger.debug(f"Order {order_id} field '{key}' will be updated to {value}")

    except ValueError as ve:  # 捕获模型 @validates 的错误
        db.session.rollback()
        raise ValidationError(f"更新订单时数据验证失败: {ve}",
                              error_code=ErrorCode.PARAM_INVALID.value)

    if not updated:
        logger.info(f"没有为订单 {order_id} 提供需要更新的信息。")
        return _serialize_order(order)

    try:
        # updated_at 由 onupdate 自动处理
        db.session.commit()
        logger.info(f"订单 {order_id} 信息更新成功。")
        return _serialize_order(order)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新订单 {order_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("更新订单信息失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 更新订单项数量 ---
def update_order_item_quantity(order_id: int, order_item_id: int, quantity: int,
                               operator_id: int) -> dict[str, Any]:
    """
    更新订单中某个订单项的数量，并重新计算订单总价。

    Args:
        order_id: 订单 ID。
        order_item_id: 要更新的订单项 ID。
        quantity: 新数量，必须为正整数。
        operator_id: 发起更新的用户 ID。

    Returns:
        更新后的订单信息字典。

    Raises:
        ValidationError: 数量无效。
        NotFoundError: 订单或订单项或菜品未找到。
        BusinessError: 状态不允许修改，或库存不足。
        AuthorizationError: 用户无权操作该订单。
        APIException: 数据库错误。
    """
    if quantity <= 0:
        raise BusinessError("数量必须大于 0。", error_code=ErrorCode.PARAM_INVALID.value)

    try:
        order = Order.query.options(selectinload(Order.order_items)).get(order_id)
        if not order:
            raise NotFoundError(f"订单 ID {order_id} 未找到。",
                                error_code=ErrorCode.ORDER_NOT_FOUND.value)

        if order.user_id != operator_id:
            raise AuthorizationError("无权修改该订单。", error_code=ErrorCode.FORBIDDEN.value)

        if order.state != OrderState.PENDING:
            raise BusinessError("仅允许修改待处理状态的订单项。",
                                error_code=ErrorCode.ORDER_STATE_INVALID.value)

        item = next((i for i in order.order_items if i.order_item_id == order_item_id), None)
        if not item:
            raise NotFoundError(f"订单项 ID {order_item_id} 不存在。",
                                error_code=ErrorCode.ORDER_ITEM_NOT_FOUND.value)

        dish = Dish.query.get(item.dish_id)
        if not dish:
            raise NotFoundError(f"菜品 ID {item.dish_id} 不存在。",
                                error_code=ErrorCode.DISH_NOT_FOUND.value)

        diff = quantity - item.quantity
        if diff > 0 and dish.stock < diff:
            raise BusinessError(f"库存不足，剩余 {dish.stock}，需要增加 {diff}。",
                                error_code=ErrorCode.INSUFFICIENT_STOCK.value)

        item.quantity = quantity
        dish.stock -= diff
        order.price = order.calculate_total_price()

        db.session.commit()
        logger.info(f"更新订单项成功，订单 {order_id}，项 {order_item_id}，新数量 {quantity}。")
        return _serialize_order(order)

    except (NotFoundError, ValidationError, BusinessError, AuthorizationError) as e:
        db.session.rollback()
        raise e
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"更新订单项数量失败: {e}", exc_info=True)
        raise APIException("更新订单项数量失败。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 取消订单 ---
def cancel_order(order_id: int, operator_id: int, operator_role: str) -> bool:
    """
    取消一个处于 PENDING 状态的订单，并恢复菜品库存。

    Args:
        order_id: 要取消的订单 ID。
        operator_id: 执行操作的用户 ID。
        operator_role: 执行操作的用户角色 ('admin', 'staff', 'user')。

    Returns:
        True 表示成功取消。

    Raises:
        NotFoundError: 如果订单未找到或订单项中的菜品未找到。
        AuthorizationError: 如果用户无权取消此订单。
        BusinessError: 如果订单状态不允许取消。
        APIException: 如果发生数据库错误。
    """
    # 预加载订单项和关联的菜品以更新库存
    order = Order.query.options(
        selectinload(Order.order_items).joinedload(OrderItem.dish)
    ).get(order_id)

    if not order:
        raise NotFoundError(f"ID 为 {order_id} 的订单未找到。",
                            error_code=ErrorCode.ORDER_NOT_FOUND.value)

    # 检查权限
    is_admin_or_staff = operator_role.upper() in [UserRole.ADMIN.name, UserRole.STAFF.name]
    is_owner = order.user_id == operator_id
    if not (is_admin_or_staff or is_owner):
        logger.warning(
            f"用户 {operator_id} (角色: {operator_role}) 尝试取消不属于自己的订单 {order_id}。")
        raise AuthorizationError("无权取消此订单。", error_code=ErrorCode.UNAUTHORIZED.value)

    # 检查订单状态是否允许取消 (确保 order.can_be_canceled() 对于非 PENDING 状态返回 False)
    if not order.can_be_canceled():  # 使用模型的方法检查状态
        logger.warning(f"尝试取消状态为 {order.state.name} 的订单 {order_id}。")
        raise BusinessError(f"订单当前状态为 '{order.state.name}'，无法取消。",
                            error_code=ErrorCode.ORDER_STATE_INVALID.value)

    try:
        # 恢复库存
        for item in order.order_items:
            # 这里的 item.dish 应该已经被预加载了
            if item.dish:
                item.dish.stock += item.quantity
                logger.info(
                    f"恢复菜品 '{item.dish.name}' (ID: {item.dish.dish_id}) 库存 {item.quantity}，剩余 {item.dish.stock}。")
            else:
                # 理论上不应发生，因为创建订单时检查了菜品存在性
                logger.error(
                    f"取消订单 {order_id} 时，订单项 {item.order_item_id} 关联的菜品 ID {item.dish_id} 未找到！")
                # 决定是继续取消还是抛异常？这里选择抛异常保证数据一致性
                raise NotFoundError(f"订单项关联的菜品 ID {item.dish_id} 未找到。",
                                    error_code=ErrorCode.DISH_NOT_FOUND.value)

        # 标记订单为取消状态
        order.mark_as_canceled()  # 调用模型方法标记状态

        # 提交事务
        db.session.commit()
        logger.info(f"订单 {order_id} 已成功取消。")
        return True

    except (NotFoundError, BusinessError, AuthorizationError) as e:
        db.session.rollback()  # 业务或权限错误也需回滚库存更改
        logger.warning(f"取消订单 {order_id} 失败 ({type(e).__name__}): {e}")
        raise e
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"取消订单 {order_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("取消订单失败，数据库错误。", error_code=ErrorCode.DATABASE_ERROR.value)


# --- 删除订单 ---
def delete_order_soft(order_id: int, operator_id: int, operator_role: str) -> bool:
    """
    软删除订单 (设置 deleted_at 标记)。

    Args:
        order_id: 要软删除的订单 ID。
        operator_id: 执行操作的用户 ID。
        operator_role: 执行操作的用户角色。

    Returns:
        True 表示Operation succeeded。

    Raises:
        NotFoundError: 如果订单未找到。
        AuthorizationError: 如果用户无权删除此订单。
        APIException: 如果发生数据库错误。
    """
    order = Order.query.get(order_id)
    if not order:
        raise NotFoundError(f"ID 为 {order_id} 的订单未找到。",
                            error_code=ErrorCode.ORDER_NOT_FOUND.value)

    # 权限检查 (仅管理员/员工或订单所有者可软删除)
    is_admin_or_staff = operator_role.upper() in [UserRole.ADMIN.name, UserRole.STAFF.name]
    is_owner = order.user_id == operator_id
    if not (is_admin_or_staff or is_owner):
        logger.warning(
            f"用户 {operator_id} (角色: {operator_role}) 尝试软删除不属于自己的订单 {order_id}。")
        raise AuthorizationError("无权删除此订单。", error_code=ErrorCode.FORBIDDEN.value)

    if order.deleted_at is not None:
        logger.info(f"订单 {order_id} 已处于软删除状态，无需操作。")
        return True  # 幂等性

    try:
        order.mark_as_deleted()  # 调用模型方法标记
        db.session.commit()
        logger.info(f"订单 {order_id} 已被软删除。")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"软删除订单 {order_id} 时发生数据库错误: {e}", exc_info=True)
        raise APIException("软删除订单失败。", error_code=ErrorCode.DATABASE_ERROR.value)


def delete_order_hard(order_id: int) -> bool:
    """
    永久删除订单及其关联的订单项 (硬删除, 通常仅管理员)。

    Args:
        order_id: 要永久删除的订单 ID。

    Returns:
        True 表示成功删除。

    Raises:
        NotFoundError: 如果订单未找到。
        APIException: 如果发生数据库错误。
    """
    # 注意：硬删除通常非常危险，确保操作者有足够权限（这应该在路由层检查）
    order = Order.query.get(order_id)
    if not order:
        raise NotFoundError(f"ID 为 {order_id} 的订单未找到。",
                            error_code=ErrorCode.ORDER_NOT_FOUND.value)

    try:
        # 由于 OrderItem 设置了 cascade="all, delete-orphan"，
        # 删除 Order 时会自动删除关联的 OrderItem
        order_id_copy = order.order_id
        user_id_copy = order.user_id
        db.session.delete(order)
        db.session.commit()
        logger.info(f"订单 {order_id_copy} (用户 ID: {user_id_copy}) 及其订单项已被永久删除。")
        return True
    except SQLAlchemyError as e:  # 捕获可能的约束或其他错误
        db.session.rollback()
        logger.error(f"永久删除订单 {order_id} 时发生数据库错误: {e}", exc_info=True)
        # 硬删除失败通常是内部错误
        raise APIException("永久删除订单失败。", error_code=ErrorCode.DATABASE_ERROR.value)

# --- (可选) 更新订单项服务 ---
# 这个功能在原代码中有，但可以考虑是否真的需要独立接口，还是在更新订单时处理
# def update_order_item_quantity(order_id: int, order_item_id: int, quantity: int) -> Dict[str, Any]:
#     """更新订单中某个订单项的数量，并重新计算订单总价。"""
#     if quantity <= 0:
#         raise ValidationError("数量必须大于 0。", error_code=ErrorCode.PARAM_INVALID.value)
#
#     try:
#         order = Order.query.options(selectinload(Order.order_items)).get(order_id)
#         if not order:
#             raise NotFoundError(...)
#         if order.state not in [OrderState.PENDING]: # 只能修改待处理订单的项
#             raise BusinessError(...)
#
#         item_to_update = None
#         for item in order.order_items:
#             if item.order_item_id == order_item_id:
#                 item_to_update = item
#                 break
#
#         if not item_to_update:
#             raise NotFoundError(...)
#
#         dish = Dish.query.get(item_to_update.dish_id)
#         if not dish:
#              raise NotFoundError(...) # 理论上不应发生
#
#         # 计算库存变化量
#         stock_change = quantity - item_to_update.quantity
#
#         # 检查总库存是否足够（如果增加数量）
#         if stock_change > 0 and dish.stock < stock_change:
#              raise BusinessError(...)
#
#         # 更新订单项数量
#         item_to_update.quantity = quantity
#         # 更新菜品库存
#         dish.stock -= stock_change # 增加数量则减少库存，减少数量则增加库存
#
#         # 重新计算订单总价并更新
#         new_total_price = order.calculate_total_price()
#         order.price = new_total_price
#
#         db.session.commit()
#         logger.info(...)
#         return _serialize_order(order) # 返回更新后的整个订单
#
#     except (NotFoundError, ValidationError, BusinessError) as e:
#          db.session.rollback()
#          raise e
#     except SQLAlchemyError as e:
#          db.session.rollback()
#          raise APIException(...)
