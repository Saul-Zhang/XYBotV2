import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs, urlencode

from WechatAPI import WechatAPIClient
from database.XYBotDB import Chatroom, OfficialAccount, XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase
from loguru import logger

class OfficalAccountSubscribe(PluginBase):
    description = "公众号订阅"
    author = "saul"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        self.db = XYBotDB()
        config = self.db.get_config("OfficalAccountSubscribe")
        self.enable = config.get("enable", True)
        self.command = config.get("command", ["订阅公众号", "取消订阅公众号", "公众号列表"])
        self.command_format = config.get("command-format", "订阅公众号 [公众号ID]")

        logger.info("OfficalAccountSubscribe插件初始化完成，enable={}, command={}", self.enable, self.command)

    @on_official_account_message
    async def on_official_account_message(self, bot: WechatAPIClient, message: dict):
        logger.info("收到公众号消息事件，开始处理")
        logger.debug("消息内容：{}", message)
        
        if not self.enable:
            logger.info("插件未启用，跳过处理")
            return
            
        if message["FromWxid"].endswith("@chatroom"):
            logger.info("群聊消息，跳过处理")
            return
            
        official_account = self.db.get_official_account_by_wxid(message["FromWxid"])
        logger.debug("公众号信息：{}", official_account)
        
        if official_account:
            subscriptions = self.db.get_subscription_user(official_account.wxid)
            xml = self.parse_xml_to_appmsg(message["Content"])
            logger.debug("转发的公众号消息：{}", xml)
            logger.debug("公众号订阅用户：{}", subscriptions)
            for subscription in subscriptions:
                await bot.send_app_message(subscription.user_wxid, xml, 0)
        else:
            logger.info("未找到对应的公众号信息：{}", message["FromWxid"])

    def parse_xml_to_appmsg(self, xml_str):
        # 解析XML
        root = ET.fromstring(xml_str)
        appmsg = root.find('appmsg')

        # 提取字段（自动处理CDATA）
        title = appmsg.find('title').text
        original_url = appmsg.find('url').text

        # 清理URL参数
        def clean_url(url):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            keep_params = {'__biz', 'mid', 'idx', 'sn', 'chksm', 'scene', 'xtrack'}
            filtered = {k: v for k, v in query.items() if k in keep_params}
            new_query = urlencode(filtered, doseq=True)
            return parsed._replace(query=new_query).geturl()

        cleaned_url = clean_url(original_url)

        # 提取来源信息
        publisher = root.find('.//mmreader/publisher')
        sourceusername = publisher.find('username').text
        sourcedisplayname = publisher.find('nickname').text

        # 提取缩略图URL
        thumburl = appmsg.find('thumburl').text

        # 字符串拼接新XML
        new_xml = f'''<appmsg appid="" sdkver="0">
                <title>{title}</title>
                <type>5</type>
                <showtype>0</showtype>
                <url>{cleaned_url}</url>
                <sourceusername>{sourceusername}</sourceusername>
                <sourcedisplayname>{sourcedisplayname}</sourcedisplayname>
                <thumburl>{thumburl}</thumburl>
                </appmsg>'''.replace('\n', '')  # 移除换行符保持紧凑

        return new_xml
    
    @on_text_message
    async def on_text_message(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            logger.info("插件未启用，跳过处理")
            return
            
        if message["FromWxid"].endswith("@chatroom"):
            chatroom = self.db.get_chatroom_by_wxid(message["FromWxid"])
            if chatroom:
                return
            else:
                contact_info = await bot.get_contact(message["FromWxid"])   
                if contact_info:
                    chatroom = Chatroom(
                        chatroom_id=message["FromWxid"],
                        name=contact_info.get("NickName", {}).get("string", ""),
                        small_head_img_url=contact_info.get("SmallHeadImgUrl", ""),
                        member_count=contact_info.get("MemberCount", 0),
                    )
                    self.db.save_or_update_chatroom(chatroom)
        elif message["FromWxid"].startswith("gh_"):
            official_account = self.db.get_official_account_by_wxid(message["FromWxid"])
            if official_account:
                return
            else:
                contact_info = await bot.get_contact(message["FromWxid"])
                if contact_info:
                    official_account = OfficialAccount(
                        wxid=contact_info.get("UserName", {}).get("string", ""),
                        name=contact_info.get("NickName", {}).get("string", ""),
                        small_head_img_url=contact_info.get("SmallHeadImgUrl", ""),
                        fake_id=""
                    )
                    self.db.save_or_update_official_account(official_account)
        else:
            return
