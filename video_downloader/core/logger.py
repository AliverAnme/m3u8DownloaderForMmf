#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""通用日志模块，支持控制台和文件双重输出"""

import os
import logging
import datetime
import sys
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any


class LoggerManager:
    """日志管理器类，提供统一的日志功能"""

    # 单例模式
    _instance: Optional["LoggerManager"] = None
    _lock = threading.Lock()  # 使用线程锁保证线程安全

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化日志管理器"""
        # 日志配置字典
        self.loggers: Dict[str, logging.Logger] = {}
        # 日志格式
        self.log_format = "%(asctime)s - [%(levelname)s] - %(message)s"
        # 日期格式
        self.date_format = "%Y-%m-%d %H:%M:%S"
        # 日志文件目录
        self.log_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "log"
        )

        # 确保日志目录存在
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def get_logger(self, name: str = "default") -> logging.Logger:
        """获取指定名称的logger实例，如果不存在则创建"""
        if name not in self.loggers:
            with self._lock:
                if name not in self.loggers:
                    logger = self._create_logger(name)
                    self.loggers[name] = logger
        return self.loggers[name]

    def _create_logger(self, name: str) -> logging.Logger:
        """创建logger实例"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # 默认设置为最低级别，便于控制

        # 避免重复添加处理器
        if not logger.handlers:
            # 创建控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)  # 控制台输出INFO级别及以上日志

            # 创建文件处理器 - 按日期滚动
            log_file_path = os.path.join(self.log_dir, f"{name}.log")
            file_handler = TimedRotatingFileHandler(
                log_file_path,
                when="midnight",  # 在午夜时滚动
                interval=1,  # 每天一个文件
                backupCount=30,  # 保留30天的日志
                encoding="utf-8",  # 支持UTF-8编码
            )
            file_handler.setLevel(logging.DEBUG)  # 文件记录DEBUG级别及以上日志

            # 创建错误日志文件处理器
            error_log_file_path = os.path.join(self.log_dir, f"{name}_error.log")
            error_file_handler = TimedRotatingFileHandler(
                error_log_file_path,
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            error_file_handler.setLevel(logging.ERROR)  # 只记录错误级别日志

            # 设置日志格式
            formatter = logging.Formatter(self.log_format, self.date_format)
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            error_file_handler.setFormatter(formatter)

            # 添加处理器到logger
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
            logger.addHandler(error_file_handler)

        return logger

    def set_level(self, name: str, level: int) -> None:
        """设置指定logger的日志级别"""
        if name in self.loggers:
            self.loggers[name].setLevel(level)

    def set_console_level(self, name: str, level: int) -> None:
        """设置指定logger的控制台输出级别"""
        if name in self.loggers:
            for handler in self.loggers[name].handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(level)
                    break

    def set_file_level(self, name: str, level: int) -> None:
        """设置指定logger的文件输出级别"""
        if name in self.loggers:
            for handler in self.loggers[name].handlers:
                if isinstance(
                    handler, TimedRotatingFileHandler
                ) and not handler.baseFilename.endswith("_error.log"):
                    handler.setLevel(level)
                    break


# 创建全局logger实例，方便直接导入使用
def get_logger(name: str = "default") -> logging.Logger:
    """获取logger实例的快捷函数"""
    return LoggerManager().get_logger(name)


# 创建默认logger
default_logger = get_logger()


# 导出常用的日志方法
def debug(msg: str, *args, **kwargs) -> None:
    """记录调试信息"""
    default_logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """记录一般信息"""
    default_logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """记录警告信息"""
    default_logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """记录错误信息"""
    default_logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """记录严重错误信息"""
    default_logger.critical(msg, *args, **kwargs)


if __name__ == "__main__":
    # 测试日志功能
    logger = get_logger("test")
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.critical("这是一条严重错误信息")

    # 测试全局函数
    debug("这是使用全局debug函数的调试信息")
    info("这是使用全局info函数的普通信息")
    warning("这是使用全局warning函数的警告信息")
    error("这是使用全局error函数的错误信息")
    critical("这是使用全局critical函数的严重错误信息")

    # 测试中文支持
    logger.info("这是一条包含中文的日志信息")
    error("这是一条包含中文的错误信息")

    info(
        f"日志文件已生成在: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'log')}"
    )
