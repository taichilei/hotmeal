"""
@File       : logger.py
@Date       : 2025-03-01
@Description: Provides function to set up application logging based on Flask config.
@Project    : HotMeal - Personalized Meal Ordering System Based on Recommendation Algorithms

"""

import logging
import logging.config  # 导入 logging.config
import os
import time
from typing import Any  # 导入类型提示

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older Python versions (需要安装 tzdata)
    # from backports.zoneinfo import ZoneInfo
    # 或者使用 pytz (需要安装 pytz)
    # import pytz
    ZoneInfo = None  # 标记 ZoneInfo 不可用


# --- 不再在模块级别读取环境变量或配置 ---
# LOG_FILE = ...
# log_dir = ...
# ...

# --- 北京时间处理 (使用 zoneinfo 或 pytz 替代) ---
# class BeijingFormatter(logging.Formatter):
#     """自定义 Formatter 来处理北京时间"""
#     tz = None
#     if ZoneInfo:
#         try:
#            tz = ZoneInfo("Asia/Shanghai")
#         except Exception:
#             tz = None
#     # elif pytz:
#     #     try:
#     #         tz = pytz.timezone("Asia/Shanghai")
#     #     except Exception:
#     #         tz = None

#     def converter(self, timestamp):
#         dt = datetime.fromtimestamp(timestamp, tz=self.tz)
#         return dt.timetuple()

#     def formatTime(self, record, datefmt=None):
#         ct = self.converter(record.created)
#         if datefmt:
#             s = time.strftime(datefmt, ct)
#         else:
#             # 默认 ISO 格式带毫秒
#             t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
#             s = "%s,%03d" % (t, record.msecs)
#         return s

# --- 或者，更简单的方式是在 Formatter 的 datefmt 中处理（如果驱动支持）---
# --- 或者保持原来的 beijing_time 函数，它对于固定偏移量有效 ---
def beijing_time(*args):
    """简单的北京时间转换器（+8 小时）"""
    # 注意：这种方式不处理夏令时等复杂情况
    return time.localtime(time.mktime(time.gmtime()) + 8 * 3600)


def setup_logging(config: dict[str, Any], app_name: str = "hotmeal"):
    """
    根据 Flask 应用配置设置日志系统。

    Args:
        config: Flask app.config 对象 (或兼容的字典)。
        app_name: 应用主 logger 的名称。
    """
    # --- 从 Flask 配置或默认值获取日志设置 ---
    log_level = config.get('LOG_LEVEL', 'INFO').upper()
    log_file = config.get('LOG_FILE', 'logs/app.log')
    log_max_bytes = config.get('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
    log_backup_count = config.get('LOG_BACKUP_COUNT', 5)
    log_handler_type = config.get('LOG_HANDLER_TYPE', 'rotating').lower()  # rotating or timed
    log_format_type = config.get('LOG_FORMAT', 'default').lower()  # default or json

    # 自动创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            logging.info(f"日志目录已创建: {log_dir}")
        except OSError as e:
            logging.error(f"创建日志目录失败: {log_dir}, 错误: {e}", exc_info=True)
            # 可以选择继续（日志可能写入失败）或抛出异常
            # raise RuntimeError(f"无法创建日志目录 {log_dir}") from e

    # --- 配置 Formatter ---
    formatter_class = "logging.Formatter"  # 默认
    formatter_format = "%(asctime)s [%(levelname)s] %(name)s - %(module)s:%(lineno)d - %(message)s"  # 更详细的默认格式
    date_format = "%Y-%m-%d %H:%M:%S"

    if log_format_type == "json":
        try:
            # 确保导入成功
            from pythonjsonlogger import jsonlogger
            formatter_class = "pythonjsonlogger.jsonlogger.JsonFormatter"
            # JSON 格式可以自定义字段
            formatter_format = "%(asctime)s %(levelname)s %(name)s %(module)s %(lineno)d %(message)s"
            # date_format = "%Y-%m-%dT%H:%M:%S.%fZ" # ISO UTC 格式
            logging.info("使用 JSON 日志格式。")
        except ImportError:
            logging.warning("未安装 'python-json-logger'，将回退到默认文本日志格式。")
            # 使用默认配置

    # --- 配置 Handler ---
    if log_handler_type == "timed":
        file_handler_class = "logging.handlers.TimedRotatingFileHandler"
        file_handler_config = {
            "filename": log_file,
            "when": config.get('LOG_WHEN', 'midnight'),  # 例如 'midnight', 'h', 'd'
            "interval": config.get('LOG_INTERVAL', 1),
            "backupCount": log_backup_count,
            "encoding": "utf-8",  # 明确编码
        }
        logging.info(f"使用 TimedRotatingFileHandler，路径: {log_file}")
    else:  # 默认为 rotating
        file_handler_class = "logging.handlers.RotatingFileHandler"
        file_handler_config = {
            "filename": log_file,
            "maxBytes": log_max_bytes,
            "backupCount": log_backup_count,
            "encoding": "utf-8",
        }
        logging.info(f"使用 RotatingFileHandler，路径: {log_file}")

    # --- 配置时区 ---
    # 方案一：保持 beijing_time 转换器 (简单有效)
    logging.Formatter.converter = beijing_time
    # 方案二：使用自定义 Formatter (如果需要更精确的时区处理)
    # formatter_class_obj = BeijingFormatter if log_timezone == 'Asia/Shanghai' else logging.Formatter

    # --- 构建 dictConfig ---
    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,  # 不禁用现有 logger (如 Flask 的)
        "formatters": {
            "default": {
                "format": formatter_format,
                "datefmt": date_format,
                "class": formatter_class,
                # 如果使用自定义 Formatter: "()": BeijingFormatter,
            },
            # 可以定义其他格式化器，例如只包含消息的简单格式
            "simple": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",  # 控制台使用默认格式
                "level": log_level,  # 控制台日志级别
                "stream": "ext://sys.stdout"  # 明确输出到 stdout
            },
            "file": {
                "class": file_handler_class,
                "formatter": "default",  # 文件使用默认格式
                "level": "DEBUG",  # 文件记录更详细的 DEBUG 级别
                **file_handler_config  # 合并 handler 配置
            },
        },
        "loggers": {
            # 应用主 logger 配置
            app_name: {  # 使用传入的应用名称
                "handlers": ["console", "file"],  # 同时输出到控制台和文件
                "level": log_level,  # 应用 logger 的级别
                "propagate": False,  # 防止日志向 root logger 传递
            },
            # 配置 SQLAlchemy 日志 (可选，控制 SQL 输出)
            "sqlalchemy.engine": {
                "handlers": ["console"],  # SQL 日志只输出到控制台 (或文件)
                # 通过 app.config['SQLALCHEMY_ECHO'] 控制是否开启，这里设为 WARNING 避免过多输出
                "level": "INFO" if config.get('SQLALCHEMY_ECHO', False) else "WARNING",
                "propagate": False,
            },
            # 配置 Werkzeug 日志 (Flask/WSGI 服务器日志)
            "werkzeug": {
                "handlers": ["console"],  # Werkzeug 日志只输出到控制台
                "level": "INFO",  # 可以设为 INFO 查看请求日志，或 WARNING 减少噪音
                "propagate": False,
            },
        },
        # 可以配置 root logger 作为最后的保障
        # "root": {
        #     "level": "WARNING",
        #     "handlers": ["console"]
        # }
    }

    # --- 应用配置 ---
    try:
        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(app_name)  # 获取配置好的 logger
        logger.info(
            f"日志系统已使用 dictConfig 配置完成。主 Logger: '{app_name}', 级别: {log_level}")
    except Exception as config_err:
        # 如果日志配置本身出错，使用 basicConfig 打印错误
        logging.basicConfig(level=logging.ERROR)
        logging.exception(f"应用日志配置失败: {config_err}")
        # 可以选择抛出异常阻止应用启动
        # raise RuntimeError("日志配置失败，应用无法启动。") from config_err

# --- 不再在模块加载时自动配置日志 ---
# logging.config.dictConfig(LOGGING_CONFIG)
# logger = logging.getLogger("hotmeal")
