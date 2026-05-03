import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

function App() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Sundarr Web Console</p>
        <h1>搜索云端媒体，归档回家。</h1>
        <p>
          MVP 控制台会覆盖搜索、SMB 配置、媒体源配置、任务创建和进度控制。
          当前页面是 Phase 0 骨架。
        </p>
        <a href="/health">检查 API 健康状态</a>
      </section>
    </main>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
