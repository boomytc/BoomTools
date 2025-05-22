from flask import Flask, render_template, jsonify, request
import time

app = Flask(__name__)

# 要生成的文本
FULL_TEXT = """在那遥远的维罗纳城邦，两个同样尊贵的家族，
因宿怨长存而再起纷争，血染古城墙。
命运的双星从这对世仇诞生，
一对恋人以死亡终结了父辈的仇恨。
他们悲剧性的爱情与父母的愤怒，
唯有他们的死亡才能平息这场争端，
这便是我们今日为您呈现的故事，
请静心聆听，我们将在这舞台上重现。
在这古老的街道上，荣誉与剑相伴，
年轻的心灵在命运的指引下相遇。
当朱丽叶的眼眸遇见罗密欧的凝视，
世间再无比这更纯粹的爱情。
然而命运弄人，他们的相爱注定坎坷，
家族的仇恨如高墙般将他们阻隔。
但爱情啊，它超越了所有的界限，
即使是死亡也无法将其消散。
请听这悲伤的故事，关于爱与恨，
关于生与死，关于和解与遗憾。
在这两个小时的旅程中，我们将展示，
那永恒的爱情如何战胜了一切。"""

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/text', methods=['GET'])
def get_text():
    """API端点，用于获取单个字符"""
    # 获取请求参数
    index = int(request.args.get('index', 0))

    # 确保索引在有效范围内
    if index >= len(FULL_TEXT):
        return jsonify({"text": "", "done": True})

    # 返回单个字符
    return jsonify({
        "text": FULL_TEXT[index],
        "done": index >= len(FULL_TEXT) - 1
    })

@app.route('/api/text_chunk', methods=['GET'])
def get_text_chunk():
    """API端点，用于获取文本块"""
    # 获取请求参数
    index = int(request.args.get('index', 0))
    chunk_size = int(request.args.get('chunk_size', 50))  # 默认获取50个字符

    # 确保索引在有效范围内
    if index >= len(FULL_TEXT):
        return jsonify({"text": "", "done": True})

    # 计算实际可获取的字符数量
    end_index = min(index + chunk_size, len(FULL_TEXT))

    # 返回文本块
    return jsonify({
        "text": FULL_TEXT[index:end_index],
        "done": end_index >= len(FULL_TEXT)
    })

@app.route('/api/full_text', methods=['GET'])
def get_full_text():
    """API端点，用于获取完整文本（用于调试）"""
    return jsonify({"text": FULL_TEXT, "length": len(FULL_TEXT)})

# 多语言支持
@app.route('/api/translations', methods=['GET'])
def get_translations():
    """API端点，用于获取界面翻译"""
    lang = request.args.get('lang', 'zh')

    translations = {
        'zh': {
            'title': 'Token 生成速度可视化',
            'subtitle': '实时体验不同的 token 生成速度',
            'speedLabel': '生成速度',
            'rangeLabel': '范围',
            'slow': '慢',
            'medium': '中等',
            'fast': '快',
            'startButton': '开始生成'
        },
        'en': {
            'title': 'Token Generation Speed Visualizer',
            'subtitle': 'Experience different token generation speeds in real-time',
            'speedLabel': 'Generation Speed',
            'rangeLabel': 'Range',
            'slow': 'Slow',
            'medium': 'Medium',
            'fast': 'Fast',
            'startButton': 'Start Generation'
        }
    }

    return jsonify(translations.get(lang, translations['en']))

if __name__ == '__main__':
    app.run(debug=True)
