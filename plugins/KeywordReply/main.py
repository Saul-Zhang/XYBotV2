
from loguru import logger
from WechatAPI.Client import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import on_text_message
from utils.finalshell_crack import FinalShellCrack
from utils.plugin_base import PluginBase


class KeywordReply(PluginBase):
    description = "关键词回复"
    author = "saul"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.enabled = True
        self.db = XYBotDB()

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        logger.info("收到文本消息: {}", message)
        if message["FromWxid"] == "wxid_a2tnuxvrhszz22" and  FinalShellCrack.is_machine_code(message["Content"]):
            await bot.send_text_message(message["FromWxid"], FinalShellCrack.crack(message["Content"]))
        keyword_reply_config = self.db.get_config("KeywordReply")
        if keyword_reply_config["enable"]:
            keyword = keyword_reply_config["keyword"]
            for k, v in keyword.items():
                if k == message["Content"]:
                    await bot.send_text_message(message["FromWxid"], v)
                    break

