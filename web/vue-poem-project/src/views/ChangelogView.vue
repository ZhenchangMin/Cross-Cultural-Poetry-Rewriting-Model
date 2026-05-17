<template>
  <div class="page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <NavBar />

    <main class="changelog">
      <section class="hero">
        <h1 class="hero-title">更新日志</h1>
        <p class="hero-subtitle">Changelog</p>
        <div class="hero-rule"></div>
        <p class="hero-quote">
          一行行代码，<br />
          一次次推敲，<br />
          通往那座桥。
        </p>
      </section>

      <section class="timeline">
        <article
          v-for="(rel, idx) in releases"
          :key="rel.version"
          class="entry"
          :class="{ 'entry--current': idx === 0 }"
        >
          <div class="entry-marker">
            <span class="dot"></span>
            <span v-if="idx !== releases.length - 1" class="rail"></span>
          </div>

          <div class="entry-card">
            <header class="entry-head">
              <div class="version-row">
                <span class="version">{{ rel.version }}</span>
                <span v-if="idx === 0" class="badge-current">当前 · Current</span>
              </div>
              <span class="date">{{ rel.date }}</span>
            </header>

            <h3 class="entry-title">
              <span class="zh">{{ rel.title }}</span>
              <span class="en">{{ rel.en }}</span>
            </h3>

            <ul class="entry-items">
              <li v-for="(it, i) in rel.items" :key="i">
                <span class="tag" :class="`tag--${it.type}`">{{ it.type }}</span>
                <span class="text" v-html="it.text"></span>
              </li>
            </ul>
          </div>
        </article>
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

const releases = [
  {
    version: 'v1.3.0',
    date: '2026.05',
    title: '用户体验改善',
    en: 'UX Improvement',
    items: [
      { type: 'feat', text: '上线<strong>【关于我们】</strong>项目介绍页' },
      { type: 'feat', text: '上线<strong>【更新日志】</strong>版本演进时间线' },
      { type: 'feat', text: '生成结果结构化输出：转写结果 + 转写思路' },
      { type: 'fix',  text: '修复加载动画截断、滑块尺寸、滚动条配色等细节' }
    ]
  },
  {
    version: 'v1.2.0',
    date: '2026.04',
    title: '前后端联调',
    en: 'Full-Stack Integration',
    items: [
      { type: 'feat', text: '语言选择器：俄 / 韩 / 中 双向切换' },
      { type: 'feat', text: '文化适配强度滑块（基于 Venuti 异化-归化理论）' },
      { type: 'feat', text: '前端 Vue 3 + 后端 Spring Boot 3.5' },
      { type: 'feat', text: '部署上线' }
    ]
  },
  {
    version: 'v1.1.0',
    date: '2026.03',
    title: '三位一体模型',
    en: 'Trinity Model',
    items: [
      { type: 'feat', text: '<strong>TrinityRewriter</strong>：XLM-R + ProjectionMLP + CultureEmbedding + Qwen2.5 LoRA' },
      { type: 'feat', text: '语料采集与训练集构建' },
      { type: 'feat', text: '格律 / 押韵约束评分器' }
    ]
  },
  {
    version: 'v1.0.1',
    date: '2025.12',
    title: '项目立项',
    en: 'Project Kickoff',
    items: [
      { type: 'feat', text: '<strong>南京大学</strong>大学生创新创业训练计划项目立项' },
      { type: 'feat', text: '理论调研：Venuti 异化/归化、XLM-R 多语言对齐、LoRA 微调' }
    ]
  }
]
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

.changelog {
  position: relative;
  z-index: 1;
  max-width: 880px;
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
  margin: 28px 0 24px;
}
.hero-quote {
  font-family: 'Noto Serif SC', serif;
  font-size: 17px;
  line-height: 2;
  color: var(--text-aged);
  letter-spacing: 0.08em;
}

/* ── Timeline ── */
.timeline {
  margin-top: 24px;
  padding: 8px 4px;
}

.entry {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 18px;
  padding-bottom: 28px;
  position: relative;
}

.entry-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 14px;
  position: relative;
}

.dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--ink-surface);
  border: 2px solid var(--gold-dim);
  flex-shrink: 0;
  z-index: 2;
  transition: all 0.3s ease;
}

.entry--current .dot {
  background: var(--red);
  border-color: var(--red);
  box-shadow: 0 0 0 4px var(--red-ghost), 0 0 12px rgba(192, 56, 40, 0.35);
  animation: pulse 2.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px var(--red-ghost), 0 0 8px rgba(192, 56, 40, 0.25); }
  50%       { box-shadow: 0 0 0 6px var(--red-ghost), 0 0 18px rgba(192, 56, 40, 0.45); }
}

.rail {
  flex: 1;
  width: 1px;
  margin-top: 6px;
  background: linear-gradient(to bottom, var(--border-bright) 0%, var(--border) 60%, transparent 100%);
}

.entry-card {
  padding: 18px 22px 20px;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: var(--shadow);
  transition: border-color 0.28s ease, box-shadow 0.28s ease;
}
.entry-card:hover {
  border-color: var(--border-bright);
  box-shadow: var(--glow-strong);
}

.entry-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.version-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.version {
  font-family: 'Cinzel', serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--text-parchment);
}

.badge-current {
  display: inline-block;
  padding: 2px 9px;
  font-family: 'Noto Serif SC', serif;
  font-size: 10.5px;
  letter-spacing: 0.18em;
  color: var(--red);
  background: var(--red-ghost);
  border: 1px solid var(--red-border);
  border-radius: 2px;
}

.date {
  font-family: 'Cinzel', serif;
  font-size: 11.5px;
  letter-spacing: 0.16em;
  color: var(--gold-warm);
}

.entry-title {
  margin-top: 12px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.entry-title .zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: 0.16em;
  color: var(--text-parchment);
}
.entry-title .en {
  font-family: 'Cinzel', serif;
  font-size: 10px;
  letter-spacing: 0.28em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.entry-items {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.entry-items li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-family: 'Noto Serif SC', serif;
  font-size: 13.5px;
  line-height: 1.9;
  color: var(--text-aged);
  letter-spacing: 0.03em;
}

.tag {
  flex-shrink: 0;
  display: inline-block;
  min-width: 50px;
  text-align: center;
  padding: 1px 6px;
  font-family: 'Cinzel', serif;
  font-size: 9.5px;
  font-weight: 500;
  letter-spacing: 0.16em;
  border-radius: 2px;
  text-transform: uppercase;
  border: 1px solid transparent;
}
.tag--feat {
  color: var(--red);
  background: var(--red-ghost);
  border-color: var(--red-border);
}
.tag--fix {
  color: var(--gold-warm);
  background: var(--gold-ghost);
  border-color: var(--border-bright);
}
.tag--refactor {
  color: var(--text-aged);
  background: var(--ink-raised);
  border-color: var(--border);
}

.text :deep(strong) {
  color: var(--text-parchment);
  font-weight: 500;
}
.text :deep(em) {
  font-style: normal;
  font-family: 'Cinzel', serif;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--gold-warm);
}

/* ── Footnote ── */
.footnote {
  margin-top: 32px;
  text-align: center;
}

.foot-rule {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, transparent 0%, var(--border) 30%, var(--border) 70%, transparent 100%);
  margin-bottom: 18px;
}

.foot-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 12.5px;
  letter-spacing: 0.22em;
  color: var(--text-faded);
}

/* ── Responsive ── */
@media (max-width: 820px) {
  .page { padding: 0 24px 48px; }
  .hero-title { font-size: 30px; }
  .entry { grid-template-columns: 24px 1fr; gap: 12px; }
  .entry-head { flex-wrap: wrap; }
}
</style>
