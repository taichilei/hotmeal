"""
@file         app/services/staff_service.py
@description  staff user service
@date         2025-05-05
@author       taichilei
"""

import logging

from werkzeug.exceptions import BadRequest, Conflict
from werkzeug.security import generate_password_hash

from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.utils.db import db

logger = logging.getLogger(__name__)


def create_staff_user(operator_id: int, user_data: dict) -> dict:
    """
    Create a new staff user.

    :param operator_id: The id of the operator who creates the user.
    :param user_data: The data of the new user.
    :return: The data of the new user.
    """
    required_fields = ['account', 'username']
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            raise BadRequest(f"{field} is required.")

    account = user_data['account']
    username = user_data['username']
    password = user_data.get('password', 'hotmeal')
    email = user_data.get('email')
    phone_number = user_data.get('phone_number')
    favorite_cuisine = user_data.get('favorite_cuisine')

    if User.query.filter_by(account=account).first():
        raise Conflict(f"Account '{account}' already exists.")

    new_user = User(
        account=account,
        username=username,
        password_hash=generate_password_hash(password),
        role=UserRole.STAFF,
        status=UserStatus.ACTIVE,
        email=email,
        phone_number=phone_number,
        favorite_cuisine=favorite_cuisine,
    )

    db.session.add(new_user)
    db.session.commit()

    logger.info(f"[admin] Operator {operator_id} created STAFF user: {account}")
    return new_user.to_dict()


def get_staff_user(user_id: int) -> dict:
    """
    Get a staff user.

    :param user_id: The id of the user to be retrieved.
    :return: The data of the user.
    """
    user = User.query.get(user_id)
    if not user:
        raise BadRequest(f"User {user_id} does not exist.")

    return user.to_dict()


def update_staff_user(operator_id: int, user_id: int, user_data: dict) -> dict:
    """
    Update a staff user.

    :param operator_id: The id of the operator who updates the user.
    :param user_id: The id of the user to be updated.
    :param user_data: The data to be updated.
    :return: The updated user data.
    """
    user = User.query.get(user_id)
    if not user:
        raise BadRequest(f"User {user_id} does not exist.")

    # 可更新字段集合
    updatable_fields = {'account', 'username', 'password', 'email', 'phone_number',
                        'favorite_cuisine', 'role'}

    for field, value in user_data.items():
        if field not in updatable_fields:
            continue
        if field == 'password':
            if value:
                user.password_hash = generate_password_hash(value)
        elif field == 'role':
            try:
                user.role = UserRole(value)
            except ValueError:
                raise BadRequest(f"Invalid role: {value}")
        else:
            setattr(user, field, value)

    db.session.commit()

    logger.info(f"[admin] Operator {operator_id} updated STAFF user: {user.account}")
    return user.to_dict()


def delete_staff_user(operator_id: int, user_id: int) -> None:
    """
    Delete a staff user.

    :param operator_id: The id of the operator who deletes the user.
    :param user_id: The id of the user to be deleted.
    :return: None.
    """
    user = User.query.get(user_id)
    if not user:
        raise BadRequest(f"User {user_id} does not exist.")

    db.session.delete(user)
    db.session.commit()

    logger.info(f"[admin] Operator {operator_id} deleted STAFF user: {user.account}")
