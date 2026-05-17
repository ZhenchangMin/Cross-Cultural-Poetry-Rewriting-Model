<template>
  <div class="page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <NavBar />

    <header class="header">
      <div class="header-rule"></div>
      <div class="header-body">
        <span class="rune">⬡</span>
        <div class="title-block">
          <h1 class="title-zh">詩歌跨文化重寫</h1>
          <p class="title-en">Cross-Cultural Poetry Rewriting</p>
        </div>
        <span class="rune">⬡</span>
      </div>
      <div class="header-rule"></div>
    </header>

    <main class="workspace">
      <section class="pane">
        <InputBox v-model="text" />
      </section>

      <div class="divider">
        <div class="divider-rail"></div>
        <span class="divider-mark">⊕</span>
        <div class="divider-rail"></div>
      </div>

      <section class="pane">
        <PoemCard :result="result" :loading="loading" />
      </section>
    </main>

    <footer class="footer">
      <div class="footer-rule"></div>
      <ControlPanel
        v-model:style="style"
        v-model:sourceLang="sourceLang"
        v-model:targetLang="targetLang"
        v-model:intensity="intensity"
        @generate="handleGenerate"
      />
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InputBox from '../components/InputBox.vue'
import ControlPanel from '../components/ControlPanel.vue'
import PoemCard from '../components/PoemCard.vue'
import NavBar from '../components/NavBar.vue'

const text = ref('')
const result = ref('')
const style = ref('jueju')
const sourceLang = ref('KO')
const targetLang = ref('ZH')
const intensity = ref(3)
const loading = ref(false)

const handleGenerate = async () => {
  if (!text.value.trim()) return
  loading.value = true
  try {
    const res = await fetch('/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text.value,
        style: style.value,
        sourceLang: sourceLang.value,
        targetLang: targetLang.value,
        intensity: intensity.value
      })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    result.value = data.result
  } catch (e) {
    result.value = '生成失败：' + e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0 48px 40px;
  position: relative;
  overflow: hidden;
}

/* Ambient light orbs — warm, paper-toned */
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

/* ── Header ── */
.header {
  padding: 36px 0 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  position: relative;
  z-index: 1;
}

.header-rule {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, transparent 0%, var(--border-bright) 30%, var(--border-bright) 70%, transparent 100%);
}

.header-body {
  display: flex;
  align-items: center;
  gap: 28px;
}

.rune {
  color: var(--gold-dim);
  font-size: 15px;
  opacity: 0.5;
  animation: rune-breathe 4s ease-in-out infinite;
}
.rune:last-child { animation-delay: 2s; }

@keyframes rune-breathe {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 0.65; }
}

.title-block { text-align: center; }

.title-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 26px;
  font-weight: 400;
  letter-spacing: 0.18em;
  color: var(--text-parchment);
  line-height: 1.2;
}

.title-en {
  margin-top: 5px;
  font-family: 'Cinzel', serif;
  font-size: 10px;
  letter-spacing: 0.32em;
  color: var(--text-faded);
  text-transform: uppercase;
}

/* ── Workspace ── */
.workspace {
  flex: 1;
  display: flex;
  gap: 0;
  min-height: 420px;
  position: relative;
  z-index: 1;
}

.pane { flex: 1; min-width: 0; }

.divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 28px;
  gap: 6px;
}

.divider-rail {
  flex: 1;
  width: 1px;
  background: linear-gradient(to bottom, transparent, var(--border-bright) 20%, var(--border-bright) 80%, transparent);
}

.divider-mark {
  font-size: 14px;
  color: var(--gold-dim);
  opacity: 0.4;
  flex-shrink: 0;
}

/* ── Footer ── */
.footer {
  margin-top: 28px;
  position: relative;
  z-index: 1;
}

.footer-rule {
  height: 1px;
  background: linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent);
  margin-bottom: 24px;
}

/* ── Responsive (mobile) ── */
@media (max-width: 820px) {
  .page {
    padding: 0 16px 24px;
    /* 桌面端用 hidden 控制 orb 溢出；移动端必须放开纵向滚动，否则下方内容会被截断 */
    overflow-x: hidden;
    overflow-y: visible;
  }

  .orb-1 { width: 300px; height: 300px; top: -100px; left: -80px; }
  .orb-2 { width: 360px; height: 360px; bottom: -120px; right: -80px; }

  .header {
    padding: 20px 0 16px;
    gap: 10px;
  }
  .header-body { gap: 16px; }
  .rune { font-size: 12px; }
  .title-zh { font-size: 20px; letter-spacing: 0.14em; }
  .title-en { font-size: 9px; letter-spacing: 0.26em; }

  .workspace {
    flex-direction: column;
    gap: 18px;
    min-height: 0;
    flex: none; /* 解除 flex:1 强行平分，让两栏自然按 min-height 撑开 */
  }
  .pane { min-height: 280px; }

  /* 把竖直分隔条改为水平分隔条 */
  .divider {
    flex-direction: row;
    padding: 4px 0;
    gap: 10px;
  }
  .divider-rail {
    width: auto;
    height: 1px;
    background: linear-gradient(to right, transparent, var(--border-bright) 20%, var(--border-bright) 80%, transparent);
  }
  .divider-mark { font-size: 12px; }

  .footer { margin-top: 18px; }
  .footer-rule { margin-bottom: 16px; }
}
</style>
