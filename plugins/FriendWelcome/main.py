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
        
        try:
            # 获取XML内容字符串
            content = message.get("Content", {}).get("string", "")
            if not content:
                logger.error("好友请求消息内容为空")
                return
                
            # 解析XML
            root = ET.fromstring(content)
            
            # 从XML属性中获取必要信息
            scene = int(root.get("scene", "0"))
            v1 = root.get("encryptusername", "")
            v2 = root.get("ticket", "")
            
            if not all([scene, v1, v2]):
                logger.error("缺少必要的好友请求参数: scene={}, v1={}, v2={}", scene, v1, v2)
                return
                
            # 接受好友请求
            # await bot.accept_friend(scene, v1, v2)
            # logger.info("已接受好友请求: scene={}, v1={}, v2={}", scene, v1, v2)
        
        except Exception as e:
            logger.error("处理好友请求失败: {}", str(e))

    @on_add_friend_success
    async def handle_add_friend_success(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        logger.info("收到添加好友成功消息: {}", message)

        # welcome_message = self.db.get_config("FriendWelcome")["welcome-message"]
        # await bot.send_text_message(message["FromWxid"], welcome_message)
