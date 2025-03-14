import asyncio
from datetime import datetime

from loguru import logger

from database.XYBotDB import Chatroom, OfficialAccount, XYBotDB, User
from WechatAPI.Client import WechatAPIClient


class ContactManager:
    def __init__(self):
        self.db = XYBotDB()

    async def fetch_and_save_contacts(self, bot: WechatAPIClient):
        """获取联系人信息并保存到数据库"""
        try:
            if self.db.get_users_count() > 5:
                logger.info("数据库中已存在用户，跳过获取通讯录信息")
                return []
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

            # 使用更小的分块大小和重试机制
            info_list = []
            chunks = [id_list[i:i + 5] for i in range(0, len(id_list), 5)]  # 减小分块大小到5
            sem = asyncio.Semaphore(10)  # 限制并发数到10

            async def fetch_contacts(id_chunk, retries=3):
                for attempt in range(retries):
                    try:
                        contact_info = await bot.get_contact(id_chunk)
                        if contact_info:
                            logger.debug("获取联系人详细信息成功：chunk={}, size={}", id_chunk, len(contact_info))
                            return contact_info
                        logger.warning("获取联系人详细信息返回空：chunk={}", id_chunk)
                    except Exception as e:
                        logger.error("获取联系人详细信息失败(尝试 {}/{}): chunk={}, error={}", 
                                   attempt + 1, retries, id_chunk, str(e))
                        if attempt < retries - 1:
                            await asyncio.sleep(1)  # 失败后等待1秒再重试
                        continue
                return []  # 所有重试都失败后返回空列表

            async def worker(chunk):
                async with sem:
                    if chunk:  # 确保chunk不为空
                        return await fetch_contacts(chunk)
                    return []

            # 执行所有任务并等待结果
            tasks = [worker(chunk) for chunk in chunks if chunk]
            results = await asyncio.gather(*tasks)

            # 合并结果并记录处理的ID
            processed_ids = set()
            for result in results:
                if result:  # 确保result不为空
                    info_list.extend(result)
                    # 记录已处理的ID
                    for info in result:
                        if isinstance(info, dict) and isinstance(info.get("UserName", {}), dict):
                            wxid = info.get("UserName", {}).get("string", "")
                            if wxid:
                                processed_ids.add(wxid)

            # 检查是否有未处理的ID并单独处理
            unprocessed_ids = set(id_list) - processed_ids
            if unprocessed_ids:
                logger.warning("发现未处理的联系人ID: {}", unprocessed_ids)
                # 单独处理每个未处理的ID
                for wxid in unprocessed_ids:
                    try:
                        result = await fetch_contacts([wxid], retries=5)  # 对单个ID使用更多重试次数
                        if result:
                            info_list.extend(result)
                            logger.info("成功获取之前未处理的联系人信息: {}", wxid)
                        else:
                            logger.error("无法获取联系人信息，即使在单独处理后: {}", wxid)
                    except Exception as e:
                        logger.error("处理单个联系人信息时出错: {} - {}", wxid, str(e))

            clean_info = []
            for info in info_list:
                if not isinstance(info, dict):
                    logger.warning("跳过无效的联系人信息（非字典类型）：{}", info)
                    continue
                
                # 处理 UserName 字段
                username = info.get("UserName")
                wxid = ""
                if isinstance(username, dict):
                    wxid = username.get("string", "")
                elif isinstance(username, str):
                    wxid = username
                else:
                    logger.warning("跳过无效的联系人信息（无效的UserName类型）：{}", type(username))
                    continue

                if not wxid:
                    logger.warning("跳过无效的联系人信息（空的wxid）")
                    continue

                # 处理 NickName 字段
                nickname = info.get("NickName")
                nickname_str = ""
                if isinstance(nickname, dict):
                    nickname_str = nickname.get("string", "")
                elif isinstance(nickname, str):
                    nickname_str = nickname
                else:
                    logger.debug("无效的昵称格式，使用默认值：{}", type(nickname))

                # 处理 Remark 字段
                remark = info.get("Remark")
                remark_str = ""
                if isinstance(remark, dict):
                    remark_str = remark.get("string", "")
                elif isinstance(remark, str):
                    remark_str = remark

                # 处理群聊信息
                member_count = 0
                new_chatroom_data = info.get("NewChatroomData", {})
                if new_chatroom_data and isinstance(new_chatroom_data, dict):
                    member_count = new_chatroom_data.get("MemberCount", 0)
                
                contact_info = {
                    "Wxid": wxid,
                    "Nickname": nickname_str or "未知昵称",  # 确保昵称不为空
                    "Remark": remark_str,
                    "Alias": info.get("Alias", ""),
                    "SmallHeadImgUrl": info.get("SmallHeadImgUrl", ""),
                    "MemberCount": member_count,
                    "PersonalCard": info.get("PersonalCard", -1)
                }
                
                logger.debug("处理联系人信息：wxid={}, nickname={}", wxid, nickname_str)
                clean_info.append(contact_info)

            # 保存联系人信息到数据库
            user_count = 0
            chatroom_count = 0
            official_account_count = 0
            for contact in clean_info:
                wxid = contact["Wxid"]
                if wxid.endswith("@chatroom"):
                    chatroom = Chatroom(
                        chatroom_id=wxid,  # 使用正确的字段名
                        name=contact["Nickname"],
                        member_count=contact.get("MemberCount", 0),
                        small_head_img_url=contact["SmallHeadImgUrl"]
                    )
                    if self.db.save_or_update_chatroom(chatroom):
                        chatroom_count += 1
                        logger.debug("保存群聊信息成功: {}", wxid)
                elif wxid.startswith("gh_") or wxid == 'wxid_pzhf43hmwizd11':  # 使用更准确的公众号判断
                    official_account = OfficialAccount(
                        wxid=wxid,
                        name=contact["Nickname"],
                        small_head_img_url=contact["SmallHeadImgUrl"]
                    )
                    if self.db.save_or_update_official_account(official_account):
                        official_account_count += 1
                        logger.debug("保存公众号信息成功: {} ({})", wxid, contact["Nickname"])
                else:
                    try:
                        user = User(
                            wxid=wxid,
                            nickname=contact["Nickname"] or "未知昵称",
                            remark=contact["Remark"] or "",
                            wx_num=contact["Alias"] or "",
                            small_head_img_url=contact["SmallHeadImgUrl"] or "",
                            points=0,
                            whitelist=False,
                            ai_enabled=False,
                            signin_streak=0
                        )
                        if self.db.save_or_update_contact(user):
                            user_count += 1
                            logger.debug("保存用户信息成功: {}", wxid)
                        else:
                            logger.warning("保存用户信息失败: {}", wxid)
                    except Exception as e:
                        logger.error("保存用户信息失败: {} - {}", wxid, str(e))

            done_time = datetime.now()
            logger.info("获取通讯录信息完成，共处理 {} 个联系人，成功保存 {} 个联系人，{} 个群聊，{} 个公众号，耗时：{}", 
                       len(clean_info), user_count, chatroom_count, official_account_count, done_time - start_time)
            
            return clean_info

        except Exception as e:
            logger.error("获取联系人信息过程中发生错误: {}", str(e))
            logger.exception(e)
            return [] 