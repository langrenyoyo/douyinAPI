# Douyin DM Lead Demo

一个最小可跑的抖音私信/线索承接示例，包含：

- 抖音 webhook 签名校验
- 私信事件接收
- SQLite 落库
- 线索联系人视图
- 发送私信接口封装
- 获取授权二维码页面
- 图片上传
- 私信多媒体下载

## 文件说明

- `app.py`：主程序
- `.env.example`：环境变量示例
- `douyin_dm_lead_api_analysis.md`：接口分析文档
- `sample_webhook_payload.json`：本地 webhook 示例报文
- `test_webhook.py`：本地带签名回调测试脚本
- `call_local_api.py`：调用本地接口的通用脚本
- `sample_*_request.json`：各接口请求模板

## 环境变量

至少需要配置：

- `DY_SECRET_KEY`：文档中的签名密钥

可选配置：

- `DY_BASE_URL`：默认使用测试地址
- `DY_ALLOWED_DRIFT_SECONDS`：签名时间漂移容忍秒数
- `DY_HTTP_TIMEOUT_SECONDS`：调用抖音接口的超时秒数
- `AUTO_REPLY_ENABLED`：是否启用 webhook 自动回复
- `AUTO_REPLY_MAIN_ACCOUNT_ID`：自动回复使用的主账号 id
- `AUTO_REPLY_TEXT`：自动回复文案
- `PUBLIC_BASE_URL`：抖音可访问到的公网根地址
- `AUTH_REDIRECT_URL`：授权成功后的回跳地址
- `DY_MAIN_ACCOUNT_ID`：抖音主账号 id
- `DY_ACCOUNT_NAME`：抖音账号名称

PowerShell 示例：

```powershell
$env:DY_SECRET_KEY="your-secret-key"
$env:DY_BASE_URL="https://gmp.bytedanceapi.com/ai_chat_agent_test_api/v1/openapi"
$env:AUTO_REPLY_ENABLED="false"
```

## 启动

约定端口：

- 前端：`8010`
- 后端：`8081`

```powershell
uvicorn app:app --reload --host 0.0.0.0 --port 8081
```

前端启动：

```powershell
cd frontend
npm run dev
```

## 路由

- `GET /health`：健康检查
- `POST /webhook/douyin`：接收抖音 webhook
- `GET /events`：查看保存的事件
- `GET /leads`：查看提取出的线索联系人
- `GET /leads/export`：导出线索列表
- `GET /dashboard/lead-stats`：线索统计卡片
- `GET /conversations`：会话列表
- `GET /conversations/unread-summary`：未读会话/消息统计
- `GET /conversations/{conversation_id}/messages`：会话消息明细
- `POST /conversations/{conversation_id}/messages`：在会话内发送消息
- `POST /conversations/{conversation_id}/read`：会话标记已读
- `POST /conversations/{conversation_id}/pin`：会话置顶
- `POST /conversations/{conversation_id}/unpin`：取消置顶
- `POST /conversations/{conversation_id}/close`：关闭会话
- `POST /conversations/{conversation_id}/open`：重新打开会话
- `GET /leads/{lead_open_id}/follow-records`：线索跟进记录
- `GET /quick-replies`：快捷回复列表
- `GET /api-call-logs`：查看调用抖音接口的请求/响应日志
- `POST /leads/{lead_open_id}/assign`：分配线索
- `POST /leads/{lead_open_id}/follow`：记录线索跟进
- `POST /leads/{lead_open_id}/tags`：更新线索标签
- `POST /quick-replies`：新增快捷回复
- `POST /douyin/get-auth-url`：获取授权二维码页面
- `POST /douyin/get-auth-url/configured`：使用 `.env` 配置直接获取授权二维码页面
- `POST /douyin/send-msg`：直接转发发送私信
- `POST /douyin/upload-image`：上传图片用于发私信
- `POST /douyin/download-resource`：下载私信多媒体资源
- `POST /leads/send-message`：按本地保存的 lead 信息发送私信

## webhook 说明

请求头需要包含：

- `X-Auth-Timestamp`
- `Authorization`

签名规则：

```text
sha256(SECRET_KEY + body + "-" + timestamp)
```

## 推荐联调顺序

1. 启动服务
2. 用 `/health` 确认服务可用
3. 在抖音授权时把回调地址配置为 `/webhook/douyin`
4. 收到事件后查看 `/events` 和 `/leads`
5. 再使用 `/leads/send-message` 做回访或自动触达

## 真实抖音接入前提

只有配置好以下条件，前端页面里才会出现真实抖音数据：

1. 已配置 `DY_SECRET_KEY`
2. 已配置 `DY_MAIN_ACCOUNT_ID` 和 `DY_ACCOUNT_NAME`
3. 已配置 `PUBLIC_BASE_URL`
4. `PUBLIC_BASE_URL` 必须是抖音服务器可访问的公网地址
5. 已配置 `AUTH_REDIRECT_URL`
6. 已完成抖音授权
7. 用户真实发起私信或进入会话，触发 webhook

注意：

- `127.0.0.1` 或局域网地址不能作为 `callback_url`
- 没有公网回调地址，就不会收到真实抖音事件
- 没有事件进入，本地线索/会话/消息表就会一直为空

## 本地测试 webhook

先启动服务，再执行：

```powershell
python test_webhook.py --secret "your-secret-key"
```

默认会读取 `sample_webhook_payload.json`，并向本机 `http://127.0.0.1:8000/webhook/douyin` 发送一条带签名的测试请求。
如果你按当前约定启动后端端口，请改为 `http://127.0.0.1:8081/webhook/douyin`。

## 本地调用接口模板

启动服务后，可以直接用以下命令测试本地代理接口。

获取授权二维码页面：

```powershell
python call_local_api.py --path /douyin/get-auth-url --payload sample_get_auth_url_request.json
```

发送私信：

```powershell
python call_local_api.py --path /douyin/send-msg --payload sample_send_msg_request.json
```

按线索表发送私信：

```powershell
python call_local_api.py --path /leads/send-message --payload sample_send_lead_message_request.json
```

上传图片：

```powershell
python call_local_api.py --path /douyin/upload-image --payload sample_upload_image_request.json
```

下载私信资源：

```powershell
python call_local_api.py --path /douyin/download-resource --payload sample_download_resource_request.json
```

使用前请先把各个 `sample_*.json` 中的占位值替换为真实值，尤其是：

- `main_account_id`
- `from_user_id`
- `to_user_id` / `lead_open_id`
- `conversation_id`
- `msg_id`
- `image_base64`
- 回调域名和授权回跳地址

## 接口排障

如果本地接口调用失败，可以直接查看：

- `GET /api-call-logs`

这里会保存：

- 调用的抖音接口路径
- 请求时间戳
- HTTP 状态码
- 响应原文
- 异常类型
- 异常消息

这对排查签名错误、参数错误、上游 4xx/5xx 都很有帮助。

如果上游接口直接报错，本地接口现在也会返回结构化错误 JSON，例如：

```json
{
  "code": -1,
  "msg": "Upstream request failed",
  "error_type": "HTTPError",
  "upstream_status": 400,
  "upstream_response": "..."
}
```

这样你不用只看终端，也不用先翻数据库，就能先拿到关键失败信息。

## webhook 幂等处理

考虑到上游回调失败后可能重试，当前 demo 已增加 webhook 去重：

- 会基于 `event + from_user_id + to_user_id + conversation_short_id + server_message_id + create_time` 生成 `event_key`
- 如果同一个 `event_key` 已处理过，再收到时会标记为重复事件
- 重复事件仍会记录到 `webhook_events`
- 但不会重复触发自动回复

你可以通过 `GET /events` 查看：

- `event_key`
- `is_duplicate`

## 页面接口说明

当前后端已经补出一版可供“线索管理”和“会话中心”页面直接消费的接口层：

- 线索管理页：
  - `GET /dashboard/lead-stats`
  - `GET /leads`
  - `GET /leads/export`
  - `GET /leads/{lead_open_id}/follow-records`
  - `POST /leads/{lead_open_id}/assign`
  - `POST /leads/{lead_open_id}/follow`
  - `POST /leads/{lead_open_id}/tags`

- 会话中心页：
  - `GET /conversations`
  - `GET /conversations/unread-summary`
  - `GET /conversations/{conversation_id}/messages`
  - `POST /conversations/{conversation_id}/messages`
  - `POST /conversations/{conversation_id}/read`
  - `POST /conversations/{conversation_id}/pin`
  - `POST /conversations/{conversation_id}/unpin`
  - `POST /conversations/{conversation_id}/close`
  - `POST /conversations/{conversation_id}/open`
  - `GET /quick-replies`
  - `POST /quick-replies`

说明：

- webhook 进入后会自动沉淀成线索、会话、消息、跟进记录
- 本地发送消息成功后，也会同步写入 `messages` 和 `conversations`
- 当前更偏向“后端原型”和“联调接口层”
- 当前已补筛选、分页、已读、快捷回复等基础能力
- 当前已补日期筛选、导出、标签、置顶、未读统计、会话开关等能力
- 如果前端要完全复刻你给的两个页面，后面还可以继续补自动分配、通知设置、分组、通知策略、权限体系等接口

## 自动回复

如果你想在收到 webhook 后自动回一条消息，可以打开：

```powershell
$env:AUTO_REPLY_ENABLED="true"
$env:AUTO_REPLY_MAIN_ACCOUNT_ID="1234"
$env:AUTO_REPLY_TEXT="您好，已收到您的咨询，我们会尽快回复您。"
```

当前自动回复规则：

- `im_receive_msg`：按 `im_reply_msg` 回消息
- `im_enter_direct_msg`：按 `im_enter_direct_msg` 回消息

如果缺少 `conversation_short_id` 或 `server_message_id`，自动回复会跳过。

## 注意

- 当前 demo 使用 SQLite，适合本地联调，不适合直接上生产。
- 当前 demo 已补齐私信主链路和常用配套接口，并支持基础 API 调用日志；但还没有进一步做重试、限流、异步任务和生产级日志。
- webhook 中 `content` 在文档里既像对象也像字符串，代码已兼容两种写法。
- 自动回复当前是同步执行的，适合演示，不适合高并发生产场景。
- 当前去重策略基于业务字段生成 `event_key`，适合演示和一般联调；如果上游后续提供更稳定的事件唯一 id，建议切换到上游 id。
