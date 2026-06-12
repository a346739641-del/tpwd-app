from flask import Flask, request, jsonify, render_template_string
import urllib.request, urllib.parse, json, re, os, hashlib, xml.etree.ElementTree as ET, time, threading

app = Flask(__name__)

LOGIN_URL = "https://www.apptimes.cn/login"
API_URL = "https://www.apptimes.cn/tool/tpwd-parse"
USERNAME = os.environ.get("TPWD_USER", "13332633249")
PASSWORD = os.environ.get("TPWD_PASS", "molin000")
APPKEY = os.environ.get("TPWD_APPKEY", "lr8kz1wq")
WX_TOKEN = os.environ.get("WX_TOKEN", "tpwd123")  # 公众号后台填的 Token

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

def login():
    req = urllib.request.Request(LOGIN_URL)
    resp = opener.open(req)
    html = resp.read().decode()
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    token = m.group(1) if m else ""
    data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD, "_token": token, "remember": "1"}).encode()
    req2 = urllib.request.Request(LOGIN_URL, data=data)
    resp2 = opener.open(req2)
    return json.loads(resp2.read()).get("code") == 0

login()

def refresh_session():
    threading.Timer(3600, refresh_session).start()
    try: login()
    except: pass
refresh_session()

def call_api(content):
    data = urllib.parse.urlencode({"content": content, "appkey": APPKEY}).encode()
    req = urllib.request.Request(API_URL, data=data)
    resp = opener.open(req)
    return json.loads(resp.read())

def parse_tpwd(content):
    try:
        res = call_api(content)
        if isinstance(res, list):
            login()
            res = call_api(content)
        if isinstance(res, dict) and res.get("code") == 0:
            url = res.get("data", {}).get("url", "")
            m = re.search(r"id=(\d+)", url)
            item_id = m.group(1) if m else None
            return item_id, url
        return None, None
    except:
        return None, None

def check_signature(signature, timestamp, nonce):
    arr = sorted([WX_TOKEN, timestamp, nonce])
    return hashlib.sha1("".join(arr).encode()).hexdigest() == signature

# ====== 公众号消息处理 ======
@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    if request.method == "GET":
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        if check_signature(signature, timestamp, nonce):
            return echostr
        return "验证失败"

    # POST - 接收用户消息
    xml_data = request.data
    root = ET.fromstring(xml_data)
    msg_type = root.findtext("MsgType")
    from_user = root.findtext("FromUserName")
    to_user = root.findtext("ToUserName")

    if msg_type == "text":
        content = root.findtext("Content", "").strip()
        if not content:
            reply = "请输入淘口令"
        else:
            item_id, url = parse_tpwd(content)
            if item_id:
                reply = f"商品ID: {item_id}\n\n完整链接: {url}"
            else:
                reply = "解析失败，请确认淘口令是否正确"

        xml_reply = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply}]]></Content>
</xml>"""
        return xml_reply, 200, {"Content-Type": "application/xml"}

    return ""

# ====== 原有网页入口 ======
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>淘口令解析</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,"Microsoft YaHei","PingFang SC",sans-serif;background:#f5f5f5;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:16px}
.container{background:#fff;border-radius:16px;padding:32px 24px;width:100%;max-width:460px;box-shadow:0 4px 30px rgba(0,0,0,0.06)}
h1{font-size:20px;color:#222;text-align:center;margin-bottom:4px}
.sub{text-align:center;color:#999;font-size:13px;margin-bottom:24px}
textarea{width:100%;height:110px;padding:14px;border:1.5px solid #e0e0e0;border-radius:12px;font-size:15px;line-height:1.5;resize:none;outline:none;font-family:inherit;background:#fafafa}
textarea:focus{border-color:#ff6a00;background:#fff}
.hint{text-align:center;margin-top:10px;font-size:12px;color:#aaa}
.hint span{background:#f0f0f0;padding:4px 14px;border-radius:20px}
.row{display:flex;gap:10px;margin-top:16px}
.btn{flex:1;padding:14px;border:none;border-radius:12px;font-size:16px;font-weight:500;cursor:pointer;text-align:center}
.btn-pri{background:#ff6a00;color:#fff}
.btn-pri:active{background:#e55e00}
.btn-pri:disabled{background:#ccc}
.btn-out{background:#fff;color:#666;border:1.5px solid #ddd}
.btn-out:active{background:#f5f5f5}
.loading{display:none;text-align:center;margin-top:20px;color:#999;font-size:14px}
.spinner{display:inline-block;width:18px;height:18px;border:2px solid #ddd;border-top-color:#ff6a00;border-radius:50%;animation:s .6s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes s{to{transform:rotate(360deg)}}
.err{display:none;margin-top:16px;padding:12px 16px;background:#fff0f0;border-radius:10px;color:#d32f2f;font-size:14px;border:1px solid #ffcdd2}
.res{display:none;margin-top:20px}
.card{background:#fafafa;border:1px solid #eee;border-radius:14px;overflow:hidden}
.id-box{text-align:center;padding:20px 18px;border-bottom:1px solid #f0f0f0}
.id-num{font-size:32px;font-weight:700;color:#ff6a00;letter-spacing:1px;cursor:pointer}
.id-lbl{font-size:12px;color:#999;margin-top:6px}
.id-cp{font-size:12px;color:#999;margin-top:8px}
.id-cp span{background:#f0f0f0;padding:3px 12px;border-radius:20px}
.r-item{display:flex;align-items:center;padding:14px 18px}
.r-lbl{font-size:12px;color:#999;width:70px;flex-shrink:0}
.r-val{font-size:14px;color:#333;word-break:break-all;flex:1;line-height:1.4}
.toast{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.75);color:#fff;padding:12px 24px;border-radius:10px;font-size:14px;z-index:999;pointer-events:none}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<div class="container">
<h1>淘口令解析</h1>
<p class="sub">自动提取商品数字ID</p>
<textarea id="content" placeholder="双击此处粘贴" readonly onfocus="this.removeAttribute('readonly')"></textarea>
<div class="hint"><span>双击输入框粘贴</span></div>
<div class="row">
<button class="btn btn-pri" id="btn" onclick="parse()">解析</button>
<button class="btn btn-out" onclick="clr()">清空</button>
</div>
<div class="loading" id="loading"><span class="spinner"></span> 解析中...</div>
<div class="err" id="err"></div>
<div class="res" id="res">
<div class="card">
<div class="id-box" onclick="cp()">
<div class="id-num" id="id">-</div>
<div class="id-lbl">商品数字ID（点击复制）</div>
<div class="id-cp"><span>点击数字即可复制</span></div>
</div>
<div class="r-item"><span class="r-lbl">链接</span><span class="r-val" id="url"></span></div>
</div>
</div>
</div>
<script>
var inp=document.getElementById("content");
inp.addEventListener("dblclick",function(){paste()});
inp.addEventListener("touchend",function(e){var n=Date.now();if(this.lastTap&&(n-this.lastTap)<400){e.preventDefault();paste();this.lastTap=0}else{this.lastTap=n}});
function paste(){if(navigator.clipboard&&navigator.clipboard.readText){navigator.clipboard.readText().then(function(t){if(t){inp.value=t;toast("已粘贴")}else{toast("剪贴板为空")}}).catch(function(){inp.value="";inp.focus();document.execCommand("paste")})}else{inp.value="";inp.focus();setTimeout(function(){try{document.execCommand("paste")}catch(e){toast("请手动粘贴")}},100)}}
function clr(){inp.value="";document.getElementById("res").style.display="none";document.getElementById("err").style.display="none";inp.focus()}
function parse(){var c=inp.value.trim();if(!c){toast("请输入淘口令");return}
var btn=document.getElementById("btn");btn.disabled=true;document.getElementById("loading").style.display="block";document.getElementById("err").style.display="none";document.getElementById("res").style.display="none"
fetch("/parse",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"content="+encodeURIComponent(c)}).then(function(r){return r.json()}).then(function(res){if(res.code===0){document.getElementById("id").textContent=res.item_id;document.getElementById("url").textContent=res.url;document.getElementById("res").style.display="block"}else{document.getElementById("err").textContent=res.msg;document.getElementById("err").style.display="block"}}).catch(function(e){document.getElementById("err").textContent="请求失败: "+e.message;document.getElementById("err").style.display="block"}).finally(function(){btn.disabled=false;document.getElementById("loading").style.display="none"})}
function cp(){var id=document.getElementById("id").textContent;if(!id||id==="-")return
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(id).then(function(){toast("已复制: "+id)}).catch(function(){fc(id)})}else{fc(id)}}
function fc(t){var ta=document.createElement("textarea");ta.value=t;ta.style.position="fixed";ta.style.opacity="0";document.body.appendChild(ta);ta.select();try{document.execCommand("copy");toast("已复制: "+t)}catch(e){toast("复制失败")};document.body.removeChild(ta)}
function toast(m){var t=document.getElementById("toast");t.textContent=m;t.style.display="block";clearTimeout(t._timer);t._timer=setTimeout(function(){t.style.display="none"},1500)}
</script>
</body>
</html>"""

# ====== 第三方平台 API 接口 ======
# 微擎、微信云托管等第三方平台可以调这个接口获取回复内容
# 请求: POST /api/reply, body: content=淘口令
# 返回: {"code":0, "reply":"商品ID: xxx\n\n链接: xxx"}
@app.route("/api/reply", methods=["POST"])
def api_reply():
    content = request.form.get("content", "") or request.args.get("content", "")
    if not content:
        return jsonify({"code": 1, "reply": "请输入淘口令"})
    try:
        item_id, url = parse_tpwd(content)
        if item_id:
            return jsonify({"code": 0, "reply": f"商品ID: {item_id}\n\n完整链接: {url}"})
        return jsonify({"code": 1, "reply": "解析失败，请确认淘口令是否正确"})
    except Exception as e:
        return jsonify({"code": 1, "reply": f"系统错误: {str(e)}"})

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/parse", methods=["POST"])
def parse():
    content = request.form.get("content", "")
    if not content:
        return jsonify({"code": 1, "msg": "请输入淘口令"})
    try:
        item_id, url = parse_tpwd(content)
        if item_id:
            return jsonify({"code": 0, "item_id": item_id, "url": url})
        return jsonify({"code": 1, "msg": "解析失败"})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
