from flask import Flask, render_template, jsonify, request, send_from_directory
# from WechatAPI import WechatAPIClient
import tomllib
import os
import asyncio
from datetime import datetime
from database.XYBotDB import XYBotDB

app = Flask(__name__, 
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    template_folder=os.path.join(os.path.dirname(__file__), "templates")
)

# 读取配置文件
def load_config():
    with open("main_config.toml", "rb") as f:
        config = tomllib.load(f)
    
    # 加载插件配置
    try:
        with open("plugins/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)
            config["Plugins"] = plugin_config
    except FileNotFoundError:
        config["Plugins"] = {}
    
    return config

# 获取机器人实例
def get_bot():
    config = load_config()
    # return WechatAPIClient(
    #     ip="127.0.0.1",
    #     port=config["WechatAPIServer"]["port"]
    # )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/contacts')
def get_contacts():
    db = XYBotDB()
    
    # 获取所有用户（好友）信息
    friends = []
    for user in db.get_all_users():
        if not user.wxid.endswith("@chatroom"):  # 排除群聊
            friends.append({
                "wxid": user.wxid,
                "nickname": user.nickname,
                "remark": user.remark,
                "wx_num": user.wx_num,
                "avatar": user.big_head_img_url,
                "type": "好友"
            })
    
    # 获取所有群聊信息
    groups = []
    for chatroom in db.get_all_chatrooms():
        members = db.get_chatroom_members(chatroom.chatroom_id)
        groups.append({
            "wxid": chatroom.chatroom_id,
            "nickname": chatroom.nickname if hasattr(chatroom, 'nickname') else "未知群聊",
            "member_count": len(members) if members else 0,
            "type": "群聊"
        })
    
    # 合并好友和群聊列表
    contacts = friends + groups
    return jsonify(contacts)

@app.route('/api/config')
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    new_config = request.json
    
    # 分离主配置和插件配置
    plugin_config = new_config.pop("Plugins", {})
    
    # 保存主配置
    with open("main_config.toml", "w", encoding="utf-8") as f:
        tomllib.dump(new_config, f)
    
    # 保存插件配置
    with open("plugins/config.toml", "w", encoding="utf-8") as f:
        tomllib.dump(plugin_config, f)
    
    return jsonify({"status": "success"})

@app.route('/api/plugins')
def get_plugins():
    plugins = []
    for item in os.listdir("plugins"):
        if os.path.isdir(os.path.join("plugins", item)) and not item.startswith("__"):
            plugins.append({
                "name": item,
                "enabled": item not in load_config()["XYBot"]["disabled-plugins"]
            })
    return jsonify(plugins)

@app.route('/api/status')
def get_status():
    try:
        config = load_config()
        return jsonify({
            "logged_in": True,  # 这里需要从bot实例获取真实状态
            "uptime": "运行中",  # 这里需要计算真实运行时间
            "message_count": 0  # 这里需要从数据库获取真实消息数量
        })
    except Exception as e:
        return jsonify({
            "logged_in": False,
            "uptime": "未知",
            "message_count": 0,
            "error": str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 