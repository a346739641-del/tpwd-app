from flask import Flask, request, jsonify, render_template_string, make_response
import urllib.request, urllib.parse, json, re, os, hashlib, xml.etree.ElementTree as ET, time, threading

app = Flask(__name__)

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

LOGIN_URL = "https://www.apptimes.cn/login"
API_URL = "https://www.apptimes.cn/tool/tpwd-parse"
USERNAME = os.environ.get("TPWD_USER", "13332633249")
PASSWORD = os.environ.get("TPWD_PASS", "molin000")
APPKEY = os.environ.get("TPWD_APPKEY", "lr8kz1wq")
WX_TOKEN = os.environ.get("WX_TOKEN", "tpwd123")

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
opener.addheaders = [("User-Agent", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36"),
    ("Accept", "application/json, text/plain, */*"),
    ("X-Requested-With", "XMLHttpRequest")]

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
            data = res.get("data")
            if isinstance(data, dict):
                url = data.get("url", "")
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                url = data[0].get("url", "")
            else:
                return None, None
            m = re.search(r"itemIds=(\d+)", url) or re.search(r"(?:\?|&)id=(\d+)", url)
            item_id = m.group(1) if m else None
            return item_id, url
        return None, None
    except:
        return None, None

def check_signature(signature, timestamp, nonce):
    arr = sorted([WX_TOKEN, timestamp, nonce])
    return hashlib.sha1("".join(arr).encode()).hexdigest() == signature

# ====== 公众号 ======
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

# ====== API ======
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

@app.route("/parse", methods=["POST", "OPTIONS"])
def parse():
    if request.method == "OPTIONS":
        resp = make_response("")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp
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

# ====== PWA 图标 ======
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#e8894a"/><stop offset="100%" stop-color="#d6743a"/></linearGradient></defs>
<rect width="512" height="512" rx="100" fill="url(#g)"/>
<text x="256" y="320" text-anchor="middle" font-size="280" font-weight="bold" font-family="sans-serif" fill="#fff">淘</text>
</svg>"""

@app.route("/icon.svg")
def icon_svg():
    r = make_response(ICON_SVG)
    r.headers["Content-Type"] = "image/svg+xml"
    return r

@app.route("/icon-192.png")
def icon_192():
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="38" fill="#d6743a"/><text x="96" y="124" text-anchor="middle" font-size="100" font-weight="bold" fill="#fff" font-family="sans-serif">淘</text></svg>', 200, {"Content-Type": "image/svg+xml"}

@app.route("/icon-512.png")
def icon_512():
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="100" fill="#d6743a"/><text x="256" y="320" text-anchor="middle" font-size="280" font-weight="bold" fill="#fff" font-family="sans-serif">淘</text></svg>', 200, {"Content-Type": "image/svg+xml"}

# ====== manifest.json ======
@app.route("/manifest.json")
def manifest():
    m = {
        "name": "淘口令解析",
        "short_name": "淘口令",
        "description": "自动提取淘口令中的商品数字ID",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#fdf6ed",
        "theme_color": "#d6743a",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/svg+xml"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}
        ]
    }
    return jsonify(m)

# ====== service-worker.js ======
SW_JS = """self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method === 'POST') return;
  e.respondWith(
    caches.open('tpwd-v1').then(c => c.match(e.request).then(r => r || fetch(e.request)))
  );
});
"""

@app.route("/service-worker.js")
def sw():
    r = make_response(SW_JS)
    r.headers["Content-Type"] = "application/javascript"
    r.headers["Cache-Control"] = "no-cache"
    return r

# ====== PWA 首页 ======
PWA_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/icon-192.png">
<meta name="theme-color" content="#d6743a">
<title>淘口令解析</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{height:100%;background:#fcf3e9;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.page{height:100vh;position:relative}
.bg-layer{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;background:linear-gradient(160deg,#fdf6ed,#fef9f0);pointer-events:none}
.orb{position:absolute;border-radius:50%;opacity:0.18}
.o1{width:180px;height:180px;background:radial-gradient(circle,#f5cba0,transparent 70%);top:-30px;left:10%;animation:float 7s ease-in-out infinite}
.o2{width:120px;height:120px;background:radial-gradient(circle,#f0b27a,transparent 70%);bottom:20%;right:8%;animation:float 9s ease-in-out infinite 1s}
.o3{width:80px;height:80px;background:radial-gradient(circle,#e8b87a,transparent 70%);top:40%;left:70%;animation:float 6s ease-in-out infinite 0.5s}
.o4{width:150px;height:150px;background:radial-gradient(circle,#f2d1a8,transparent 70%);bottom:-20px;left:15%;animation:float 10s ease-in-out infinite 2s}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-18px)}}
.main{position:relative;z-index:1;display:flex;flex-direction:column;height:100vh}
.msg-list{flex:1;padding:16px 14px 10px;overflow-y:auto;overflow-x:hidden;box-sizing:border-box;-webkit-overflow-scrolling:touch}
.msg-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding-top:40%}
.msg-empty-icon{font-size:44px;margin-bottom:12px}
.msg-empty-text{font-size:14px;color:#ccb8a8}
.msg-row{width:100%;margin-bottom:16px;animation:msgIn .3s ease}
@keyframes msgIn{from{opacity:0;transform:translateY(10px)}}
.msg-right{display:flex;justify-content:flex-end}
.msg-left{display:flex;justify-content:flex-start}
.bubble{max-width:75%;padding:10px 14px;font-size:15px;line-height:1.5;word-break:break-all;position:relative}
.bubble-user{background:#d6743a;color:#fff;border-radius:12px 4px 12px 12px;box-shadow:0 2px 8px rgba(214,116,58,0.15)}
.bubble-bot{background:#fff;color:#3d2a1a;border-radius:4px 12px 12px 12px;box-shadow:0 1px 6px rgba(180,120,60,0.06);border:1px solid #f5ede6}
.bubble-error{color:#c0392b}
.bot-label{font-size:11px;color:#b8a08c;margin-bottom:2px;letter-spacing:1px}
.bot-id{font-size:26px;font-weight:700;color:#d6743a;letter-spacing:2px;line-height:1.3;cursor:pointer}
.bot-id:active{opacity:0.7}
.bot-copy{font-size:11px;color:#dcc8b8;margin-top:8px;padding-top:8px;border-top:1px solid #f0e8e0;text-align:center;cursor:pointer}
.input-bar{padding:10px 12px 16px;background:rgba(255,255,255,0.88);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-top:1px solid #eee}
.input{width:100%;min-height:110px;max-height:200px;border:none;font-size:16px;line-height:1.6;color:#3d2a1a;background:#f5f0ea;border-radius:12px;padding:14px;box-sizing:border-box;font-family:inherit;resize:none;outline:none}
.input::placeholder{color:#ccb8a8}
.btn{width:100%;height:42px;line-height:42px;margin:10px 0 0;background:linear-gradient(135deg,#e8894a,#d6743a);color:#fff;border-radius:10px;font-size:16px;text-align:center;border:none;cursor:pointer}
.btn:active{opacity:0.8}
.btn:disabled{opacity:0.4}
.toast{position:fixed;top:40%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:#fff;padding:10px 24px;border-radius:12px;font-size:14px;z-index:999;pointer-events:none;display:none;white-space:nowrap}
</style>
</head>
<body>
<div class="page">
<div class="bg-layer"></div>
<div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div><div class="orb o4"></div>
<div class="main">
  <div class="msg-list" id="msgList">
    <div class="msg-empty" id="empty">
      <div class="msg-empty-icon">☀️</div>
      <div class="msg-empty-text">双击下方输入框粘贴淘口令</div>
    </div>
  </div>
  <div class="input-bar">
    <textarea class="input" id="input" placeholder="双击粘贴淘口令..." maxlength="500"></textarea>
    <button class="btn" id="btn" onclick="send()">发送</button>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
const $=s=>document.querySelector(s)
const msgList=$('#msgList'),input=$('#input'),btn=$('#btn'),empty=$('#empty')
let lastTap=0
input.addEventListener('touchend',e=>{const n=Date.now();if(lastTap&&n-lastTap<350){e.preventDefault();lastTap=0;paste()}else{lastTap=n}})
input.addEventListener('dblclick',paste)
async function paste(){try{const t=await navigator.clipboard.readText();if(t){input.value=t;showToast('已粘贴')}}catch{showToast('无法读取剪贴板')}}
async function send(){const t=input.value.trim();if(!t||btn.disabled)return;if(t.indexOf('https://e.tb.cn')===-1){showToast('请发送淘口令（含 e.tb.cn 链接）');return};addMsg(t,'user');input.value='';btn.disabled=true
try{const r=await fetch('/parse',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'content='+encodeURIComponent(t)});const d=await r.json();if(d.code===0){addResult(d.item_id)}else{addMsg(d.msg||'解析失败','error')}}catch{addMsg('网络错误，请检查网络后重试','error')}
btn.disabled=false}
function addMsg(t,type){empty.style.display='none';const r=document.createElement('div');r.className='msg-row '+(type==='user'?'msg-right':'msg-left');r.innerHTML=type==='error'?'<div class="bubble bubble-bot bubble-error">'+esc(t)+'</div>':'<div class="bubble bubble-'+type+'">'+esc(t)+'</div>';msgList.appendChild(r);scroll()}
function addResult(id){empty.style.display='none';const r=document.createElement('div');r.className='msg-row msg-left';r.innerHTML='<div class="bubble bubble-bot"><div class="bot-label">商品数字ID</div><div class="bot-id" onclick="copyId('+id+')">'+id+'</div><div class="bot-copy" onclick="copyId('+id+')">点击复制</div></div>';msgList.appendChild(r);scroll()}
async function copyId(id){try{await navigator.clipboard.writeText(String(id));showToast('已复制 '+id)}catch{const t=document.createElement('textarea');t.value=id;t.style.position='fixed';t.style.opacity='0';document.body.appendChild(t);t.select();document.execCommand('copy');document.body.removeChild(t);showToast('已复制 '+id)}}
function scroll(){requestAnimationFrame(()=>{msgList.scrollTop=msgList.scrollHeight})}
function showToast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._t);t._t=setTimeout(()=>{t.style.display='none'},1500)}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
if('serviceWorker'in navigator){window.addEventListener('load',()=>{navigator.serviceWorker.register('/service-worker.js')})}
</script>
</div>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(PWA_HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
