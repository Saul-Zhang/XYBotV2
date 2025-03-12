import asyncio
from datetime import datetime

from loguru import logger

from database.XYBotDB import XYBotDB, User
from WechatAPI.Client import WechatAPIClient


class ContactManager:
    def __init__(self):
        self.db = XYBotDB()

    async def fetch_and_save_contacts(self, bot: WechatAPIClient):
        """获取联系人信息并保存到数据库"""
        logger.info("开始获取通讯录信息")
        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            logger.info("获取通讯录信息列表：{}", contact_list)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        # 使用协程池处理联系人信息获取
        info_list = []

        async def fetch_contacts(id_chunk):
            contact_info = await bot.get_contact(id_chunk)
            logger.info("获取通讯录信息：{}", contact_info)
            return contact_info

        chunks = [id_list[i:i + 20] for i in range(0, len(id_list), 20)]
        sem = asyncio.Semaphore(20)

        async def worker(chunk):
            async with sem:
                return await fetch_contacts(chunk[:-1])  # 去掉最后一个ID，保持与原代码一致

        tasks = [worker(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        # 合并结果
        for result in results:
            info_list.extend(result)

        clean_info = []
        logger.info("获取通讯录完整信息列表：{}", info_list)
        for info in info_list:
            if info.get("UserName", {}).get("string", ""):
                clean_info.append({
                    "Wxid": info.get("UserName", {}).get("string", ""),
                    "Nickname": info.get("NickName", {}).get("string", ""),
                    "Remark": info.get("Remark", {}).get("string"),
                    "Alias": info.get("Alias", ""),
                    "BigHeadImgUrl": info.get("BigHeadImgUrl", "")})

        # 保存联系人信息到数据库
        for contact in clean_info:
            user = User(
                wxid=contact["Wxid"],
                nickname=contact["Nickname"],
                remark=contact["Remark"],
                wx_num=contact["Alias"],
                big_head_img_url=contact["BigHeadImgUrl"]
            )
            self.db.save_or_update_contact(user)
        logger.success("保存联系人信息完成")
        return clean_info 