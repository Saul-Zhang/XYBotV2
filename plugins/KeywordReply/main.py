
from loguru import logger
from WechatAPI.Client import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import on_text_message
from utils.plugin_base import PluginBase


class KeywordReply(PluginBase):
    description = "关键词回复"
    author = "saul"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.db = XYBotDB()

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        logger.info("收到文本消息: {}", message)
        keyword_reply_config = self.db.get_config("KeywordReply")
        keyword = keyword_reply_config["keyword"]
        for k, v in keyword.items():
            if k == message["Content"]:
                await bot.send_text_message(message["FromWxid"], v)
                break

