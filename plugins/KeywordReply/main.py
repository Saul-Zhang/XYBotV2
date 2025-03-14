
from loguru import logger
from WechatAPI.Client import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import on_quote_message, on_text_message
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

    @on_quote_message
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        logger.info("收到引用消息: {}", message)
        if message["FromWxid"] == "wxid_a2tnuxvrhszz22":
            if message["Content"] == "1":
                nickname = message["Quote"]["nickname"]
                logger.debug("正在查找公众号: {}", nickname)
                official_account = self.db.find_official_account_by_name(nickname)
                if official_account:
                    logger.debug("找到公众号: {} ({})", nickname, official_account.wxid)
                    if self.db.save_subscription(message["SenderWxid"], official_account.wxid):
                        logger.info("成功保存订阅关系: {} -> {}", message["SenderWxid"], official_account.wxid)
                        await bot.send_text_message(message["SenderWxid"], f"已开始监听公众号: {nickname}")
                    else:
                        logger.error("保存订阅关系失败")
                else:
                    logger.warning("未找到公众号: {}", nickname)
            elif message["Content"] == "2":
                nickname = message["Quote"]["nickname"]
                logger.debug("正在查找公众号: {}", nickname)
                official_account = self.db.find_official_account_by_name(nickname)
                if official_account:
                    logger.debug("找到公众号: {} ({})", nickname, official_account.wxid)
                    if self.db.delete_subscription(message["SenderWxid"], official_account.wxid):
                        logger.info("成功取消订阅: {} -> {}", message["SenderWxid"], official_account.wxid)
                        await bot.send_text_message(message["SenderWxid"], f"已取消监听公众号: {nickname}")
                    else:
                        logger.error("取消订阅失败")
                else:
                    logger.warning("未找到公众号: {}", nickname)
