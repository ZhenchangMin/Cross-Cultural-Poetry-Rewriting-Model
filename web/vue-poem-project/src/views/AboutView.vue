<template>
  <div class="page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <NavBar />

    <main class="about">
      <section class="hero">
        <h1 class="hero-title">关于诗渡</h1>
        <p class="hero-subtitle">About&nbsp;Poem&nbsp;Bridge</p>
        <div class="hero-rule"></div>
        <p class="hero-quote">
          让一首诗，<br />
          在另一种语言与文化里，<br />
          重新生长。
        </p>
        <p class="hero-quote-en">
          A poem reborn — in another language, another culture.
        </p>
      </section>

      <section class="intro">
        <h2 class="section-title">
          <span class="zh">项目简介</span>
          <span class="en">Project</span>
        </h2>
        <p class="prose">
          <strong>诗渡（Poem&nbsp;Bridge）</strong>是一项面向多语种古典与现代诗歌的
          <em>跨文化转写</em>（Cross-Cultural&nbsp;Rewriting）系统。
          我们尝试让一首诗歌，不只是被字面翻译，
          而是以新的形式被"重新写出来"——保留其情感与内容的同时，
          穿上目标文化的格律与音韵。
        </p>
      </section>

      <section class="pillars">
        <h2 class="section-title">
          <span class="zh">三个支柱</span>
          <span class="en">Three Pillars</span>
        </h2>
        <div class="card-grid">
          <article class="card">
            <div class="card-num">01</div>
            <h3 class="card-title">跨文化转写</h3>
            <p class="card-sub">Transcreation, not Translation</p>
            <p class="card-body">
              不止于语义的迁移，而是让诗歌在目标文化的土壤中
              重新生长出符合其美学传统的形态。
            </p>
          </article>

          <article class="card">
            <div class="card-num">02</div>
            <h3 class="card-title">异化与归化</h3>
            <p class="card-sub">Foreignization &amp; Domestication</p>
            <p class="card-body">
              基于韦努蒂（Venuti,&nbsp;1995）的二元理论框架，
              提供可调节的<strong>文化适配强度</strong>滑块，
              在保留异域意象与转化为本土意象之间自由切换。
            </p>
          </article>

          <article class="card">
            <div class="card-num">03</div>
            <h3 class="card-title">三位一体模型</h3>
            <p class="card-sub">Trinity Architecture</p>
            <p class="card-body">
              语义（XLM-R）、风格（LoRA）、文化（Culture&nbsp;Embedding）
              三类向量被同时注入大语言模型的输入空间，
              实现零样本跨语言生成。
            </p>
          </article>
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

.about {
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
  padding: 56px 0 48px;
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
  font-size: 17px;
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

/* ── Sections ── */
.section-title {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 22px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.section-title .zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.2em;
  color: var(--text-parchment);
}
.section-title .en {
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.32em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.intro {
  margin-top: 8px;
  padding: 8px 4px 32px;
}

.prose {
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  line-height: 2;
  color: var(--text-aged);
  letter-spacing: 0.04em;
  margin-bottom: 14px;
}
.prose strong {
  color: var(--text-parchment);
  font-weight: 500;
}
.prose em {
  font-style: normal;
  color: var(--red);
  border-bottom: 1px dashed var(--red-border);
  padding-bottom: 1px;
}
.prose .date {
  font-family: 'Cinzel', serif;
  letter-spacing: 0.12em;
  color: var(--gold-warm);
}

.lang-tag {
  display: inline-block;
  padding: 2px 10px;
  margin: 0 4px;
  font-size: 13px;
  background: var(--gold-ghost);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--gold-warm);
  letter-spacing: 0.08em;
}

/* ── Pillars ── */
.pillars {
  padding: 24px 4px 8px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.card {
  position: relative;
  padding: 28px 22px 26px;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  box-shadow: var(--shadow);
  transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: var(--glow-strong);
  border-color: var(--border-bright);
}

.card-num {
  position: absolute;
  top: 12px;
  right: 16px;
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--gold-dim);
  opacity: 0.6;
}

.card-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 0.16em;
  color: var(--text-parchment);
  line-height: 1.2;
}
.card-sub {
  margin-top: 5px;
  font-family: 'Cinzel', serif;
  font-size: 9.5px;
  letter-spacing: 0.26em;
  color: var(--red);
  opacity: 0.75;
  text-transform: uppercase;
}

.card-body {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  font-family: 'Noto Serif SC', serif;
  font-size: 13.5px;
  line-height: 1.95;
  color: var(--text-aged);
  letter-spacing: 0.03em;
}
.card-body strong {
  color: var(--red);
  font-weight: 500;
}

/* ── Footnote ── */
.footnote {
  margin-top: 56px;
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

.foot-en {
  margin-top: 6px;
  font-family: 'Cinzel', serif;
  font-size: 10px;
  letter-spacing: 0.3em;
  color: var(--text-faded);
  text-transform: uppercase;
}

/* ── Responsive ── */
@media (max-width: 820px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
  .hero-title { font-size: 30px; }
  .page { padding: 0 24px 48px; }
}
</style>
