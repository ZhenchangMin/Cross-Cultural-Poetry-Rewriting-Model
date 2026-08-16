<template>
  <div class="page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <NavBar />

    <main class="disclaimer">
      <section class="hero">
        <h1 class="hero-title">免责声明</h1>
        <p class="hero-subtitle">Disclaimer</p>
        <div class="hero-rule"></div>
        <p class="hero-quote">
          诗渡是一项学术研究原型，<br />
          所有输入与输出仅供研究与演示之用。
        </p>
        <p class="hero-quote-en">
          Research prototype — for academic demonstration only.
        </p>
      </section>

      <section class="notice">
        <div class="notice-stamp">
          <span class="stamp-zh">声明</span>
          <span class="stamp-en">Notice</span>
        </div>
        <p class="notice-text">
          使用本系统即表示您已阅读并同意以下各项条款。
          若不同意其中任何一条，请立即停止使用本系统。
        </p>
      </section>

      <section class="clauses">
        <article class="clause">
          <div class="clause-num">01</div>
          <h3 class="clause-title">关于用户输入</h3>
          <p class="clause-sub">User Input</p>
          <p class="clause-body">
            用户在本系统中输入的任何文本（包括但不限于诗歌、词语、段落、私人创作）
            <strong>完全由用户本人负责</strong>。用户须确保所输入内容不侵犯任何第三方的著作权、人格权或其他合法权益，且不违反所在司法辖区的法律法规。
            
            本项目团队不会审核、监控或主动留存用户输入内容用于本研究目的以外的用途。
          </p>
        </article>

        <article class="clause">
          <div class="clause-num">02</div>
          <h3 class="clause-title">关于 AI 生成内容</h3>
          <p class="clause-sub">AI-Generated Output</p>
          <p class="clause-body">
            本系统的所有输出由<em>神经网络模型自动生成</em>，<strong>不代表项目团队、所属机构或任何相关方的观点、立场和情感倾向</strong>。
            生成结果可能包含事实错误、语义偏差、文化误读，或在罕见情况下出现不当表达。
            这是当前生成式模型的<strong>固有局限</strong>，并非人工编辑。
            用户在引用、转载或进一步传播相关内容前，应自行判断与核实。
          </p>
        </article>

        <article class="clause">
          <div class="clause-num">03</div>
          <h3 class="clause-title">使用风险与责任</h3>
          <p class="clause-sub">Use at Your Own Risk</p>
          <p class="clause-body">
            用户对其使用本系统输出内容所产生的<strong>一切后果自行承担责任</strong>。
            
          </p>
        </article>

        <article class="clause">
          <div class="clause-num">04</div>
          <h3 class="clause-title">学术研究性质</h3>
          <p class="clause-sub">Research Nature</p>
          <p class="clause-body">
            本系统是<strong>南京大学大学生创新创业训练计划</strong>的学术研究原型，
            旨在探索跨语言、跨文化诗歌转写的可行性，<em>不作为商业产品提供</em>。
          </p>
        </article>
      </section>

      <section class="contact">
        <div class="contact-rule"></div>
        <p class="contact-text">
          如对本声明有任何疑问，或认为生成内容侵犯您的权益，
          请通过以下渠道与我们联系。
        </p>
        <p class="contact-en">
          For inquiries, reach us via the channels below.
        </p>

        <div class="contact-grid">
          <a
            class="contact-card"
            href="mailto:mmm493027@gmail.com"
          >
            <div class="contact-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3 7l9 6 9-6" />
              </svg>
            </div>
            <div class="contact-meta">
              <span class="contact-label">Email</span>
              <span class="contact-value">mmm493027@gmail.com</span>
            </div>
          </a>

          <a
            class="contact-card"
            href="https://github.com/ZhenchangMin/Cross-Cultural-Poetry-Rewriting-Model"
            target="_blank"
            rel="noopener noreferrer"
          >
            <div class="contact-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 .5C5.73.5.66 5.57.66 11.84c0 5.01 3.25 9.26 7.76 10.76.57.1.78-.25.78-.55 0-.27-.01-1-.02-1.96-3.16.69-3.83-1.52-3.83-1.52-.52-1.31-1.27-1.66-1.27-1.66-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.75 2.68 1.24 3.33.95.1-.74.4-1.24.72-1.53-2.52-.29-5.18-1.26-5.18-5.6 0-1.24.44-2.25 1.17-3.04-.12-.29-.51-1.44.11-3 0 0 .96-.31 3.14 1.16.91-.25 1.88-.38 2.85-.39.97.01 1.94.14 2.85.39 2.18-1.47 3.14-1.16 3.14-1.16.62 1.56.23 2.71.11 3 .73.79 1.17 1.8 1.17 3.04 0 4.35-2.67 5.31-5.21 5.59.41.35.77 1.04.77 2.1 0 1.52-.01 2.74-.01 3.11 0 .3.21.66.79.55 4.51-1.5 7.75-5.75 7.75-10.76C23.34 5.57 18.27.5 12 .5z" />
              </svg>
            </div>
            <div class="contact-meta">
              <span class="contact-label">GitHub</span>
              <span class="contact-value">ZhenchangMin / Cross-Cultural-Poetry-Rewriting-Model</span>
            </div>
          </a>
        </div>
      </section>

      <section class="footnote">
        <div class="foot-rule"></div>
        <p class="foot-text">
          诗渡&nbsp;·&nbsp;Poem&nbsp;Bridge
        </p>
      </section>
    </main>
  </div>
</template>

<script setup>
import NavBar from '../components/NavBar.vue'
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0 48px 60px;
  position: relative;
  overflow-x: hidden;
}

.orb {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(100px);
  z-index: 0;
}
.orb-1 {
  width: 500px; height: 500px;
  top: -160px; left: -140px;
  background: radial-gradient(circle, rgba(192, 56, 40, 0.07) 0%, transparent 65%);
}
.orb-2 {
  width: 600px; height: 600px;
  bottom: -200px; right: -140px;
  background: radial-gradient(circle, rgba(160, 104, 24, 0.08) 0%, transparent 65%);
}

.disclaimer {
  position: relative;
  z-index: 1;
  max-width: 920px;
  margin: 0 auto;
  width: 100%;
  padding-top: 24px;
}

/* ── Hero ── */
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 0 40px;
}

.hero-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 38px;
  font-weight: 500;
  letter-spacing: 0.22em;
  color: var(--text-parchment);
  line-height: 1.2;
}

.hero-subtitle {
  margin-top: 10px;
  font-family: 'Cinzel', serif;
  font-size: 12px;
  letter-spacing: 0.36em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.hero-rule {
  width: 72px;
  height: 1px;
  background: var(--red);
  opacity: 0.55;
  margin: 28px 0 26px;
}

.hero-quote {
  font-family: 'Noto Serif SC', serif;
  font-size: 16px;
  line-height: 2;
  color: var(--text-aged);
  letter-spacing: 0.08em;
}

.hero-quote-en {
  margin-top: 14px;
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--text-faded);
  text-transform: uppercase;
}

/* ── Notice banner ── */
.notice {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 22px 24px;
  margin-top: 8px;
  background: var(--red-ghost);
  border: 1px solid var(--red-border);
  border-left: 3px solid var(--red);
  border-radius: 4px;
}

.notice-stamp {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border: 1.5px solid var(--red);
  border-radius: 4px;
  color: var(--red);
  background: rgba(192, 56, 40, 0.04);
}
.stamp-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.18em;
  line-height: 1.1;
}
.stamp-en {
  margin-top: 4px;
  font-family: 'Cinzel', serif;
  font-size: 8.5px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  opacity: 0.8;
}

.notice-text {
  flex: 1;
  font-family: 'Noto Serif SC', serif;
  font-size: 14px;
  line-height: 1.95;
  color: var(--text-aged);
  letter-spacing: 0.04em;
}

/* ── Clauses ── */
.clauses {
  margin-top: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.clause {
  position: relative;
  padding: 26px 26px 24px;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: var(--shadow);
  transition: border-color 0.28s ease, box-shadow 0.28s ease;
}
.clause:hover {
  border-color: var(--border-bright);
  box-shadow: var(--glow-strong);
}

.clause-num {
  position: absolute;
  top: 14px;
  right: 18px;
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--gold-dim);
  opacity: 0.6;
}

.clause-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: 0.16em;
  color: var(--text-parchment);
  line-height: 1.2;
}
.clause-sub {
  margin-top: 4px;
  font-family: 'Cinzel', serif;
  font-size: 9.5px;
  letter-spacing: 0.26em;
  color: var(--red);
  opacity: 0.75;
  text-transform: uppercase;
}

.clause-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  font-family: 'Noto Serif SC', serif;
  font-size: 13.5px;
  line-height: 1.95;
  color: var(--text-aged);
  letter-spacing: 0.03em;
}
.clause-body strong {
  color: var(--red);
  font-weight: 500;
}
.clause-body em {
  font-style: normal;
  color: var(--text-parchment);
  border-bottom: 1px dashed var(--border-bright);
  padding-bottom: 1px;
}

/* ── Contact ── */
.contact {
  margin-top: 44px;
  padding: 24px 4px 8px;
  text-align: center;
}

.contact-rule {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, transparent 0%, var(--border) 30%, var(--border) 70%, transparent 100%);
  margin-bottom: 22px;
}

.contact-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 14px;
  line-height: 1.95;
  color: var(--text-aged);
  letter-spacing: 0.05em;
}

.contact-en {
  margin-top: 8px;
  font-family: 'Cinzel', serif;
  font-size: 10px;
  letter-spacing: 0.24em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.contact-grid {
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  text-align: left;
}

.contact-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
}
.contact-card:hover {
  border-color: var(--red-border);
  transform: translateY(-2px);
  box-shadow: var(--glow-strong);
}

.contact-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--red-border);
  border-radius: 4px;
  background: var(--red-ghost);
  color: var(--red);
}

.contact-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.contact-label {
  font-family: 'Cinzel', serif;
  font-size: 9.5px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--red);
  opacity: 0.8;
}

.contact-value {
  font-family: 'Cinzel', serif;
  font-size: 12.5px;
  letter-spacing: 0.04em;
  color: var(--text-parchment);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Footnote ── */
.footnote {
  margin-top: 48px;
  text-align: center;
}

.foot-rule {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, transparent 0%, var(--border) 30%, var(--border) 70%, transparent 100%);
  margin-bottom: 22px;
}

.foot-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 0.22em;
  color: var(--text-aged);
}

/* ── Responsive ── */
@media (max-width: 820px) {
  .page { padding: 0 24px 48px; }
  .hero-title { font-size: 30px; }
  .notice {
    flex-direction: column;
    align-items: stretch;
  }
  .notice-stamp {
    width: 100%;
    height: auto;
    flex-direction: row;
    gap: 10px;
    padding: 8px 12px;
  }
  .stamp-en { margin-top: 0; }
  .contact-grid { grid-template-columns: 1fr; }

  /* 窄屏放开 contact-value 的 nowrap，让长 repo 路径换行展示完整 */
  .contact-value {
    white-space: normal;
    word-break: break-all;
    font-size: 12px;
    line-height: 1.5;
  }
}
</style>
