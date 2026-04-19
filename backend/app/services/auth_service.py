"""
@File       : auth_service.py
@Date       : 2025-04-09 (Refactored: 2025-03-01)
@Desc       : Service responsible for user authentication (credential verification) and JWT generation.

@Version    : 1.1.0 # Version updated after refactor
"""

import logging

from flask_jwt_extended import create_access_token

from app.models.user import User
from app.utils.response import AuthenticationError

logger = logging.getLogger(__name__)


# SECRET_KEY is typically handled by Flask-JWT-Extended config (using app.config['SECRET_KEY'] or app.config['JWT_SECRET_KEY'])


class AuthService:
    """
    Provides authentication services.
    """

    @staticmethod
    def authenticate(account: str, password: str) -> User:
        """
        Authenticates a user based on account and password.

        Args:
            account: The user's account name.
            password: The user's plaintext password.

        Returns:
            The authenticated User object if credentials are valid.

        Raises:
            AuthenticationError: If the account is not found or the password does not match.
        """
        logger.debug(f"Attempting to authenticate user with account: {account}")
        # Query user by account
        user = User.query.filter_by(account=account).first()

        # Check if user exists
        if not user:
            logger.warning(f"Authentication failed: user not found for account: {account}")
            raise AuthenticationError("User not found")

        # Check if password is correct using the model's method
        if not user.check_password(password):
            logger.warning(f"Authentication failed: invalid password for account: {account}")
            raise AuthenticationError("Invalid password")

        logger.info(f"Authentication successful for account: {account}, user_id: {user.user_id}")
        # Return the User object on successful authentication
        return user

    @staticmethod
    def generate_token(user: User) -> str:
        """
        Generates a JWT access token for a given user.

        Args:
            user: The authenticated User object.

        Returns:
            A JWT access token string.
        """
        if not isinstance(user, User):
            raise TypeError("Input must be a User object")

        # Identity for the token, Flask-JWT-Extended recommends string
        identity = str(user.user_id)
        # Additional claims to include in the token (e.g., user role)
        additional_claims = {"role": user.role.value}  # Assumes role is an Enum

        # Create the access token
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        logger.debug(f"Generated JWT token for user_id: {user.user_id}")
        return access_token
