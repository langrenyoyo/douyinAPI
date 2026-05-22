import { useEffect, useState } from 'react'
import './index.css'

const workspacePages = [
  { key: 'conversations', label: '会话管理', hint: '查看私信会话与消息流转' },
  { key: 'leads', label: '线索管理', hint: '查看沉淀线索与跟进状态' },
  { key: 'video-edit', label: '视频剪辑', hint: '创建视频剪辑和图转视频任务' },
  { key: 'review-test', label: '一键审核测试', hint: '测试拒审素材修复与采纳任务' },
]

const defaultVideoForm = {
  account_id: '',
  account_type: 'AGENT',
  task_type: 'video_edit',
  title: '',
  product_name: '',
  prompt: '',
  script: '',
  selling_points: '',
  benefit_points: '',
  video_element_ids: '',
  material_urls: '',
  image_urls: '',
  count: '1',
  task_name: '',
  is_auto_save_all_result: false,
}

const defaultReviewForm = {
  material_id: '',
  account_id: '',
  mid: '',
  repair_ids: '',
  task_id: '',
  suggestions_payload:
    '{\n  "advertiser_id": "123456789",\n  "filtering": {\n    "material_ids": [8888],\n    "promotion_ids": [],\n    "ai_repair_ids": [],\n    "repair_start_time": "2026-05-01 00:00:00",\n    "repair_end_time": "2026-05-31 23:59:59"\n  },\n  "page": "1",\n  "page_size": "10"\n}',
  cross_account_payload: '{\n  "material_id": 8888,\n  "account_id": 123456,\n  "mid": "replace-with-mid"\n}',
  adopt_task_payload: '{\n  "repair_ids": [10001]\n}',
  adopt_result_payload: '{\n  "task_id": "replace-with-task-id"\n}',
}

function formatDateTime(value) {
  if (!value) return '--'
  const num = Number(value)
  if (Number.isFinite(num)) {
    return new Date(num).toLocaleString('zh-CN', { hour12: false })
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function parseLines(value) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseNumberLines(value) {
  return parseLines(value)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))
}

function LeadPage({ stats, leads, loading }) {
  return (
    <div className="page-shell">
      <div className="hero-cards">
        <article className="hero-card">
          <span>全部线索</span>
          <strong>{stats.total_leads ?? 0}</strong>
          <em>私信触达沉淀</em>
        </article>
        <article className="hero-card ghost">
          <span>待分配</span>
          <strong>{stats.pending_leads ?? 0}</strong>
          <em>等待认领</em>
        </article>
        <article className="hero-card">
          <span>跟进中</span>
          <strong>{stats.following_leads ?? 0}</strong>
          <em>持续转化</em>
        </article>
        <article className="hero-card compare">
          <span>未读会话</span>
          <strong>{stats.unread_conversations ?? 0}</strong>
          <em>需要优先回复</em>
        </article>
      </div>

      <div className="banner warning">
        当前页面展示的是本地数据库中的真实沉淀结果；只有 webhook 收到事件后，线索列表才会更新。
      </div>

      <section className="table-card">
        <div className="table-header">
          <strong>线索列表</strong>
          <span className="status-dot">共 {leads.length} 条</span>
        </div>

        <div className="lead-table">
          <div className="lead-row head">
            <span>客户</span>
            <span>手机号</span>
            <span>微信</span>
            <span>最近活跃时间</span>
            <span>互动类型</span>
            <span>线索类型</span>
            <span>最近记录</span>
            <span>渠道</span>
            <span>状态</span>
          </div>
          {loading ? <div className="empty">加载中...</div> : null}
          {!loading && leads.length === 0 ? <div className="empty">暂无线索数据</div> : null}
          {!loading
            ? leads.map((lead) => (
                <div className="lead-row" key={lead.open_id}>
                  <span className="lead-user">
                    <img
                      src={lead.avatar_url || 'https://placehold.co/56x56/e9eefc/4a5cc7?text=%E7%BA%BF'}
                      alt={lead.display_name || '线索'}
                    />
                    <b>{lead.display_name || '未命名客户'}</b>
                  </span>
                  <span>{lead.phone || '--'}</span>
                  <span>{lead.wechat || '--'}</span>
                  <span>{formatDateTime(lead.latest_active_time)}</span>
                  <span>{lead.latest_scene || '私信'}</span>
                  <span>{lead.lead_type || '私信线索'}</span>
                  <span>{lead.last_interaction_record || '--'}</span>
                  <span>{lead.lead_channel || '企业号'}</span>
                  <span>{lead.lead_status || 'pending'}</span>
                </div>
              ))
            : null}
        </div>
      </section>
    </div>
  )
}

function ConversationPage({
  conversations,
  activeConversation,
  messages,
  quickReplies,
  unreadSummary,
  loading,
  onSelectConversation,
}) {
  return (
    <div className="conversation-shell">
      <div className="conversation-alerts">
        <div className="banner warning">只有收到真实回调后，会话列表和消息流才会出现真实数据。</div>
        <div className="banner info">本地模拟 webhook 已经支持入库，可用于验证会话链路是否正常。</div>
      </div>

      <div className="conversation-layout">
        <aside className="conversation-list-card">
          <div className="list-toolbar">
            <button className="chip">全部会话</button>
            <button className="chip">未读优先</button>
          </div>
          <input className="search full" placeholder="搜索客户昵称或会话 ID" />

          <div className="conversation-list">
            {loading ? <div className="empty">加载中...</div> : null}
            {!loading && !conversations.length ? <div className="empty">暂无会话数据</div> : null}
            {conversations.map((item) => (
              <button
                key={item.conversation_short_id}
                className={`conversation-item ${
                  activeConversation?.conversation_short_id === item.conversation_short_id ? 'selected' : ''
                }`}
                onClick={() => onSelectConversation(item)}
              >
                <img
                  src={item.avatar_url || 'https://placehold.co/56x56/e9eefc/4a5cc7?text=%E4%BC%9A'}
                  alt={item.display_name || '会话'}
                />
                <div className="conversation-copy">
                  <div className="conversation-topline">
                    <strong>{item.display_name || '未命名会话'}</strong>
                    <span>{item.latest_message_time ? formatDateTime(item.latest_message_time).slice(11, 16) : '--'}</span>
                  </div>
                  <p>{item.latest_message_text || '暂无消息'}</p>
                </div>
                {item.unread_count ? <i>{item.unread_count}</i> : null}
              </button>
            ))}
          </div>
        </aside>

        <section className="chat-card">
          <div className="chat-metrics">
            <div>
              <span>会话总数</span>
              <strong>{conversations.length}</strong>
            </div>
            <div>
              <span>未读会话</span>
              <strong>{unreadSummary.unread_conversations ?? 0}</strong>
            </div>
            <div>
              <span>快捷回复</span>
              <strong>{quickReplies.length}</strong>
            </div>
          </div>

          <div className="chat-header">
            <div className="chat-user">
              <img
                src={activeConversation?.avatar_url || 'https://placehold.co/48x48/e9eefc/4a5cc7?text=%E8%81%8A'}
                alt={activeConversation?.display_name || '聊天'}
              />
              <div>
                <strong>{activeConversation?.display_name || '请选择会话'}</strong>
                <span>未读消息 {activeConversation?.unread_count ?? 0}</span>
              </div>
            </div>
            <div className="chat-actions">消息流</div>
          </div>

          <div className="message-stream">
            {!activeConversation ? <div className="empty">请选择左侧会话查看消息明细</div> : null}
            {activeConversation
              ? messages.map((message) => (
                  <div key={message.id} className={`message-bubble ${message.direction === 'outbound' ? 'outbound' : 'inbound'}`}>
                    <small>{formatDateTime(message.create_time)}</small>
                    <p>{message.message_text || '[多媒体消息]'}</p>
                  </div>
                ))
              : null}
          </div>

          <div className="composer">
            <div className="composer-tools">快捷回复预览</div>
            <textarea placeholder="这里保留了会话输入区样式，当前版本不直接发送消息。" />
            <div className="quick-replies">
              {quickReplies.slice(0, 3).map((item) => (
                <span key={item.id}>{item.title}</span>
              ))}
            </div>
          </div>
        </section>

        <aside className="detail-card">
          <h3>会话摘要</h3>
          <div className="detail-grid">
            <span>客户名称</span>
            <strong>{activeConversation?.display_name || '--'}</strong>
            <span>会话 ID</span>
            <strong>{activeConversation?.conversation_short_id || '--'}</strong>
            <span>最近事件</span>
            <strong>{activeConversation?.latest_event || '--'}</strong>
            <span>消息类型</span>
            <strong>{activeConversation?.latest_message_type || '--'}</strong>
            <span>最后更新时间</span>
            <strong>{formatDateTime(activeConversation?.latest_message_time)}</strong>
          </div>
        </aside>
      </div>
    </div>
  )
}

function VideoEditPage({
  videoForm,
  onChange,
  onSubmit,
  submitting,
  tasks,
  activeTask,
  onSelectTask,
  onRefreshTask,
  taskLoading,
  createResult,
}) {
  return (
    <div className="page-shell">
      <div className="hero-cards">
        <article className="hero-card">
          <span>任务总数</span>
          <strong>{tasks.length}</strong>
          <em>本地任务记录</em>
        </article>
        <article className="hero-card ghost">
          <span>已完成</span>
          <strong>{tasks.filter((item) => item.status === 'succeeded').length}</strong>
          <em>可查看视频结果</em>
        </article>
        <article className="hero-card">
          <span>进行中</span>
          <strong>{tasks.filter((item) => !['succeeded', 'failed'].includes(item.status)).length}</strong>
          <em>等待刷新状态</em>
        </article>
        <article className="hero-card compare">
          <span>运行模式</span>
          <strong>{activeTask?.source || 'mock'}</strong>
          <em>支持 mock / upstream</em>
        </article>
      </div>

      <div className="video-edit-layout">
        <section className="table-card video-form-card">
          <div className="table-header">
            <strong>创建视频任务</strong>
            <span className="status-dot">支持视频剪辑 / 图转视频</span>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>账户 ID</span>
              <input name="account_id" value={videoForm.account_id} onChange={onChange} placeholder="例如：123456789" />
            </label>

            <label className="field">
              <span>账户体系</span>
              <select name="account_type" value={videoForm.account_type} onChange={onChange}>
                <option value="AGENT">AGENT</option>
                <option value="BP">BP</option>
              </select>
            </label>

            <label className="field">
              <span>任务类型</span>
              <select name="task_type" value={videoForm.task_type} onChange={onChange}>
                <option value="video_edit">视频剪辑</option>
                <option value="image_to_video">图转视频</option>
              </select>
            </label>

            <label className="field">
              <span>任务标题</span>
              <input name="title" value={videoForm.title} onChange={onChange} placeholder="例如：春季鞋款卖点剪辑" />
            </label>

            <label className="field">
              <span>商品名称</span>
              <input name="product_name" value={videoForm.product_name} onChange={onChange} placeholder="例如：轻量跑鞋" />
            </label>

            <label className="field wide">
              <span>一句话需求 / Prompt</span>
              <textarea
                name="prompt"
                value={videoForm.prompt}
                onChange={onChange}
                placeholder="例如：输出一条 15 秒竖版视频，突出轻便、透气、通勤百搭。"
              />
            </label>

            <label className="field wide">
              <span>脚本文案</span>
              <textarea
                name="script"
                value={videoForm.script}
                onChange={onChange}
                placeholder="可选，填写镜头节奏、口播、字幕草稿。"
              />
            </label>

            <label className="field wide">
              <span>卖点列表</span>
              <textarea
                name="selling_points"
                value={videoForm.selling_points}
                onChange={onChange}
                placeholder="每行一个卖点，例如：\n透气网面\n轻量鞋底\n适合通勤"
              />
            </label>

            <label className="field wide">
              <span>利益点列表</span>
              <textarea
                name="benefit_points"
                value={videoForm.benefit_points}
                onChange={onChange}
                placeholder="每行一个利益点，例如：\n满 300 立减 50\n七天包邮"
              />
            </label>

            <label className="field wide">
              <span>视频元素 ID</span>
              <textarea
                name="video_element_ids"
                value={videoForm.video_element_ids}
                onChange={onChange}
                placeholder="每行一个视频元素 ID，例如：\n123456\n789012"
              />
            </label>

            <label className="field wide">
              <span>视频素材链接</span>
              <textarea
                name="material_urls"
                value={videoForm.material_urls}
                onChange={onChange}
                placeholder="每行一个素材 URL，适合视频剪辑任务。"
              />
            </label>

            <label className="field wide">
              <span>图片素材链接</span>
              <textarea
                name="image_urls"
                value={videoForm.image_urls}
                onChange={onChange}
                placeholder="每行一个图片 URL，适合图转视频任务。"
              />
            </label>

            <label className="field">
              <span>生成数量</span>
              <input name="count" value={videoForm.count} onChange={onChange} placeholder="默认 1，最大 5" />
            </label>

            <label className="field">
              <span>任务名称</span>
              <input name="task_name" value={videoForm.task_name} onChange={onChange} placeholder="例如：春季鞋款混剪任务" />
            </label>

            <label className="field checkbox-field wide">
              <input
                type="checkbox"
                name="is_auto_save_all_result"
                checked={videoForm.is_auto_save_all_result}
                onChange={(event) =>
                  onChange({
                    target: {
                      name: 'is_auto_save_all_result',
                      value: event.target.checked,
                    },
                  })
                }
              />
              <span>任务完成后自动保存全部结果</span>
            </label>
          </div>

          <div className="video-form-actions">
            <button className="primary-btn" onClick={onSubmit} disabled={submitting}>
              {submitting ? '创建中...' : '创建视频任务'}
            </button>
            <span className="field-tip">本地默认走 mock 模式，接入真实上游后可切换为 upstream。</span>
          </div>
        </section>

        <section className="table-card task-list-card">
          <div className="table-header">
            <strong>任务列表</strong>
            <span className="status-dot">最近创建的任务会显示在这里</span>
          </div>

          {!tasks.length ? <div className="empty">暂无视频任务，先创建一个试试。</div> : null}
          <div className="task-list">
            {tasks.map((task) => (
              <button
                key={task.task_id}
                className={`task-item ${activeTask?.task_id === task.task_id ? 'selected' : ''}`}
                onClick={() => onSelectTask(task)}
              >
                <div>
                  <strong>{task.title || '未命名任务'}</strong>
                  <p>{task.product_name || task.task_type}</p>
                </div>
                <div className="task-meta">
                  <span className={`task-status ${task.status}`}>{task.status}</span>
                  <span>{task.progress}%</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      </div>

      {createResult ? (
        <section className={`banner ${createResult.ok ? 'info' : 'warning'}`}>
          {createResult.ok ? '视频任务创建成功。' : '视频任务创建失败。'}
          <div className="auth-url">
            <span>{createResult.message}</span>
          </div>
        </section>
      ) : null}

      <section className="table-card">
        <div className="table-header">
          <strong>任务详情</strong>
          <div className="header-actions">
            <button
              className="chip"
              onClick={() => activeTask && onRefreshTask(activeTask.task_id)}
              disabled={!activeTask || taskLoading}
            >
              {taskLoading ? '刷新中...' : '刷新任务状态'}
            </button>
          </div>
        </div>

        {!activeTask ? <div className="empty">请选择一个视频任务查看详情。</div> : null}
        {activeTask ? (
          <div className="video-task-detail">
            <div className="auth-status-grid">
              <div className="auth-status-item">
                <span>任务 ID</span>
                <strong>{activeTask.task_id}</strong>
              </div>
              <div className="auth-status-item">
                <span>任务类型</span>
                <strong>{activeTask.task_type}</strong>
              </div>
              <div className="auth-status-item">
                <span>当前状态</span>
                <strong>{activeTask.status}</strong>
              </div>
              <div className="auth-status-item">
                <span>进度</span>
                <strong>{activeTask.progress}%</strong>
              </div>
              <div className="auth-status-item">
                <span>数据来源</span>
                <strong>{activeTask.source}</strong>
              </div>
              <div className="auth-status-item">
                <span>更新时间</span>
                <strong>{formatDateTime(activeTask.updated_at)}</strong>
              </div>
            </div>

            <div className="detail-panels">
              <article className="detail-panel">
                <h3>输入摘要</h3>
                <p><b>商品：</b>{activeTask.product_name || '--'}</p>
                <p><b>标题：</b>{activeTask.title || '--'}</p>
                <p><b>Prompt：</b>{activeTask.prompt || '--'}</p>
                <p><b>脚本：</b>{activeTask.script || '--'}</p>
              </article>
              <article className="detail-panel">
                <h3>素材信息</h3>
                <p><b>卖点：</b>{activeTask.selling_points?.join(' / ') || '--'}</p>
                <p><b>视频素材：</b>{activeTask.material_urls?.length || 0} 条</p>
                <p><b>图片素材：</b>{activeTask.image_urls?.length || 0} 条</p>
              </article>
              <article className="detail-panel">
                <h3>生成结果</h3>
                <p><b>视频：</b>{activeTask.result_video_url ? <a href={activeTask.result_video_url} target="_blank" rel="noreferrer">{activeTask.result_video_url}</a> : '--'}</p>
                <p><b>封面：</b>{activeTask.result_cover_url ? <a href={activeTask.result_cover_url} target="_blank" rel="noreferrer">{activeTask.result_cover_url}</a> : '--'}</p>
                <p><b>错误：</b>{activeTask.error_message || '--'}</p>
              </article>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}

function ReviewTestPage({
  reviewForm,
  onChange,
  onRunAction,
  reviewLoading,
  reviewResult,
}) {
  return (
    <div className="page-shell">
      <div className="hero-cards">
        <article className="hero-card">
          <span>审核测试</span>
          <strong>4</strong>
          <em>建议、跨账户、采纳、结果</em>
        </article>
        <article className="hero-card ghost">
          <span>运行模式</span>
          <strong>mock</strong>
          <em>可切换真实接口</em>
        </article>
        <article className="hero-card">
          <span>适用场景</span>
          <strong>拒审修复</strong>
          <em>广告素材过审</em>
        </article>
        <article className="hero-card compare">
          <span>接口入口</span>
          <strong>/review</strong>
          <em>独立于即创视频剪辑</em>
        </article>
      </div>

      <section className="table-card">
        <div className="table-header">
          <strong>一键审核测试</strong>
          <span className="status-dot">对应“拒审素材一键过审”接口能力</span>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>素材 ID</span>
            <input name="material_id" value={reviewForm.material_id} onChange={onChange} placeholder="例如：8888" />
          </label>
          <label className="field">
            <span>账户 ID</span>
            <input name="account_id" value={reviewForm.account_id} onChange={onChange} placeholder="例如：123456789" />
          </label>
          <label className="field">
            <span>mid</span>
            <input name="mid" value={reviewForm.mid} onChange={onChange} placeholder="用于跨账户查询" />
          </label>
          <label className="field">
            <span>修复建议 ID</span>
            <input name="repair_ids" value={reviewForm.repair_ids} onChange={onChange} placeholder="多个用逗号分隔" />
          </label>
          <label className="field wide">
            <span>采纳任务 ID</span>
            <input name="task_id" value={reviewForm.task_id} onChange={onChange} placeholder="用于查询采纳任务结果" />
          </label>

          <label className="field wide">
            <span>获取修复建议原始 JSON</span>
            <textarea
              name="suggestions_payload"
              value={reviewForm.suggestions_payload}
              onChange={onChange}
              placeholder='例如：{"advertiser_id":"123456789","filtering":{"material_ids":[8888]},"page":"1","page_size":"10"}'
            />
          </label>

          <label className="field wide">
            <span>跨账户查询原始 JSON</span>
            <textarea
              name="cross_account_payload"
              value={reviewForm.cross_account_payload}
              onChange={onChange}
              placeholder='例如：{"material_id":8888,"account_id":123456,"mid":"xxx"}'
            />
          </label>

          <label className="field wide">
            <span>创建采纳任务原始 JSON</span>
            <textarea
              name="adopt_task_payload"
              value={reviewForm.adopt_task_payload}
              onChange={onChange}
              placeholder='例如：{"repair_ids":[10001]}'
            />
          </label>

          <label className="field wide">
            <span>查询采纳结果原始 JSON</span>
            <textarea
              name="adopt_result_payload"
              value={reviewForm.adopt_result_payload}
              onChange={onChange}
              placeholder='例如：{"task_id":"review_task_xxx"}'
            />
          </label>
        </div>

        <div className="review-action-grid">
          <button className="primary-btn" onClick={() => onRunAction('suggestions')} disabled={reviewLoading}>
            {reviewLoading ? '处理中...' : '获取修复建议'}
          </button>
          <button className="chip" onClick={() => onRunAction('cross-account')} disabled={reviewLoading}>
            查询跨账户修复建议
          </button>
          <button className="chip" onClick={() => onRunAction('adopt-task')} disabled={reviewLoading}>
            创建采纳任务
          </button>
          <button className="chip" onClick={() => onRunAction('adopt-task-result')} disabled={reviewLoading}>
            查询采纳结果
          </button>
        </div>
      </section>

      <section className="table-card">
        <div className="table-header">
          <strong>接口返回</strong>
        </div>
        {!reviewResult ? <div className="empty">点击上面的按钮后，这里会展示审核接口返回结果。</div> : null}
        {reviewResult ? (
          <pre className="result-block">{JSON.stringify(reviewResult, null, 2)}</pre>
        ) : null}
      </section>
    </div>
  )
}

function AuthStatusCard({ authStatus, loading }) {
  if (loading) {
    return <section className="banner info">正在检查抖音授权状态...</section>
  }

  if (!authStatus) {
    return <section className="banner warning">暂未获取到授权状态，请先完成授权或检查后端接口。</section>
  }

  const authorized = Boolean(authStatus.authorized)
  const bindStatus = authStatus.bind_info?.bind_status
  const name = authStatus.callback_record?.nick_name || authStatus.bind_info?.account_name || '--'
  const openId = authStatus.callback_record?.open_id || authStatus.bind_info?.open_id || '--'

  return (
    <section className={`table-card auth-status-card ${authorized ? 'authorized' : 'unauthorized'}`}>
      <div className="table-header">
        <strong>抖音授权状态</strong>
        <span className={`auth-status-badge ${authorized ? 'ok' : 'warn'}`}>
          {authorized ? '已授权' : '待授权'}
        </span>
      </div>
      <div className="auth-status-grid">
        <div className="auth-status-item">
          <span>当前状态</span>
          <strong>{authorized ? '授权成功' : '尚未授权'}</strong>
        </div>
        <div className="auth-status-item">
          <span>是否需重授</span>
          <strong>{authStatus.need_reauthorize ? '是' : '否'}</strong>
        </div>
        <div className="auth-status-item">
          <span>账号昵称</span>
          <strong>{name}</strong>
        </div>
        <div className="auth-status-item">
          <span>绑定状态</span>
          <strong>{bindStatus ?? '--'}</strong>
        </div>
        <div className="auth-status-item">
          <span>open_id</span>
          <strong>{openId}</strong>
        </div>
        <div className="auth-status-item">
          <span>绑定时间</span>
          <strong>{authStatus.bind_info?.bind_time || '--'}</strong>
        </div>
      </div>
    </section>
  )
}

function AuthCallbackPage() {
  const params = new URLSearchParams(window.location.search)
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, '').replace(/^\?/, ''))
  const code = params.get('code') || hashParams.get('code')
  const state = params.get('state') || hashParams.get('state')
  const authCode = params.get('auth_code') || hashParams.get('auth_code')
  const error = params.get('error') || hashParams.get('error')
  const openId = params.get('open_id') || hashParams.get('open_id')
  const nickName = params.get('nick_name') || hashParams.get('nick_name')
  const avatar = params.get('avatar') || hashParams.get('avatar')
  const rawUrl = window.location.href
  const rawQuery = window.location.search || window.location.hash || ''
  const [saveStatus, setSaveStatus] = useState('idle')
  const [saveMessage, setSaveMessage] = useState('')
  const [latestRecord, setLatestRecord] = useState(null)
  const [authStatus, setAuthStatus] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function saveCallbackResult() {
      setSaveStatus('saving')
      setSaveMessage('')
      try {
        const res = await fetch('/auth-callback-records', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code,
            auth_code: authCode,
            state,
            error,
            open_id: openId,
            nick_name: nickName,
            avatar,
            raw_query: rawQuery,
            callback_url: rawUrl,
          }),
        })
        const data = await res.json()
        if (!res.ok || data?.code !== 0) {
          throw new Error(data?.msg || '保存授权回调失败')
        }
        if (!cancelled) {
          setSaveStatus('success')
          setSaveMessage('授权回调结果已保存')
        }
      } catch (err) {
        if (!cancelled) {
          setSaveStatus('error')
          setSaveMessage(err.message || '保存授权回调失败')
        }
      }
    }

    async function loadLatestRecord() {
      try {
        const [recordRes, statusRes] = await Promise.all([fetch('/auth-callback-records'), fetch('/auth-status')])
        const data = await recordRes.json()
        const statusData = await statusRes.json()
        if (!cancelled) {
          setLatestRecord(Array.isArray(data) && data.length ? data[0] : null)
          setAuthStatus(statusData?.data || null)
        }
      } catch {
        if (!cancelled) {
          setLatestRecord(null)
          setAuthStatus(null)
        }
      }
    }

    saveCallbackResult().finally(loadLatestRecord)

    return () => {
      cancelled = true
    }
  }, [authCode, avatar, code, error, nickName, openId, rawQuery, rawUrl, state])

  return (
    <div className="app-shell auth-callback-shell">
      <main className="content full-width">
        <header className="topbar">
          <div>
            <small>Douyin DM Lead Hub</small>
            <h1>授权回调结果</h1>
          </div>
        </header>

        <section className="table-card">
          <div className="table-header">
            <strong>回调参数</strong>
          </div>
          <div className="event-list auth-callback-grid">
            <div className="event-item"><span>code</span><span>{code || '--'}</span></div>
            <div className="event-item"><span>auth_code</span><span>{authCode || '--'}</span></div>
            <div className="event-item"><span>state</span><span>{state || '--'}</span></div>
            <div className="event-item"><span>error</span><span>{error || '--'}</span></div>
            <div className="event-item"><span>open_id</span><span>{openId || '--'}</span></div>
            <div className="event-item"><span>nick_name</span><span>{nickName || '--'}</span></div>
            <div className="event-item full"><span>avatar</span><span>{avatar || '--'}</span></div>
            <div className="event-item full"><span>当前地址</span><span>{rawUrl}</span></div>
          </div>
        </section>

        <section className={`banner ${saveStatus === 'error' ? 'warning' : 'info'}`}>
          {saveStatus === 'saving' ? '正在保存授权回调结果...' : null}
          {saveStatus === 'success' ? saveMessage : null}
          {saveStatus === 'error' ? saveMessage : null}
          {saveStatus === 'idle' ? '等待保存授权回调结果' : null}
        </section>

        {latestRecord ? (
          <section className="table-card">
            <div className="table-header">
              <strong>最近一次授权记录</strong>
            </div>
            <div className="event-list auth-callback-grid">
              <div className="event-item"><span>保存时间</span><span>{latestRecord.created_at || '--'}</span></div>
              <div className="event-item"><span>code</span><span>{latestRecord.code || '--'}</span></div>
              <div className="event-item"><span>auth_code</span><span>{latestRecord.auth_code || '--'}</span></div>
              <div className="event-item"><span>state</span><span>{latestRecord.state || '--'}</span></div>
              <div className="event-item"><span>error</span><span>{latestRecord.error || '--'}</span></div>
              <div className="event-item"><span>open_id</span><span>{latestRecord.open_id || '--'}</span></div>
              <div className="event-item"><span>nick_name</span><span>{latestRecord.nick_name || '--'}</span></div>
              <div className="event-item full"><span>avatar</span><span>{latestRecord.avatar || '--'}</span></div>
              <div className="event-item full"><span>callback_url</span><span>{latestRecord.callback_url || '--'}</span></div>
            </div>
          </section>
        ) : null}

        {authStatus ? (
          <section className="table-card">
            <div className="table-header">
              <strong>当前授权状态</strong>
            </div>
            <div className="event-list auth-callback-grid">
              <div className="event-item"><span>是否已授权</span><span>{authStatus.authorized ? '是' : '否'}</span></div>
              <div className="event-item"><span>是否需重授</span><span>{authStatus.need_reauthorize ? '是' : '否'}</span></div>
              <div className="event-item"><span>原因</span><span>{authStatus.reason || '--'}</span></div>
              <div className="event-item"><span>open_id</span><span>{authStatus.callback_record?.open_id || authStatus.bind_info?.open_id || '--'}</span></div>
              <div className="event-item"><span>昵称</span><span>{authStatus.callback_record?.nick_name || authStatus.bind_info?.account_name || '--'}</span></div>
              <div className="event-item"><span>绑定状态</span><span>{authStatus.bind_info?.bind_status ?? '--'}</span></div>
              <div className="event-item"><span>绑定时间</span><span>{authStatus.bind_info?.bind_time || '--'}</span></div>
              <div className="event-item"><span>解绑时间</span><span>{authStatus.bind_info?.unbind_time || '--'}</span></div>
              <div className="event-item"><span>token 状态</span><span>{authStatus.token_record?.status || '--'}</span></div>
              <div className="event-item full"><span>错误信息</span><span>{authStatus.token_record?.error_message || '--'}</span></div>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  )
}

export default function App() {
  const isAuthCallbackPage = window.location.pathname === '/auth/callback'

  if (isAuthCallbackPage) {
    return <AuthCallbackPage />
  }

  const [currentPage, setCurrentPage] = useState('leads')
  const [stats, setStats] = useState({})
  const [leads, setLeads] = useState([])
  const [conversations, setConversations] = useState([])
  const [messages, setMessages] = useState([])
  const [quickReplies, setQuickReplies] = useState([])
  const [unreadSummary, setUnreadSummary] = useState({})
  const [activeConversation, setActiveConversation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [authTestResult, setAuthTestResult] = useState(null)
  const [authTestLoading, setAuthTestLoading] = useState(false)
  const [eventLog, setEventLog] = useState([])
  const [eventLoading, setEventLoading] = useState(false)
  const [apiLog, setApiLog] = useState(null)
  const [workspaceAuthStatus, setWorkspaceAuthStatus] = useState(null)
  const [workspaceAuthLoading, setWorkspaceAuthLoading] = useState(true)
  const [videoForm, setVideoForm] = useState(defaultVideoForm)
  const [videoTasks, setVideoTasks] = useState([])
  const [activeVideoTask, setActiveVideoTask] = useState(null)
  const [videoSubmitting, setVideoSubmitting] = useState(false)
  const [videoTaskLoading, setVideoTaskLoading] = useState(false)
  const [videoCreateResult, setVideoCreateResult] = useState(null)
  const [reviewForm, setReviewForm] = useState(defaultReviewForm)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewResult, setReviewResult] = useState(null)

  async function loadWorkspaceData() {
    setLoading(true)
    setWorkspaceAuthLoading(true)
    try {
      const [statsRes, leadsRes, conversationsRes, quickRepliesRes, unreadRes, authStatusRes, videoTasksRes] = await Promise.all([
        fetch('/dashboard/lead-stats'),
        fetch('/leads?page=1&page_size=20'),
        fetch('/conversations'),
        fetch('/quick-replies'),
        fetch('/conversations/unread-summary'),
        fetch('/auth-status'),
        fetch('/aigc/video-tasks'),
      ])
      const statsData = await statsRes.json()
      const leadsData = await leadsRes.json()
      const conversationsData = await conversationsRes.json()
      const quickRepliesData = await quickRepliesRes.json()
      const unreadData = await unreadRes.json()
      const authStatusData = await authStatusRes.json()
      const videoTasksData = await videoTasksRes.json()

      setStats(statsData)
      setLeads(leadsData.items || [])
      setConversations(conversationsData || [])
      setQuickReplies(quickRepliesData || [])
      setUnreadSummary(unreadData || {})
      setWorkspaceAuthStatus(authStatusData?.data || null)
      setVideoTasks(Array.isArray(videoTasksData) ? videoTasksData : [])

      if (conversationsData?.length) {
        setActiveConversation((prev) =>
          prev
            ? conversationsData.find((item) => item.conversation_short_id === prev.conversation_short_id) || conversationsData[0]
            : conversationsData[0],
        )
      }
      if (Array.isArray(videoTasksData) && videoTasksData.length) {
        setActiveVideoTask((prev) => videoTasksData.find((item) => item.task_id === prev?.task_id) || videoTasksData[0])
      }
    } finally {
      setLoading(false)
      setWorkspaceAuthLoading(false)
    }
  }

  useEffect(() => {
    loadWorkspaceData()
  }, [])

  useEffect(() => {
    async function loadMessages() {
      if (!activeConversation?.conversation_short_id) {
        setMessages([])
        return
      }
      const res = await fetch(`/conversations/${activeConversation.conversation_short_id}/messages`)
      const data = await res.json()
      setMessages(data || [])
    }

    loadMessages()
  }, [activeConversation])

  async function testDouyinAuth() {
    setAuthTestLoading(true)
    setAuthTestResult(null)
    try {
      const res = await fetch('/douyin/get-auth-url/configured', { method: 'POST' })
      const data = await res.json()
      setAuthTestResult({
        ok: res.ok,
        status: res.status,
        data,
      })
    } catch (error) {
      setAuthTestResult({
        ok: false,
        status: 0,
        data: { msg: error.message },
      })
    } finally {
      setAuthTestLoading(false)
    }
  }

  async function refreshEventLogs() {
    setEventLoading(true)
    try {
      const res = await fetch('/events')
      const data = await res.json()
      setEventLog(Array.isArray(data) ? data.slice(0, 5) : [])
    } finally {
      setEventLoading(false)
    }
  }

  async function refreshApiLog() {
    const res = await fetch('/api-call-logs')
    const data = await res.json()
    setApiLog(Array.isArray(data) && data.length ? data[0] : null)
  }

  useEffect(() => {
    if (!authTestResult?.ok || !authTestResult.data?.data?.auth_url) return undefined
    refreshEventLogs()
    refreshApiLog()
    const timer = setInterval(() => {
      refreshEventLogs()
      refreshApiLog()
    }, 5000)
    return () => clearInterval(timer)
  }, [authTestResult])

  function handleVideoFormChange(event) {
    const { name, value, checked, type } = event.target
    setVideoForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  function handleReviewFormChange(event) {
    const { name, value } = event.target
    setReviewForm((prev) => ({ ...prev, [name]: value }))
  }

  async function loadVideoTaskList(selectTaskId) {
    const res = await fetch('/aigc/video-tasks')
    const data = await res.json()
    const tasks = Array.isArray(data) ? data : []
    setVideoTasks(tasks)
    if (tasks.length) {
      const target = tasks.find((item) => item.task_id === selectTaskId) || tasks[0]
      setActiveVideoTask(target)
    } else {
      setActiveVideoTask(null)
    }
  }

  async function createVideoTask() {
    setVideoSubmitting(true)
    setVideoCreateResult(null)
    try {
      const payload = {
        account_id: videoForm.account_id ? Number(videoForm.account_id) : undefined,
        account_type: videoForm.account_type || undefined,
        task_type: videoForm.task_type,
        title: videoForm.title || undefined,
        product_name: videoForm.product_name || undefined,
        prompt: videoForm.prompt || undefined,
        script: videoForm.script || undefined,
        selling_points: parseLines(videoForm.selling_points),
        benefit_points: parseLines(videoForm.benefit_points),
        video_element_ids: parseNumberLines(videoForm.video_element_ids),
        material_urls: parseLines(videoForm.material_urls),
        image_urls: parseLines(videoForm.image_urls),
        count: videoForm.count ? Number(videoForm.count) : 1,
        task_name: videoForm.task_name || undefined,
        is_auto_save_all_result: Boolean(videoForm.is_auto_save_all_result),
      }
      const res = await fetch('/aigc/video-tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok || data?.code !== 0) {
        throw new Error(data?.msg || '创建视频任务失败')
      }
      setVideoCreateResult({ ok: true, message: `任务 ${data.data.task_id} 创建成功` })
      setVideoForm(defaultVideoForm)
      await loadVideoTaskList(data.data.task_id)
      await refreshApiLog()
    } catch (error) {
      setVideoCreateResult({ ok: false, message: error.message || '创建视频任务失败' })
    } finally {
      setVideoSubmitting(false)
    }
  }

  async function refreshVideoTask(taskId) {
    setVideoTaskLoading(true)
    try {
      const res = await fetch(`/aigc/video-tasks/${taskId}/refresh`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok || data?.code !== 0) {
        throw new Error(data?.msg || '刷新任务失败')
      }
      await loadVideoTaskList(taskId)
      await refreshApiLog()
    } catch (error) {
      setVideoCreateResult({ ok: false, message: error.message || '刷新任务失败' })
    } finally {
      setVideoTaskLoading(false)
    }
  }

  async function runReviewAction(action) {
    setReviewLoading(true)
    setReviewResult(null)
    try {
      let path = '/review/suggestions'
      let payload = {}
      if (action === 'suggestions') {
        path = '/review/suggestions'
        payload = reviewForm.suggestions_payload ? JSON.parse(reviewForm.suggestions_payload) : {}
      } else if (action === 'cross-account') {
        path = '/review/cross-account'
        payload = reviewForm.cross_account_payload ? JSON.parse(reviewForm.cross_account_payload) : {}
      } else if (action === 'adopt-task') {
        path = '/review/adopt-task'
        payload = reviewForm.adopt_task_payload ? JSON.parse(reviewForm.adopt_task_payload) : {}
      } else {
        path = '/review/adopt-task/result'
        payload = reviewForm.adopt_result_payload ? JSON.parse(reviewForm.adopt_result_payload) : {}
      }

      const res = await fetch(path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ payload }),
      })
      const data = await res.json()
      setReviewResult(data)
      await refreshApiLog()
    } catch (error) {
      setReviewResult({ code: -1, message: error.message || '审核接口调用失败' })
    } finally {
      setReviewLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <small>Douyin DM Lead Hub</small>
          <strong>会话、线索与视频剪辑工作台</strong>
          <span>保留私信运营主流程，同时新增视频剪辑板块，支持后续接入新的 AIGC 成片接口。</span>
        </div>

        <section className="menu-group compact">
          <h4>工作页面</h4>
          {workspacePages.map((page) => (
            <button
              key={page.key}
              className={`menu-item card ${page.key === currentPage ? 'active' : ''}`}
              onClick={() => setCurrentPage(page.key)}
            >
              <b>{page.label}</b>
              <span>{page.hint}</span>
            </button>
          ))}
        </section>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <small>客户运营工作台</small>
            <h1>
              {currentPage === 'leads'
                ? '线索管理'
                : currentPage === 'conversations'
                  ? '会话管理'
                  : '视频剪辑'}
            </h1>
          </div>
          <div className="topbar-actions">
            <button className="chip">前端 8010 / 后端 8081</button>
            <button className="primary-btn" onClick={testDouyinAuth} disabled={authTestLoading}>
              {authTestLoading ? '测试中...' : '测试抖音接口'}
            </button>
          </div>
        </header>

        <AuthStatusCard authStatus={workspaceAuthStatus} loading={workspaceAuthLoading} />

        {authTestResult ? (
          <section className={`banner ${authTestResult.ok ? 'info' : 'warning'}`}>
            <strong>抖音接口测试：</strong>
            <div className="auth-result">
              <div>
                {authTestResult.ok ? '成功' : '失败'} / HTTP {authTestResult.status}
              </div>
              <div className="auth-url">
                {authTestResult.data?.data?.auth_url ? (
                  <a href={authTestResult.data.data.auth_url} target="_blank" rel="noreferrer">
                    {authTestResult.data.data.auth_url}
                  </a>
                ) : (
                  <span>{JSON.stringify(authTestResult.data)}</span>
                )}
              </div>
              <div className="auth-actions">
                <button className="chip" onClick={refreshEventLogs} disabled={eventLoading}>
                  {eventLoading ? '刷新中...' : '授权后查看回调'}
                </button>
              </div>
            </div>
          </section>
        ) : null}

        {eventLog.length ? (
          <section className="table-card">
            <div className="table-header">
              <strong>最近回调结果</strong>
            </div>
            <div className="event-list">
              {eventLog.map((item) => (
                <div key={item.id} className="event-item">
                  <span>{item.event}</span>
                  <span>{item.from_user_id || '--'}</span>
                  <span>{item.conversation_short_id || '--'}</span>
                  <span>{item.create_time || '--'}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {apiLog ? (
          <section className="table-card">
            <div className="table-header">
              <strong>最近接口日志</strong>
            </div>
            <div className="event-list">
              <div className="event-item">
                <span>{apiLog.api_path}</span>
                <span>{apiLog.http_status}</span>
                <span>{apiLog.error_type || '--'}</span>
                <span>{apiLog.created_at}</span>
              </div>
            </div>
          </section>
        ) : null}

        {currentPage === 'leads' ? (
          <LeadPage stats={stats} leads={leads} loading={loading} />
        ) : null}

        {currentPage === 'conversations' ? (
          <ConversationPage
            conversations={conversations}
            activeConversation={activeConversation}
            messages={messages}
            quickReplies={quickReplies}
            unreadSummary={unreadSummary}
            loading={loading}
            onSelectConversation={setActiveConversation}
          />
        ) : null}

        {currentPage === 'video-edit' ? (
          <VideoEditPage
            videoForm={videoForm}
            onChange={handleVideoFormChange}
            onSubmit={createVideoTask}
            submitting={videoSubmitting}
            tasks={videoTasks}
            activeTask={activeVideoTask}
            onSelectTask={setActiveVideoTask}
            onRefreshTask={refreshVideoTask}
            taskLoading={videoTaskLoading}
            createResult={videoCreateResult}
          />
        ) : null}

        {currentPage === 'review-test' ? (
          <ReviewTestPage
            reviewForm={reviewForm}
            onChange={handleReviewFormChange}
            onRunAction={runReviewAction}
            reviewLoading={reviewLoading}
            reviewResult={reviewResult}
          />
        ) : null}
      </main>
    </div>
  )
}
