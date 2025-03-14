import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime

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
        logger.debug("公众号名称：{}", official_account.name if official_account else "未知")
        
        if official_account:
            # 解析消息内容获取标题
            try:
                root = ET.fromstring(message["Content"])
                appmsg = root.find('appmsg')
                title = appmsg.find('title').text if appmsg is not None else "未知标题"
            except Exception as e:
                logger.error("解析公众号消息标题失败: {}", str(e))
                title = "解析失败"

            # 更新公众号最后消息信息
            official_account.last_message = title
            official_account.last_message_time = datetime.now()
            if self.db.update_official_account(official_account):
                logger.debug("更新公众号最后消息成功: {} - {}", official_account.name, title)
            else:
                logger.error("更新公众号最后消息失败")

            # 转发消息给订阅用户
            subscriptions = self.db.get_subscription_user(official_account.wxid)
            xml, extra_msg = self.parse_xml_to_appmsg(message["Content"])
            logger.debug("公众号订阅用户数量：{}", len(subscriptions))
            for subscription in subscriptions:
                await bot.send_app_message(subscription.user_wxid, xml, 0)
            if extra_msg:
                await bot.send_text_message(subscription.user_wxid, extra_msg)
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

        # 检查是否有多篇文章
        extra_msg = ""
        try:
            category = root.find('.//mmreader/category')
            if category is not None:
                items = category.findall('item')
                if len(items) > 1:
                    # 收集所有副文章的标题
                    titles = []
                    for i, item in enumerate(items[1:], 1):  # 从第二篇文章开始
                        item_title = item.find('title').text
                        if item_title:
                            titles.append(f"{i}.{item_title}")
                    
                    if titles:
                        extra_msg = f"【{sourcedisplayname}】还推送了{len(titles)}篇副文章\n" + "\n".join(titles)
        except Exception as e:
            logger.error("解析副文章失败: {}", str(e))

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

        return new_xml, extra_msg
    
    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            logger.info("插件未启用，跳过处理")
            return

        logger.debug("准备开始检测是否已保存当前账号")
        if message["FromWxid"].endswith("@chatroom"):
            logger.debug("当前账号是群聊")
            chatroom = self.db.get_chatroom_by_wxid(message["FromWxid"])
            if chatroom:
                logger.debug("当前账号已保存")
                return
            else:
                logger.debug("当前账号未保存，开始保存")
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
            logger.debug("当前账号是公众号")
            official_account = self.db.get_official_account_by_wxid(message["FromWxid"])
            if official_account:
                logger.debug("当前账号已保存")
                return
            else:
                logger.debug("当前账号未保存，开始保存")
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
