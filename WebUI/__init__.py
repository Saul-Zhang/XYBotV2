import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Union

from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_session import Session
from flask_socketio import SocketIO
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log('WEBUI', record.getMessage())


def _configure_logging(app: Flask) -> None:
    # 清除Flask默认日志处理器并配置使用loguru
    app.logger.handlers = []
    app.logger.propagate = False
    app.logger.addHandler(InterceptHandler())

    # 同样为werkzeug日志配置loguru
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = []
    werkzeug_logger.propagate = False
    werkzeug_logger.addHandler(InterceptHandler())

def _setup_instance_directories(app: Flask) -> None:
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        logger.log('WEBUI', f"已创建实例目录: {app.instance_path}")
    except OSError as e:
        logger.log('WEBUI', f"创建实例目录失败: {e}")


def create_app() -> Tuple[Flask, SocketIO]:
    """创建并配置Flask应用实例及SocketIO实例
        
    Returns:
        tuple: 包含配置好的Flask应用实例和SocketIO实例
    """
    # 创建Flask应用，设置静态文件和模板路径
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')
    # 配置日志系统
    _configure_logging(app)

    logger.log('WEBUI', "正在初始化XYBotV2 WebUI应用...")

    # 加载配置
    app.config.from_pyfile(Path(__file__).resolve().parent / 'config.py')
    logger.log('WEBUI', "已加载WEBUI配置")

    # 确保实例文件夹存在
    _setup_instance_directories(app)


    # 初始化Flask-Session
    Session(app)

    # 初始化Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # 注册模板过滤器
    from .utils.template_filters import register_template_filters
    register_template_filters(app)

    # 注册蓝图
    from .routes import register_blueprints
    register_blueprints(app)
    logger.log('WEBUI', "已注册路由蓝图，模板过滤器")

    # 初始化WebSocket服务
    from .services.websocket_service import socketio, init_websocket

    # 配置socketio
    socketio_config = {
        'cors_allowed_origins': '*',  # 允许的跨域来源，生产环境应该更严格
        'async_mode': 'eventlet',  # 使用eventlet作为异步模式
        'logger': False,  # 禁用socketio日志
        'engineio_logger': False  # 禁用engineio日志
    }

    # 初始化socketio
    socketio.init_app(app, **socketio_config)
    logger.log('WEBUI', "已初始化会话管理，用户认证系统，SocketIO服务")

    # 启动WebSocket服务
    init_websocket()
    logger.log('WEBUI', "已启动WebSocket日志监控")

    # 注册全局上下文处理器
    @app.context_processor
    def inject_global_vars() -> Dict[str, Union[str, datetime]]:
        """为所有模板注入全局变量
        
        Returns:
            包含全局变量的字典
        """
        return {
            'app_name': 'XYBotV2 WebUI',
            'version': '1.0.0',
            'now': datetime.now()
        }

    # 定义用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        pass

    # 简单的首页路由（重定向到概览页）
    @app.route('/')
    def index():
        """应用首页路由处理，重定向到概览页"""
        return redirect(url_for('overview.index'))

    logger.log('WEBUI', "XYBotV2 WebUI应用初始化完成")
    return app, socketio
