import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs, urlencode

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class OfficalAccountSubscribe(PluginBase):
    description = "公众号订阅"
    author = "saul"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # self.enable = config["enable"]
        # self.command = config["command"]
        # self.command_format = config["command-format"]

        self.db = XYBotDB()

    @on_official_account_message()
    async def on_official_account_message(self, bot: WechatAPIClient, message: dict):
        if message["FromUserName"].endswith("@chatroom"):
            return
        official_account = self.db.get_official_account_by_wxid(message["FromUserName"])
        if official_account:
            subscriptions = self.db.get_subscription_user(official_account.wxid)
            xml = self.parse_xml_to_appmsg(message["Content"])
            for subscription in subscriptions:
                await bot.send_app_message(subscription.user_wxid, xml, 0)

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
