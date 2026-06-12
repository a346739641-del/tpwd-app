# 淘口令解析 - 公众号自动回复

用户给公众号发送淘口令，自动回复商品数字ID。

## 部署到 Render.com（免费）

### 1. 上传代码

把 `app.py`、`requirements.txt` 上传到 GitHub 仓库。

### 2. 注册 Render

1. 注册 https://render.com （用 GitHub 账号登录）
2. Dashboard → New + → Web Service
3. 连接你的 GitHub 仓库
4. 配置：
   - **Name**: `tpwd-parse`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free
5. 点 **Create Web Service**

### 3. 设置环境变量

部署后在 Render Dashboard → Environment 中添加：

| 变量名 | 值 |
|--------|------|
| `TPWD_USER` | `13332633249` |
| `TPWD_PASS` | `molin000` |
| `TPWD_APPKEY` | `lr8kz1wq` |
| `WX_TOKEN` | `tpwd123` |

部署完成后会得到 URL，如 `https://tpwd-parse.onrender.com`

---

## 个人订阅号接入方式

个人订阅号没有"服务器配置"功能，需要通过**第三方平台**中转。

### 推荐平台

| 平台 | 说明 | 费用 |
|------|------|------|
| **微信云托管** | 腾讯官方，最稳定，公众号后台可直接进入 | 有免费额度 |
| **微擎** | 最流行的公众号管理框架，功能强大 | 需自建服务器 |
| **微小宝** | 在线SaaS平台，配置简单 | 有免费版 |
| **新媒体管家** | 浏览器插件形式 | 免费 |

### 配置方法

无论用哪个平台，流程都一样：

1. 把公众号授权给第三方平台
2. 在平台的"自动回复"或"智能回复"设置中
3. **回调地址填**: `https://你的地址/api/reply`
4. **请求方式**: POST
5. **参数名**: `content`（平台会把用户消息内容传过来）
6. **回复方式**: 解析接口返回的 JSON 中的 `reply` 字段

### API 接口说明

**请求**:
```
POST https://你的地址/api/reply
Content-Type: application/x-www-form-urlencoded
content=淘口令内容
```

**返回**:
```json
{
  "code": 0,
  "reply": "商品ID: 1013620091978\n\n完整链接: https://item.taobao.com/item.htm?id=..."
}
```

### 微信云托管（最推荐）

1. 公众号后台 → **微信云托管** （左侧菜单底部）
2. 注册开通，创建环境
3. 在云托管中部署本代码（支持直接上传或 GitHub 导入）
4. 在云托管中开启"消息推送"功能
5. 云托管会自动处理微信回调，不需要额外配置

> **注意**: Render 免费版 15 分钟无访问会休眠，首次访问会慢几秒。如果流量大建议升级付费版。
