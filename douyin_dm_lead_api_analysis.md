# 抖音私信 OpenAPI 与线索相关能力分析

来源文档：`C:\Users\Administrator\Desktop\抖音私信能力对外OpenApi.pdf`

## 1. 文档中出现的接口

基础域名：

- 线上：`https://gmp.bytedanceapi.com/ai_chat_agent_api/v1/openapi`
- 测试：`https://gmp.bytedanceapi.com/ai_chat_agent_test_api/v1/openapi`

接口清单：

| 接口/能力 | 路径 | 作用 | 是否私信相关 | 是否线索相关 |
| --- | --- | --- | --- | --- |
| 获取抖音授权二维码页面接口 | `/get_aweme_auth_url` | 获取授权页并注册回调地址 | 是 | 间接相关 |
| 私信事件回调 | `callback_url` | 接收私信事件 webhook | 是 | 是 |
| 私信消息发送接口 | `/send_msg` | 给用户发送私信 | 是 | 是 |
| 用户私信多媒体资源下载接口 | `/download_resource` | 下载用户在私信中发送的图片/视频 | 是 | 间接相关 |
| 抖音账号信息查询接口 | `/list_bind_info` | 查询已绑定抖音账号及 open_id | 是 | 间接相关 |
| 图片上传接口 | `/upload_image_file` | 上传图片，供发送私信时使用 | 是 | 间接相关 |

结论：

- 文档没有出现独立的“线索”接口。
- “线索”能力是通过“私信回调 + 私信场景 + 会话进入事件 + 发送私信”来承接的。

## 2. 和私信直接相关的接口说明

### 2.1 `/get_aweme_auth_url`

用途：

- 生成抖音授权二维码页面地址。
- 授权时会登记 `callback_url`，后续私信事件会回调到该地址。

关键参数：

- `main_account_id`
- `account_name`
- `auth_redirect_url`
- `callback_url`
- `callback_event`

说明：

- 这是整个私信能力的入口。
- 如果没有先授权和配置回调，后续私信链路无法闭环。

### 2.2 `callback_url` 私信事件回调

用途：

- 接收抖音侧推送的私信事件。

文档明确写出的事件：

- `im_receive_msg`：接收到的私信
- `im_send_msg`：发送出去的私信

回调中有价值的字段：

- `from_user_id`
- `to_user_id`
- `content.conversation_short_id`
- `content.server_message_id`
- `content.message_type`
- `content.user_infos`
- `content.create_time`

说明：

- `conversation_short_id` 是后续发送私信时的 `conversation_id` 来源之一。
- `server_message_id` 是后续发送私信时的 `msg_id` 来源之一。

### 2.3 `/send_msg`

用途：

- 发送文本或图片私信。

关键参数：

- `main_account_id`
- `from_user_id`
- `to_user_id`
- `content`
- `image_id`
- `conversation_id`
- `msg_id`
- `scene`

重点说明：

- 文档显示 `conversation_id` 和 `msg_id` 在某些场景下是必传。
- 这两个值主要来源于 webhook 回调。

### 2.4 `/download_resource`

用途：

- 下载用户在私信中发来的多媒体内容。

关键参数：

- `main_account_id`
- `conversation_id`
- `msg_id`
- `resource_type`

说明：

- 如果你的系统要处理用户发来的图片、视频或做自动归档，这个接口是必需的。

### 2.5 `/list_bind_info`

用途：

- 查询授权绑定过的抖音账号。

关键参数：

- `main_account_id`
- `page_num`
- `page_size`
- `name_or_open_id`

说明：

- 常用于查账号和 `open_id`，属于私信系统的配套接口。

### 2.6 `/upload_image_file`

用途：

- 上传图片，返回图片 id，后续用于 `/send_msg` 发图。

关键参数：

- `main_account_id`
- `image_base64`
- `file_name`

说明：

- 发送图片私信前需要先调用它。

## 3. 和线索最相关的能力

虽然文档没有单独定义 lead/线索接口，但以下能力明显用于线索运营或线索触达。

### 3.1 进入会话事件驱动后续触达

文档在 `/send_msg` 参数说明中提到：

- `conversation_id` 可来源于“接收用户进入私信会话页事件”的 webhook 中 `conversation_short_id`
- `msg_id` 可来源于“接收用户进入私信会话页事件”的 webhook 中 `server_message_id`

这意味着：

- 用户进入私信页，本身就是一个重要触发事件。
- 这个事件可以作为线索进入、线索激活、客服接待、自动欢迎语触达的起点。

### 3.2 `/send_msg` 的 `scene`

文档中与线索最相关的场景值：

- `im_enter_direct_msg`：用户主动进入私信会话页
- `im_b2b_direct_message`：B2B 场景私信触达
- `im_authorize_message`：主动私信持续触达
- `im_reply_msg`：对消息进行回复

判断：

- `im_b2b_direct_message` 最像传统“销售线索/B2B 线索触达”。
- `im_authorize_message` 更像用户已授权后的持续运营触达。
- `im_enter_direct_msg` 更像用户进入会话后的自动欢迎、自动跟进、线索接待。

## 4. 文档里的一个关键不一致

文档在“回调事件列表”里明确列出的是：

- `im_receive_msg`
- `im_send_msg`

但是回调示例中的 `event` 却写成了：

- `im_enter_direct_msg`

这说明至少有两种可能：

1. 文档遗漏了部分回调事件枚举。
2. `im_enter_direct_msg` 既被当成回调事件，也被当成发送场景值使用。

对接建议：

- 后端 webhook 解析时不要只白名单 `im_receive_msg`、`im_send_msg`。
- 应兼容处理 `im_enter_direct_msg` 以及未来可能新增的相近事件。

## 5. 推荐的实际对接链路

如果你的目标是“私信接待 + 线索承接”，推荐按下面顺序做：

1. 调用 `/get_aweme_auth_url`
2. 完成账号授权，并配置 `callback_url`
3. 接收 webhook，保存以下字段：
   - `event`
   - `from_user_id`
   - `to_user_id`
   - `content.conversation_short_id`
   - `content.server_message_id`
   - `content.message_type`
   - `content.create_time`
4. 当用户发消息或进入私信页时，把该用户视为可跟进线索
5. 调用 `/send_msg` 做欢迎语、自动回复、人工接待或 B2B 触达
6. 如果用户发送图片/视频，调用 `/download_resource`
7. 如果要发图片，先调用 `/upload_image_file`

## 6. 最终判断

### 私信核心接口

- `/get_aweme_auth_url`
- `callback_url`
- `/send_msg`
- `/download_resource`
- `/list_bind_info`
- `/upload_image_file`

### 线索核心能力

严格来说不是独立接口，而是以下组合：

- 用户进入私信会话页事件
- 用户发送私信事件
- `conversation_short_id` / `server_message_id`
- `/send_msg` 的 `scene`
- `im_b2b_direct_message`
- `im_authorize_message`
- `im_enter_direct_msg`

## 7. 开发侧建议

- 把 webhook 事件表设计为“可扩展事件模型”，不要写死只支持两个事件。
- 持久化保存 `conversation_short_id` 和 `server_message_id`，因为它们直接决定能否继续触达。
- 线索系统如果要和私信系统打通，建议把“用户进入私信页”和“用户主动发私信”都定义为线索触发条件。
- 如果后续需要 CRM 化，可以把 `open_id`、会话 id、最近消息 id、最近触达场景一起落库。

## 8. 建议的下一步实现顺序

如果现在准备开始开发，建议按这个顺序推进：

1. 先实现签名校验中间件
2. 再实现 `/get_aweme_auth_url` 的调用封装
3. 落地 webhook 接收接口并保存事件原文
4. 从 webhook 中解析并持久化：
   - `from_user_id`
   - `to_user_id`
   - `conversation_short_id`
   - `server_message_id`
   - `event`
   - `message_type`
5. 封装 `/send_msg`
6. 补 `/upload_image_file` 和 `/download_resource`
7. 最后再把这些能力接入线索/CRM 流程

原因：

- 真正的核心不是先“发消息”，而是先把回调链路打通。
- 没有回调里的 `conversation_short_id` 和 `server_message_id`，很多发送场景无法完整跑通。

## 9. 如果要做线索系统，最少要存的字段

建议最少保存以下字段：

| 字段 | 用途 |
| --- | --- |
| `open_id` | 用户唯一标识 |
| `account_open_id` | 当前接待的抖音账号 |
| `conversation_short_id` | 后续触达需要 |
| `server_message_id` | 某些触达场景需要 |
| `event` | 判断是发消息、收消息还是进入会话 |
| `message_type` | 判断文本、图片、视频等 |
| `message_content_raw` | 保留原始内容，方便追查 |
| `create_time` | 线索首次/最近活跃时间 |
| `scene` | 区分回复、进入会话、B2B 触达、持续触达 |
| `bind_status` | 判断账号是否可正常使用 |

额外建议：

- `conversation_short_id` 和 `server_message_id` 建议按“最近一次有效值”更新。
- webhook 原始报文建议完整留档，便于排查事件类型变化。

## 10. 当前项目与文档差异

### 10.1 已对齐

- 已对接 `/get_aweme_auth_url`，并传入文档要求的 `main_account_id / account_name / auth_redirect_url / callback_url / callback_event`
- 已实现 `callback_url` 对应的 webhook 接收，并对私信事件做签名校验、落库、会话/线索沉淀
- 已对接 `/send_msg`、`/download_resource`、`/upload_image_file`
- 已新增 `/list_bind_info` 的本地代理接口，用于校验抖音账号绑定状态
- 已将授权回调页改为优先解析 `open_id / nick_name / avatar`，与文档中的 `auth_redirect_url` 回传方式一致
- 已将授权状态判断逻辑改为优先基于 `/list_bind_info` 的 `bind_status`

### 10.2 仍未完全覆盖

- 项目还没有把 `/list_bind_info` 的返回结果长期保存为独立的本地“绑定账号表”，当前主要用于运行时查询授权状态
- 文档中的全部私信场景和值班运营能力没有逐项做成前端页面或本地业务规则，目前实现的是主链路
- 文档更偏接口说明，项目当前仍然没有完全覆盖所有潜在事件类型和全部运营场景

### 10.3 项目自增能力

- 新增了 `/auth-callback-records`：保存授权回跳参数，便于排查授权过程
- 新增了 `/auth-token-records`：兼容记录 `code -> token` 的结果，方便调试，但不是当前私信文档主流程必需项
- 新增了 `/auth-status`：把回调记录和 `/list_bind_info` 结果整合成“是否已授权/是否需重授权”的本地视图
- 前端增加了授权回调结果页和调试展示页，便于联调和人工确认

### 10.4 当前最关键的认知差异

- 这份文档的授权成功判断，更核心的是：
  - `auth_redirect_url` 回来时是否带回 `open_id / nick_name / avatar`
  - `/list_bind_info` 查询时 `bind_status` 是否为成功
- 而不是标准网页 OAuth 场景下常见的“必须先拿到 `code` 再换 token 才算成功”
- 因此，项目中保留的 `code -> token` 逻辑应视为兼容能力，不应再作为当前文档下的唯一成功标准
