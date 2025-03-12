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
        try:
            start_time = datetime.now()
            logger.info("开始获取通讯录信息时间：{}", start_time)

            id_list = []
            wx_seq, chatroom_seq = 0, 0
            while True:
                contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
                if not contact_list:
                    logger.error("获取联系人列表失败，返回为空")
                    return []
                
                logger.debug("获取通讯录信息列表：{}", contact_list)
                id_list.extend(contact_list.get("ContactUsernameList", []))
                wx_seq = contact_list.get("CurrentWxcontactSeq", 0)
                chatroom_seq = contact_list.get("CurrentChatRoomContactSeq", 0)
                if contact_list.get("CountinueFlag", 0) != 1:
                    break

            if not id_list:
                logger.warning("未获取到任何联系人ID")
                return []

            # 使用协程池处理联系人信息获取
            info_list = []
            chunks = [id_list[i:i + 20] for i in range(0, len(id_list), 20)]
            sem = asyncio.Semaphore(20)

            async def fetch_contacts(id_chunk):
                try:
                    contact_info = await bot.get_contact(id_chunk)
                    if contact_info:
                        logger.debug("获取联系人详细信息成功：{}", len(contact_info))
                        return contact_info
                    return []
                except Exception as e:
                    logger.error("获取联系人详细信息失败: {}", str(e))
                    return []

            async def worker(chunk):
                async with sem:
                    if chunk:  # 确保chunk不为空
                        return await fetch_contacts(chunk[:-1])
                    return []

            tasks = [worker(chunk) for chunk in chunks if chunk]
            results = await asyncio.gather(*tasks)

            # 合并结果
            for result in results:
                if result:  # 确保result不为空
                    info_list.extend(result)

            clean_info = []
            for info in info_list:
                if not isinstance(info, dict):
                    logger.warning("跳过无效的联系人信息：{}", info)
                    continue
                    
                username = info.get("UserName", {})
                if not isinstance(username, dict):
                    continue
                    
                wxid = username.get("string", "")
                if not wxid:
                    continue

                nickname = info.get("NickName", {})
                remark = info.get("Remark", {})
                
                contact_info = {
                    "Wxid": wxid,
                    "Nickname": nickname.get("string", "") if isinstance(nickname, dict) else "",
                    "Remark": remark.get("string", "") if isinstance(remark, dict) else "",
                    "Alias": info.get("Alias", ""),
                    "BigHeadImgUrl": info.get("BigHeadImgUrl", "")
                }
                clean_info.append(contact_info)

            # 保存联系人信息到数据库
            saved_count = 0
            for contact in clean_info:
                try:
                    user = User(
                        wxid=contact["Wxid"],
                        nickname=contact["Nickname"],
                        remark=contact["Remark"],
                        wx_num=contact["Alias"],
                        big_head_img_url=contact["BigHeadImgUrl"]
                    )
                    self.db.save_or_update_contact(user)
                    saved_count += 1
                except Exception as e:
                    logger.error("保存联系人信息失败: {} - {}", contact["Wxid"], str(e))

            done_time = datetime.now()
            logger.info("获取通讯录信息完成，共处理 {} 个联系人，成功保存 {} 个，耗时：{}", 
                       len(clean_info), saved_count, done_time - start_time)
            
            return clean_info

        except Exception as e:
            logger.error("获取联系人信息过程中发生错误: {}", str(e))
            logger.exception(e)
            return [] 