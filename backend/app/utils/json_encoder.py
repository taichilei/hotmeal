"""
@File       : json_encoder.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 自定义 JSON 编码器，处理 datetime、Decimal、Enum、UUID 等特殊类型的序列化
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from flask.json.provider import DefaultJSONProvider


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        """
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)
