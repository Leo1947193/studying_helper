# config.py
import os
from dotenv import load_dotenv

load_dotenv() # 加载.env文件中的环境变量

# DeepSeek API 配置
# 请确保你的API Key是安全的，生产环境中建议使用环境变量
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat" # 或者其他你选择的DeepSeek模型，如 deepseek-v2

# 数据文件路径
TEMPLATES_FILE = "templates_methods.json"
