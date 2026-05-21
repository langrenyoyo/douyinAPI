import { useEffect, useState } from 'react'
import './index.css'

const workspacePages = [
  { key: 'conversations', label: '会话管理', hint: '咨询承接与客服沟通' },
  { key: 'leads', label: '线索管理', hint: '线索查看与跟进分配' },
]

function formatDateTime(value) {
  if (!value) return '--'
  const num = Number(value)
  if (!Number.isFinite(num)) return value
  return new Date(num).toLocaleString('zh-CN', { hour12: false })
}

function LeadPage({ stats, leads, loading }) {
  return (
    <div className="page-shell">
      <div className="hero-cards">
        <article className="hero-card">
          <span>全部线索</span>
          <strong>{stats.total_leads ?? 0}</strong>
          <em>环比 +30%</em>
        </article>
        <article className="hero-card ghost">
          <span>待分配</span>
          <strong>{stats.pending_leads ?? 0}</strong>
          <em>待处理</em>
        </article>
        <article className="hero-card">
          <span>跟进中</span>
          <strong>{stats.following_leads ?? 0}</strong>
          <em>线索承接中</em>
        </article>
        <article className="hero-card compare">
          <span>行业对比</span>
          <strong>{stats.unread_conversations ?? 0}</strong>
          <em>当前未读会话</em>
        </article>
      </div>

      <div className="banner warning">
        检测到企业号存在未授权营销账户，将会导致部分 dou+ 线索不能跟进，建议尽快完成授权。
      </div>

      <div className="toolbar">
        <div className="toolbar-left">
          <button className="chip active">按电话</button>
          <input className="search" placeholder="请输入内容" />
          <button className="chip">创建时间</button>
          <button className="chip">互动类型</button>
        </div>
        <div className="toolbar-right">
          <button className="link-btn">更多筛选项</button>
          <button className="chip">重置</button>
        </div>
      </div>

      <section className="table-card">
        <div className="table-header">
          <div className="tabs">
            <button className="tab active">全部 ({stats.total_leads ?? 0})</button>
            <button className="tab">待分配 ({stats.pending_leads ?? 0})</button>
            <button className="tab">待跟进 ({stats.following_leads ?? 0})</button>
          </div>
          <div className="header-actions">
            <span className="status-dot">去重中</span>
            <button className="chip">自定义列表</button>
            <button className="primary-btn">导出数据</button>
          </div>
        </div>

        <div className="lead-table">
          <div className="lead-row head">
            <span>姓名</span>
            <span>电话</span>
            <span>微信</span>
            <span>线索创建时间</span>
            <span>互动类型</span>
            <span>线索类型</span>
            <span>最新互动记录</span>
            <span>线索渠道</span>
            <span>操作</span>
          </div>
          {loading ? <div className="empty">加载中...</div> : null}
          {!loading && leads.length === 0 ? <div className="empty">暂无线索数据</div> : null}
          {!loading
            ? leads.map((lead) => (
                <div className="lead-row" key={lead.open_id}>
                  <span className="lead-user">
                    <img
                      src={lead.avatar_url || 'https://placehold.co/56x56/e9eefc/4a5cc7?text=%E7%BA%BF'}
                      alt={lead.display_name}
                    />
                    <b>{lead.display_name || '未命名'}</b>
                  </span>
                  <span>{lead.phone || '******5232'}</span>
                  <span>{lead.wechat || '--'}</span>
                  <span>{formatDateTime(lead.latest_active_time)}</span>
                  <span>{lead.latest_scene || '私信'}</span>
                  <span>{lead.lead_type || '字节-在线咨询'}</span>
                  <span>{lead.last_interaction_record || '--'}</span>
                  <span>{lead.lead_channel || '企业号'}</span>
                  <span className="row-actions">分配 通话 私信 详情</span>
                </div>
              ))
            : null}
        </div>
      </section>
    </div>
  )
}

function ConversationPage({ conversations, activeConversation, messages, quickReplies, unreadSummary, loading, onSelectConversation }) {
  return (
    <div className="conversation-shell">
      <div className="conversation-alerts">
        <div className="banner warning">此网页浏览器通知已关闭，您将收不到用户新进线、新消息等提示。</div>
        <div className="banner info">为优化线索跟进体验，当前私信线索生成和落入规则已升级。</div>
      </div>

      <div className="conversation-layout">
        <aside className="conversation-list-card">
          <div className="list-toolbar">
            <button className="chip">离线</button>
            <button className="chip">通知设置</button>
          </div>
          <input className="search full" placeholder="联系人/群名称" />
          <div className="list-tabs">
            <button className="tab active">单聊</button>
            <button className="tab">群聊</button>
          </div>
          <div className="list-filter-row">
            <button className="link-btn">来源</button>
            <button className="chip">全部状态</button>
            <button className="link-btn">更多</button>
          </div>

          <div className="conversation-list">
            {loading ? <div className="empty">加载中...</div> : null}
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
                  alt={item.display_name}
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
              <span>今日接待数</span>
              <strong>{conversations.length}</strong>
            </div>
            <div>
              <span>留资数</span>
              <strong>{unreadSummary.unread_conversations ?? 0}</strong>
            </div>
            <div>
              <span>15s首响率</span>
              <strong>22.4%</strong>
            </div>
          </div>

          <div className="chat-header">
            <div className="chat-user">
              <img
                src={activeConversation?.avatar_url || 'https://placehold.co/48x48/e9eefc/4a5cc7?text=%E8%81%8A'}
                alt={activeConversation?.display_name}
              />
              <div>
                <strong>{activeConversation?.display_name || '请选择会话'}</strong>
                <span>未读消息 {activeConversation?.unread_count ?? 0}</span>
              </div>
            </div>
            <div className="chat-actions">☆ ⍟</div>
          </div>

          <div className="message-stream">
            {!activeConversation ? <div className="empty">请选择左侧会话查看详情</div> : null}
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
            <div className="composer-tools">☺ 📁 🖼 ✂ 👥</div>
            <textarea placeholder="回复内容，可按 Enter 键发送，按 Alt+Enter 换行" />
            <div className="quick-replies">
              {quickReplies.slice(0, 3).map((item) => (
                <span key={item.id}>{item.title}</span>
              ))}
            </div>
          </div>
        </section>

        <aside className="detail-card">
          <h3>备注</h3>
          <div className="detail-grid">
            <span>姓名</span>
            <strong>{activeConversation?.display_name || '--'}</strong>
            <span>电话</span>
            <strong>******5232</strong>
            <span>微信</span>
            <strong>--</strong>
            <span>地区</span>
            <strong>--</strong>
            <span>地址</span>
            <strong>--</strong>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default function App() {
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

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [statsRes, leadsRes, conversationsRes, quickRepliesRes, unreadRes] = await Promise.all([
          fetch('/dashboard/lead-stats'),
          fetch('/leads?page=1&page_size=20'),
          fetch('/conversations'),
          fetch('/quick-replies'),
          fetch('/conversations/unread-summary'),
        ])
        const statsData = await statsRes.json()
        const leadsData = await leadsRes.json()
        const conversationsData = await conversationsRes.json()
        const quickRepliesData = await quickRepliesRes.json()
        const unreadData = await unreadRes.json()

        setStats(statsData)
        setLeads(leadsData.items || [])
        setConversations(conversationsData || [])
        setQuickReplies(quickRepliesData || [])
        setUnreadSummary(unreadData || {})

        if (conversationsData?.length) {
          setActiveConversation(conversationsData[0])
        }
      } finally {
        setLoading(false)
      }
    }

    loadData()
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <small>Douyin CRM</small>
          <strong>会话与线索工作台</strong>
          <span>仅保留客服最常用的两个页面，聚焦承接与转化。</span>
        </div>

        <section className="menu-group compact">
          <h4>工作页面</h4>
          {workspacePages.map((page) => (
            <button
              key={page.key}
              className={`menu-item card ${(page.key === currentPage) ? 'active' : ''}`}
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
            <h1>{currentPage === 'leads' ? '线索管理' : '会话管理'}</h1>
          </div>
          <div className="topbar-actions">
            <button className="chip">前端 8010 / 后端 8081</button>
            <button className="primary-btn" onClick={testDouyinAuth} disabled={authTestLoading}>
              {authTestLoading ? '测试中...' : '测试抖音接口'}
            </button>
          </div>
        </header>

        {authTestResult ? (
          <section className={`banner ${authTestResult.ok ? 'info' : 'warning'}`}>
            <strong>抖音接口测试：</strong>
            <span>
              {authTestResult.ok ? '成功' : '失败'} / HTTP {authTestResult.status} / {JSON.stringify(authTestResult.data)}
            </span>
          </section>
        ) : null}

        {currentPage === 'leads' ? (
          <LeadPage stats={stats} leads={leads} loading={loading} />
        ) : (
          <ConversationPage
            conversations={conversations}
            activeConversation={activeConversation}
            messages={messages}
            quickReplies={quickReplies}
            unreadSummary={unreadSummary}
            loading={loading}
            onSelectConversation={setActiveConversation}
          />
        )}
      </main>
    </div>
  )
}
