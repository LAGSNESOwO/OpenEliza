import time
import uuid
import os
import pickle
from flask import Flask, request, jsonify
from eliza import Eliza

app = Flask(__name__)

# 会话存储目录
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# 保存会话到文件
def save_session(session_id, eliza_instance):
    try:
        with open(f"{SESSIONS_DIR}/{session_id}.pkl", "wb") as f:
            pickle.dump(eliza_instance, f)
    except Exception as e:
        app.logger.error(f"Error saving session: {e}")

# 从文件加载会话
def load_session(session_id):
    try:
        with open(f"{SESSIONS_DIR}/{session_id}.pkl", "rb") as f:
            return pickle.load(f)
    except:
        return None

# 添加中文规则扩展
def add_chinese_rules(eliza_instance):
    # 添加基本中文规则
    chinese_rules = {
        "你好": ["你好！我是ELIZA，很高兴和你交谈。", "你好，有什么我可以帮助你的吗？"],
        "难过": ["你为什么感到难过？", "是什么让你感到难过？", "你经常这样难过吗？"],
        "开心": ["你为什么感到开心？", "继续分享让你开心的事情吧。", "是什么让你这么开心？"],
        "我感觉": ["为什么你会{0}？", "从什么时候开始你{0}？", "当你{0}时，你会怎么做？"],
        "我想": ["为什么你想{0}？", "你真的希望{0}吗？", "如果你能{0}，会怎么样？"],
        "我需要": ["为什么你需要{0}？", "{0}对你有多重要？", "如果你得不到{0}呢？"],
        "我是": ["你为什么认为你是{0}？", "你喜欢做一个{0}吗？", "你已经是{0}多久了？"],
        "我": ["为什么你{0}？", "能告诉我更多关于你{0}的事情吗？", "这让你感觉如何？"],
        "为什么": ["你为什么想知道{0}？", "你认为{0}的原因是什么？", "这对你来说重要吗？"],
        "因为": ["这真的是原因吗？", "还有其他原因吗？", "这个原因能解释其他事情吗？"],
        "抱歉": ["道歉不必要。", "什么让你觉得需要道歉？", "我能理解你的感受。"],
        "梦想": ["你经常做梦吗？", "你的梦境告诉你什么？", "你记得其他梦吗？"],
        "也许": ["你似乎不太确定？", "为什么会有这种不确定？", "你不确定的原因是什么？"],
        "你": ["我们在讨论你，不是我。", "为什么你关心我{0}？", "这是你真正想了解的吗？"],
        "总是": ["真的总是吗？", "你能想到一个特例吗？", "什么情况下不是这样？"],
        "思考": ["你经常思考这些问题吗？", "思考这个问题对你有什么帮助？"],
        "相同": ["以什么方式相同？", "你能想到其他例子吗？", "有什么区别吗？"],
        "朋友": ["你的朋友对你意味着什么？", "你为什么提到朋友？", "你是否依赖你的朋友？"],
        "电脑": ["你为什么提到电脑？", "你认为机器有什么问题？", "你觉得我是一个机器人吗？"],
        "是的": ["你似乎很确定。", "你能详细解释一下吗？", "我明白了。"],
        "不": ["为什么不？", "你真的不确定吗？", "是什么让你否定这个？"],
        "失败": ["为什么你认为这是失败的？", "你是否经常失败？", "失败意味着什么？"]
    }
    
    eliza_instance.keys.update(chinese_rules)
    return eliza_instance

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completion():
    data = request.json
    
    # 获取请求参数
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.7)  # 仅为API兼容性
    
    # 获取会话ID或创建新的
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    # 创建或获取ELIZA实例
    eliza_instance = load_session(session_id)
    if not eliza_instance:
        eliza_instance = Eliza()
        eliza_instance.load()
        eliza_instance = add_chinese_rules(eliza_instance)
    
    # 提取用户最后的消息
    user_message = ""
    for message in reversed(messages):
        if message['role'] == 'user':
            user_message = message['content']
            break
    
    if not user_message:
        return jsonify({"error": "No user message found"}), 400
    
    # 获取ELIZA响应
    eliza_response = eliza_instance.respond(user_message)
    
    # 保存会话状态
    save_session(session_id, eliza_instance)
    
    # 构建OpenAI格式的响应
    response = {
        "id": f"chatcmpl-{str(uuid.uuid4())[:10]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "eliza-simulator",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": eliza_response
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_message),
            "completion_tokens": len(eliza_response),
            "total_tokens": len(user_message) + len(eliza_response)
        },
        "session_id": session_id  # 返回会话ID便于后续使用
    }
    
    return jsonify(response)

@app.route('/', methods=['GET'])
def home():
    return """
    <html>
    <head><title>ELIZA API</title></head>
    <body>
        <h1>ELIZA API 运行中</h1>
        <p>这是一个模拟经典ELIZA聊天机器人的API服务。</p>
        <p>使用 <code>/v1/chat/completions</code> 端点发送POST请求进行交互。</p>
        <h2>示例请求格式:</h2>
        <pre>
{
  "model": "eliza-simulator",
  "messages": [{"role": "user", "content": "我今天感到很难过"}],
  "temperature": 0.7
}
        </pre>
    </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()})

# 清理过期会话的函数 (如果需要可以添加定时任务)
def cleanup_old_sessions(max_age_hours=24):
    current_time = time.time()
    try:
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.pkl'):
                file_path = os.path.join(SESSIONS_DIR, filename)
                # 检查文件修改时间
                if (current_time - os.path.getmtime(file_path)) > (max_age_hours * 3600):
                    os.remove(file_path)
    except Exception as e:
        app.logger.error(f"Error cleaning up sessions: {e}")

if __name__ == '__main__':
    # 获取PORT环境变量，适配云平台
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
