import datetime
import tomllib
from concurrent.futures import ThreadPoolExecutor
from typing import Union

from loguru import logger
from sqlalchemy import Column, String, Integer, DateTime, create_engine, JSON, Boolean
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.singleton import Singleton

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='id')
    wxid = Column(String(20), nullable=False, unique=True, index=True, comment='wxid')
    wx_num = Column(String(20), nullable=False, default="", comment='wx_num')
    points = Column(Integer, nullable=False, default=0, comment='points')
    signin_stat = Column(DateTime, nullable=False, default=datetime.datetime.fromtimestamp(0), comment='signin_stat')
    signin_streak = Column(Integer, nullable=False, default=0, comment='signin_streak')
    whitelist = Column(Boolean, nullable=False, default=False, comment='whitelist')
    llm_thread_id = Column(JSON, nullable=False, default=lambda: {}, comment='llm_thread_id')
    nickname = Column(String(50), nullable=False, default="", comment='nickname')
    big_head_img_url = Column(String(255), nullable=False, default="", comment='big_head_img_url')
    small_head_img_url = Column(String(255), nullable=False, default="", comment='small_head_img_url')
    remark = Column(String(255), nullable=False, default="", comment='remark')
    ai_enabled = Column(Boolean, nullable=False, default=False, comment='ai_enabled')


class Chatroom(Base):
    __tablename__ = 'chatroom'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='id')
    chatroom_id = Column(String(20),  nullable=False, unique=True, index=True,
                         comment='chatroom_id')
    members = Column(JSON, nullable=False, default=list, comment='members')
    llm_thread_id = Column(JSON, nullable=False, default=lambda: {}, comment='llm_thread_id')
    member_count = Column(Integer, nullable=False, default=0, comment='member_count')
    small_head_img_url = Column(String(255), nullable=False, default="", comment='small_head_img_url')
    ai_enabled = Column(Boolean, nullable=False, default=False, comment='ai_enabled')
    
class OfficialAccount(Base):
    __tablename__ = 'official_account'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='id')
    wxid = Column(String(20), nullable=False, unique=True, index=True,
                  comment='wxid')
    name = Column(String(50), nullable=False, default="", comment='name')
    small_head_img_url = Column(String(255), nullable=True, default="", comment='small_head_img_url')
    last_message = Column(String(255), nullable=True, default="", comment='last_message')
    last_message_time = Column(DateTime, nullable=True, default=datetime.datetime.fromtimestamp(0), comment='last_message_time')
    need_real_time = Column(Boolean, nullable=True, default=False, comment='need_real_time')
    fake_id = Column(String(255), nullable=True, default="", comment='fake_id')

class Subscription(Base):
    __tablename__ = 'subscription'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='订阅ID')
    user_wxid = Column(String(20), nullable=False, index=True, autoincrement=False, comment='wxid')
    gh_wxid = Column(String(50), nullable=False, default="", comment='gh_wxid')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.datetime.now(), comment='created_at')

class Config(Base):
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='配置ID')
    plugin_name = Column(String(50), nullable=False, unique=True, index=True, comment='插件名称')
    config_data = Column(JSON, nullable=False, default=lambda: {}, comment='配置数据')
    last_modified = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='最后修改时间')


class XYBotDB(metaclass=Singleton):
    def __init__(self):
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        self.database_url = main_config["XYBot"]["XYBotDB-url"]
        self.engine = create_engine(self.database_url)
        self.DBSession = sessionmaker(bind=self.engine)

        # 创建表
        Base.metadata.create_all(self.engine)
        logger.success("数据库初始化成功")

        # 初始化配置数据
        self._init_config_data()

        # 创建线程池执行器
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="database")

    def _init_config_data(self):
        """初始化配置表数据"""
        session = self.DBSession()
        try:
            # Dify插件初始配置
            dify_config = {
                "enable": False,
                "api-key": "app-HOCPuTnVuv7HO2AccaBnFjIo",
                "base-url": "https://api.dify.ai/v1",
                "commands": ["ai", "dify", "聊天", "AI"],
                "command-tip": "💬AI聊天指令：\n聊天 请求内容",
                "price": 0,
                "admin_ignore": True,
                "whitelist_ignore": True,
                "http-proxy": ""
            }
            if not session.query(Config).filter_by(plugin_name="Dify").first():
                config = Config(plugin_name="Dify", config_data=dify_config)
                session.add(config)

            # 获取联系人插件初始配置
            get_contact_config = {
                "enable": True,
                "command": ["获取联系人", "联系人", "通讯录", "获取通讯录"]
            }
            if not session.query(Config).filter_by(plugin_name="GetContact").first():
                config = Config(plugin_name="GetContact", config_data=get_contact_config)
                session.add(config) 
            # 好友欢迎插件初始配置
            friend_welcome_config = {
                "enable": False,
                "welcome-message": "你好"
            }
            if not session.query(Config).filter_by(plugin_name="FriendWelcome").first():
                config = Config(plugin_name="FriendWelcome", config_data=friend_welcome_config)
                session.add(config)
            # 关键词回复插件初始配置
            keyword_reply_config = {
                "enable": False,
                "keyword": {
                    "你好": "你好"
                }
            }
            if not session.query(Config).filter_by(plugin_name="KeywordReply").first():
                config = Config(plugin_name="KeywordReply", config_data=keyword_reply_config)
                session.add(config)
            session.commit()
            logger.info("数据库: 成功初始化配置表数据")
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 初始化配置表数据失败, 错误: {e}")
        finally:
            session.close()

    def _execute_in_queue(self, method, *args, **kwargs):
        """在队列中执行数据库操作"""
        future = self.executor.submit(method, *args, **kwargs)
        try:
            return future.result(timeout=20)  # 20秒超时
        except Exception as e:
            logger.error(f"数据库操作失败: {method.__name__} - {str(e)}")
            raise

    # USER
    def get_users_count(self) -> int:
        """获取用户总数"""
        session = self.DBSession()
        try:
            return session.query(User).count()
        except Exception as e:
            logger.error(f"数据库: 获取用户总数失败, 错误: {e}")
            return 0
        finally:
            session.close()
            
    

    def save_or_update_contact(self, user: User) -> bool:
        """保存或更新联系人信息"""
        session = self.DBSession()
        try:
            existing_user = session.query(User).filter_by(wxid=user.wxid).first()
            if not existing_user:
                session.add(user)
            else:
                existing_user.nickname = user.nickname
                existing_user.remark = user.remark
                existing_user.wx_num = user.wx_num
                existing_user.small_head_img_url = user.small_head_img_url
            session.commit()
            logger.info(f"数据库: 成功保存或更新联系人{user.nickname}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存或更新联系人{user.wxid}失败, 错误: {e}")
            return False
        finally:
            session.close()
    def get_user_by_wxid(self, wxid: str) -> User:
        """获取联系人信息"""
        session = self.DBSession()
        try:
            return session.query(User).filter_by(wxid=wxid).first()
        except Exception as e:
            logger.error(f"数据库: 获取联系人{wxid}失败, 错误: {e}")
            return None
        finally:
            session.close()
    def save_or_update_official_account(self, official_account: OfficialAccount) -> bool:
        """保存或更新公众号信息"""
        session = self.DBSession()
        try:
            existing_official_account = session.query(OfficialAccount).filter_by(wxid=official_account.wxid).first()
            if not existing_official_account:
                session.add(official_account)
            else:
                existing_official_account.name = official_account.name
                existing_official_account.small_head_img_url = official_account.small_head_img_url
            session.commit()
            logger.info(f"数据库: 成功保存或更新公众号{official_account.name}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存或更新公众号{official_account.wxid}失败, 错误: {e}")
            return False
        finally:
            session.close()

    def save_or_update_chatroom(self, chatroom: Chatroom) -> bool:
        """保存或更新群聊信息"""
        session = self.DBSession()
        try:
            existing_chatroom = session.query(Chatroom).filter_by(chatroom_id=chatroom.chatroom_id).first()
            if not existing_chatroom:
                session.add(chatroom)
            else:
                existing_chatroom.members = chatroom.members    
                existing_chatroom.member_count = chatroom.member_count
                existing_chatroom.small_head_img_url = chatroom.small_head_img_url
            session.commit()
            logger.info(f"数据库: 成功保存或更新群聊{chatroom.name}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存或更新群聊{chatroom.chatroom_id}失败, 错误: {e}")
            return False
        finally:
            session.close()

    def add_points(self, wxid: str, num: int) -> bool:
        """Thread-safe point addition"""
        return self._execute_in_queue(self._add_points, wxid, num)

    def _add_points(self, wxid: str, num: int) -> bool:
        """Thread-safe point addition"""
        session = self.DBSession()
        try:
            # Use UPDATE with atomic operation
            result = session.execute(
                update(User)
                .where(User.wxid == wxid)
                .values(points=User.points + num)
            )
            if result.rowcount == 0:
                # User doesn't exist, create new
                user = User(wxid=wxid, points=num)
                session.add(user)
            logger.info(f"数据库: 用户{wxid}积分增加{num}")
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据库: 用户{wxid}积分增加失败, 错误: {e}")
            return False
        finally:
            session.close()

    def set_points(self, wxid: str, num: int) -> bool:
        """Thread-safe point setting"""
        return self._execute_in_queue(self._set_points, wxid, num)

    def _set_points(self, wxid: str, num: int) -> bool:
        """Thread-safe point setting"""
        session = self.DBSession()
        try:
            result = session.execute(
                update(User)
                .where(User.wxid == wxid)
                .values(points=num)
            )
            if result.rowcount == 0:
                user = User(wxid=wxid, points=num)
                session.add(user)
            logger.info(f"数据库: 用户{wxid}积分设置为{num}")
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据库: 用户{wxid}积分设置失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_points(self, wxid: str) -> int:
        """Get user points"""
        return self._execute_in_queue(self._get_points, wxid)

    def _get_points(self, wxid: str) -> int:
        """Get user points"""
        session = self.DBSession()
        try:
            user = session.query(User).filter_by(wxid=wxid).first()
            return user.points if user else 0
        finally:
            session.close()

    def get_signin_stat(self, wxid: str) -> datetime.datetime:
        """获取用户签到状态"""
        return self._execute_in_queue(self._get_signin_stat, wxid)

    def _get_signin_stat(self, wxid: str) -> datetime.datetime:
        session = self.DBSession()
        try:
            user = session.query(User).filter_by(wxid=wxid).first()
            return user.signin_stat if user else datetime.datetime.fromtimestamp(0)
        finally:
            session.close()

    def set_signin_stat(self, wxid: str, signin_time: datetime.datetime) -> bool:
        """Thread-safe set user's signin time"""
        return self._execute_in_queue(self._set_signin_stat, wxid, signin_time)

    def _set_signin_stat(self, wxid: str, signin_time: datetime.datetime) -> bool:
        session = self.DBSession()
        try:
            result = session.execute(
                update(User)
                .where(User.wxid == wxid)
                .values(
                    signin_stat=signin_time,
                    signin_streak=User.signin_streak
                )
            )
            if result.rowcount == 0:
                user = User(
                    wxid=wxid,
                    signin_stat=signin_time,
                    signin_streak=0
                )
                session.add(user)
            logger.info(f"数据库: 用户{wxid}登录时间设置为{signin_time}")
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据库: 用户{wxid}登录时间设置失败, 错误: {e}")
            return False
        finally:
            session.close()

    def reset_all_signin_stat(self) -> bool:
        """Reset all users' signin status"""
        session = self.DBSession()
        try:
            session.query(User).update({User.signin_stat: datetime.datetime.fromtimestamp(0)})
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 重置所有用户登录时间失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_leaderboard(self, count: int) -> list:
        """Get points leaderboard"""
        session = self.DBSession()
        try:
            users = session.query(User).order_by(User.points.desc()).limit(count).all()
            return [(user.wxid, user.points) for user in users]
        finally:
            session.close()

    def set_whitelist(self, wxid: str, stat: bool) -> bool:
        """Set user's whitelist status"""
        session = self.DBSession()
        try:
            user = session.query(User).filter_by(wxid=wxid).first()
            if not user:
                user = User(wxid=wxid)
                session.add(user)
            user.whitelist = stat
            session.commit()
            logger.info(f"数据库: 用户{wxid}白名单状态设置为{stat}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 用户{wxid}白名单状态设置失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_whitelist(self, wxid: str) -> bool:
        """Get user's whitelist status"""
        session = self.DBSession()
        try:
            user = session.query(User).filter_by(wxid=wxid).first()
            return user.whitelist if user else False
        finally:
            session.close()

    def get_whitelist_list(self) -> list:
        """Get list of all whitelisted users"""
        session = self.DBSession()
        try:
            users = session.query(User).filter_by(whitelist=True).all()
            return [user.wxid for user in users]
        finally:
            session.close()

    def safe_trade_points(self, trader_wxid: str, target_wxid: str, num: int) -> bool:
        """Thread-safe points trading between users"""
        return self._execute_in_queue(self._safe_trade_points, trader_wxid, target_wxid, num)

    def _safe_trade_points(self, trader_wxid: str, target_wxid: str, num: int) -> bool:
        """Thread-safe points trading between users"""
        session = self.DBSession()
        try:
            # Start transaction with row-level locking
            trader = session.query(User).filter_by(wxid=trader_wxid) \
                .with_for_update().first()  # Acquire row lock
            target = session.query(User).filter_by(wxid=target_wxid) \
                .with_for_update().first()  # Acquire row lock

            if not trader:
                trader = User(wxid=trader_wxid)
                session.add(trader)
            if not target:
                target = User(wxid=target_wxid)
                session.add(target)
                session.flush()  # Ensure IDs are generated

            if trader.points >= num:
                trader.points -= num
                target.points += num
                session.commit()
                logger.info(f"数据库: 用户{trader_wxid}给用户{target_wxid}转账{num}积分")
                return True
            logger.info(f"数据库: 转账失败, 用户{trader_wxid}积分不足")
            session.rollback()
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据库: 转账失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_user_list(self) -> list:
        """Get list of all users"""
        session = self.DBSession()
        try:
            users = session.query(User).all()
            return [user.wxid for user in users]
        finally:
            session.close()

    def get_llm_thread_id(self, wxid: str, namespace: str = None) -> Union[dict, str]:
        """Get LLM thread id for user or chatroom"""
        session = self.DBSession()
        try:
            # Check if it's a chatroom ID
            if wxid.endswith("@chatroom"):
                chatroom = session.query(Chatroom).filter_by(chatroom_id=wxid).first()
                if namespace:
                    return chatroom.llm_thread_id.get(namespace, "") if chatroom else ""
                else:
                    return chatroom.llm_thread_id if chatroom else {}
            else:
                # Regular user
                user = session.query(User).filter_by(wxid=wxid).first()
                if namespace:
                    return user.llm_thread_id.get(namespace, "") if user else ""
                else:
                    return user.llm_thread_id if user else {}
        finally:
            session.close()

    def save_llm_thread_id(self, wxid: str, data: str, namespace: str) -> bool:
        """Save LLM thread id for user or chatroom"""
        session = self.DBSession()
        try:
            if wxid.endswith("@chatroom"):
                chatroom = session.query(Chatroom).filter_by(chatroom_id=wxid).first()
                if not chatroom:
                    chatroom = Chatroom(
                        chatroom_id=wxid,
                        llm_thread_id={}
                    )
                    session.add(chatroom)
                # 创建新字典并更新
                new_thread_ids = dict(chatroom.llm_thread_id or {})
                new_thread_ids[namespace] = data
                chatroom.llm_thread_id = new_thread_ids
            else:
                user = session.query(User).filter_by(wxid=wxid).first()
                if not user:
                    user = User(
                        wxid=wxid,
                        llm_thread_id={}
                    )
                    session.add(user)
                # 创建新字典并更新
                new_thread_ids = dict(user.llm_thread_id or {})
                new_thread_ids[namespace] = data
                user.llm_thread_id = new_thread_ids

            session.commit()
            logger.info(f"数据库: 成功保存 {wxid} 的 llm thread id")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存用户llm thread id失败, 错误: {e}")
            return False
        finally:
            session.close()

    def delete_all_llm_thread_id(self):
        """Clear llm thread id for everyone"""
        session = self.DBSession()
        try:
            session.query(User).update({User.llm_thread_id: {}})
            session.query(Chatroom).update({Chatroom.llm_thread_id: {}})
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 清除所有用户llm thread id失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_signin_streak(self, wxid: str) -> int:
        """Thread-safe get user's signin streak"""
        return self._execute_in_queue(self._get_signin_streak, wxid)

    def _get_signin_streak(self, wxid: str) -> int:
        session = self.DBSession()
        try:
            user = session.query(User).filter_by(wxid=wxid).first()
            return user.signin_streak if user else 0
        finally:
            session.close()

    def set_signin_streak(self, wxid: str, streak: int) -> bool:
        """Thread-safe set user's signin streak"""
        return self._execute_in_queue(self._set_signin_streak, wxid, streak)

    def _set_signin_streak(self, wxid: str, streak: int) -> bool:
        session = self.DBSession()
        try:
            result = session.execute(
                update(User)
                .where(User.wxid == wxid)
                .values(signin_streak=streak)
            )
            if result.rowcount == 0:
                user = User(wxid=wxid, signin_streak=streak)
                session.add(user)
            logger.info(f"数据库: 用户{wxid}连续签到天数设置为{streak}")
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"数据库: 用户{wxid}连续签到天数设置失败, 错误: {e}")
            return False
        finally:
            session.close()

    # CHATROOM

    def get_chatroom_list(self) -> list:
        """Get list of all chatrooms"""
        session = self.DBSession()
        try:
            chatrooms = session.query(Chatroom).all()
            return [chatroom.chatroom_id for chatroom in chatrooms]
        finally:
            session.close()

    def get_chatroom_members(self, chatroom_id: str) -> set:
        """Get members of a chatroom"""
        session = self.DBSession()
        try:
            chatroom = session.query(Chatroom).filter_by(chatroom_id=chatroom_id).first()
            return set(chatroom.members) if chatroom else set()
        finally:
            session.close()

    def set_chatroom_members(self, chatroom_id: str, members: set) -> bool:
        """Set members of a chatroom"""
        session = self.DBSession()
        try:
            chatroom = session.query(Chatroom).filter_by(chatroom_id=chatroom_id).first()
            if not chatroom:
                chatroom = Chatroom(chatroom_id=chatroom_id)
                session.add(chatroom)
            chatroom.members = list(members)  # Convert set to list for JSON storage
            logger.info(f"Database: Set chatroom {chatroom_id} members successfully")
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Database: Set chatroom {chatroom_id} members failed, error: {e}")
            return False
        finally:
            session.close()

    def get_chatroom_by_wxid(self, wxid: str) -> Chatroom:
        """获取群聊信息"""
        session = self.DBSession()
        try:
            return session.query(Chatroom).filter_by(chatroom_id=wxid).first()
        except Exception as e:
            logger.error(f"数据库: 获取群聊信息失败, 错误: {e}")
            return None
        finally:
            session.close()


    # CONFIG
    def get_config(self, plugin_name: str) -> dict:
        """Get config data for a plugin"""
        session = self.DBSession()
        try:
            config = session.query(Config).filter_by(plugin_name=plugin_name).first()
            return config.config_data if config else {}
        except Exception as e:
            logger.error(f"数据库: 获取 {plugin_name} 配置失败, 错误: {e}")
            return {}
        finally:
            session.close()

    def save_config(self, plugin_name: str, config_data: dict) -> bool:
        """保存插件配置"""
        session = self.DBSession()
        try:
            config = session.query(Config).filter_by(plugin_name=plugin_name).first()
            if not config:
                config = Config(plugin_name=plugin_name)
                session.add(config)
            config.config_data = config_data
            session.commit()
            logger.info(f"数据库: 成功保存 {plugin_name} 的配置")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存 {plugin_name} 配置失败, 错误: {e}")
            return False
        finally:
            session.close()

    def get_all_users(self) -> list[User]:
        """获取所有用户信息"""
        session = self.DBSession()
        try:
            users = session.query(User).all()
            return users
        finally:
            session.close()

    def get_all_chatrooms(self) -> list[Chatroom]:
        """获取所有群聊信息"""
        session = self.DBSession()
        try:
            chatrooms = session.query(Chatroom).all()
            return chatrooms
        finally:
            session.close()

    # OfficialAccount
    def get_official_account_by_wxid(self, wxid: str) -> OfficialAccount:
        """获取公众号信息"""
        session = self.DBSession()
        try:
            return session.query(OfficialAccount).filter_by(wxid=wxid).first()
        except Exception as e:
            logger.error(f"数据库: 获取公众号信息失败, 错误: {e}")
            return None
        finally:
            session.close()
    
    def update_official_account(self, official_account: OfficialAccount) -> bool:
        """更新公众号信息"""
        session = self.DBSession()
        try:
            session.merge(official_account)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 更新公众号信息失败, 错误: {e}")
            return False
        finally:
            session.close()

    def find_official_account_by_name(self, name: str) -> OfficialAccount:
        """根据名称查找公众号"""
        session = self.DBSession()
        try:
            return session.query(OfficialAccount).filter_by(name=name).first()
        except Exception as e:
            logger.error(f"数据库: 根据名称查找公众号失败, 错误: {e}")
            return None
        finally:
            session.close()
    

    def get_subscription_user(self, gh_wxid: str) -> list[Subscription]:
        """获取订阅用户"""
        session = self.DBSession()
        try:
            subscriptions = session.query(Subscription).filter_by(gh_wxid=gh_wxid).all()
            return subscriptions
        except SQLAlchemyError as e:
            logger.error("数据库: 获取订阅用户失败, SQLAlchemy错误: {}", str(e))
            return []
        except Exception as e:
            logger.error("数据库: 获取订阅用户失败, 未知错误: {}", str(e))
            return []
        finally:
            session.close()

    def save_subscription(self, user_wxid: str, gh_wxid: str) -> bool:
        """保存订阅关系"""
        session = self.DBSession()
        try:
            existing_subscription = session.query(Subscription).filter_by(user_wxid=user_wxid, gh_wxid=gh_wxid).first()
            if existing_subscription:
                logger.info(f"数据库: 订阅关系已存在, 跳过保存")
                return True 
            subscription = Subscription(user_wxid=user_wxid, gh_wxid=gh_wxid)
            session.add(subscription)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 保存订阅关系失败, 错误: {e}")
            return False
        finally:
            session.close()
            
    def delete_subscription(self, user_wxid: str, gh_wxid: str) -> bool:
        """删除订阅关系"""
        session = self.DBSession()
        try:
            session.query(Subscription).filter_by(user_wxid=user_wxid, gh_wxid=gh_wxid).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"数据库: 删除订阅关系失败, 错误: {e}")
            return False
        finally:
            session.close()

    def __del__(self):
        """确保关闭时清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        if hasattr(self, 'engine'):
            self.engine.dispose()
