import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime

from loguru import logger

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import on_add_friend_success, on_friend_request, on_system_message
from utils.plugin_base import PluginBase


class FriendWelcome(PluginBase):
    description = "好友欢迎"
    author = "saul"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/FriendWelcome/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["FriendWelcome"]

        self.enable = config["enable"]
        self.db = XYBotDB()

    @on_friend_request
    async def handle_friend_request(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        logger.info("收到添加好友请求: {}", message)
        await bot.accept_friend_request(message["FromWxid"])

    @on_add_friend_success
    async def handle_add_friend_success(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        logger.info("收到添加好友成功消息: {}", message)

        welcome_message = self.db.get_config("FriendWelcome")["welcome-message"]
        await bot.send_text_message(message["FromWxid"], welcome_message)
