"""
@File       : time_utils.py
@Date       : 2025-03-01
@Desc       :


"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def now_utc() -> datetime:
    """
    获取当前 UTC 时间（带时区）
    """
    return datetime.now(ZoneInfo("UTC"))


def convert_to_local_time(utc_time: datetime, timezone: str = "Asia/Shanghai") -> datetime:
    """
    将 UTC 时间对象转换为指定时区，并返回 datetime 对象
    :param utc_time: UTC 时间对象
    :param timezone: 时区名称，默认使用上海时区
    :return: datetime 对象
    """
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=ZoneInfo("UTC"))
    else:
        utc_time = utc_time.astimezone(ZoneInfo("UTC"))
    return utc_time.astimezone(ZoneInfo(timezone))


def convert_to_local_time_safe(utc_time: datetime | str, timezone: str = "Asia/Shanghai") -> datetime:
    """
    兼容 datetime 和 ISO 字符串的安全时区转换
    :param utc_time: datetime 或 ISO 字符串
    :param timezone: 目标时区
    :return: 本地化 datetime 对象
    """
    if isinstance(utc_time, str):
        utc_time = parse_iso_datetime(utc_time) or now_utc()
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=ZoneInfo("UTC"))
    else:
        utc_time = utc_time.astimezone(ZoneInfo("UTC"))
    return utc_time.astimezone(ZoneInfo(timezone))


def serialize_datetime(dt: datetime, timezone: str = "Asia/Shanghai") -> str:
    """
    将 datetime 对象序列化为 ISO 格式字符串，默认转换为东八区
    :param dt: datetime 对象
    :param timezone: 目标时区，默认 Asia/Shanghai
    :return: ISO 格式字符串，如 2025-04-02T18:00:00+08:00
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    else:
        dt = dt.astimezone(ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(timezone)).isoformat()


def log_friendly_time(dt: datetime, timezone: str = "Asia/Shanghai") -> str:
    """
    将时间格式化为日志友好的本地时间字符串
    :param dt: 时间对象
    :param timezone: 时区
    :return: 字符串格式，如 "2025-04-02 18:00:00"
    """
    local_dt = convert_to_local_time(dt, timezone)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_iso_datetime(dt_str: str) -> datetime | None:
    """
    将 ISO 格式字符串转换为带时区的 datetime 对象（默认为 UTC）
    如果格式非法，返回 None
    """
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt
    except ValueError:
        return None


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间对象为字符串
    :param dt: 时间对象
    :param fmt: 格式字符串，默认为 "%Y-%m-%d %H:%M:%S"
    :return: 格式化后的时间字符串
    """
    return dt.strftime(fmt)


def humanize_time_ago(dt: datetime, timezone: str = "Asia/Shanghai") -> str:
    """
    生成“x分钟前”/“x小时前”这样的相对时间描述
    :param dt: 时间对象
    :param timezone: 时区名称，默认使用上海时区
    :return: 相对时间描述字符串
    """
    local_dt = convert_to_local_time(dt, timezone)
    now = datetime.now(ZoneInfo(timezone))
    diff = now - local_dt

    if diff < timedelta(minutes=1):
        return "刚刚"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    else:
        days = diff.days
        return f"{days}天前"
