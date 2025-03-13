import asyncio
import os
import sys
import time
import tomllib
import traceback
from pathlib import Path
from threading import Thread

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from web.app import app

from bot_core import bot_core


def is_api_message(record):
    return record["level"].name == "API"


class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        self.last_triggered = 0
        self.cooldown = 2  # 冷却时间(秒)
        self.waiting_for_change = False  # 是否在等待文件改变

    def on_modified(self, event):
        if not event.is_directory:
            current_time = time.time()
            if current_time - self.last_triggered < self.cooldown:
                return

            file_path = Path(event.src_path).resolve()
            if (file_path.name == "main_config.toml" or
                    "plugins" in str(file_path) and file_path.suffix in ['.py', '.toml']):
                logger.info(f"检测到文件变化: {file_path}")
                self.last_triggered = current_time
                if self.waiting_for_change:
                    logger.info("检测到文件改变，正在重启...")
                    self.waiting_for_change = False
                self.restart_callback()


def run_flask():
    """在单独的线程中运行Flask应用"""
    app.run(host='0.0.0.0', port=5000, debug=False)


async def main():
    try:
        # 配置日志
        logger.remove()
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
            level="DEBUG"
        )
        logger.add(
            "logs/error.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="ERROR",
            rotation="1 day",
            retention="7 days"
        )

        # 确保logs目录存在
        Path("logs").mkdir(exist_ok=True)

        # 在单独的线程中启动Flask应用
        logger.info("启动Web管理界面...")
        web_thread = Thread(target=run_flask, daemon=True)
        web_thread.start()
        logger.success("Web管理界面启动成功，访问 http://localhost:5000")

        # 启动机器人核心
        logger.info("启动机器人核心...")
        await bot_core()

    except KeyboardInterrupt:
        logger.info("程序正在关闭...")
    except Exception as e:
        logger.error("发生错误: {}", str(e))
        logger.exception(e)
    finally:
        logger.info("程序已关闭")


if __name__ == "__main__":
    # 防止低版本Python运行
    if sys.version_info.major != 3 and sys.version_info.minor != 11:
        print("请使用Python3.11")
        sys.exit(1)

    logger.level("API", no=1, color="<cyan>")

    logger.add(
        "logs/XYBot_{time}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        encoding="utf-8",
        enqueue=True,
        retention="2 weeks",
        rotation="00:01",
        backtrace=True,
        diagnose=True,
        level="DEBUG",
    )
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="TRACE",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    asyncio.run(main())
