<template>
  <div class="page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>

    <nav class="navbar">
      <div class="nav-brand">
        <span class="brand-mark">詩</span>
        <div class="brand-text-wrap">
          <span class="brand-zh">诗渡</span>
          <span class="brand-en">Poem&nbsp;Bridge</span>
        </div>
      </div>
      <ul class="nav-links">
        <li v-for="item in navItems" :key="item.key">
          <button
            type="button"
            class="nav-link"
            :class="{ active: activeNav === item.key }"
            @click="activeNav = item.key"
          >
            <span class="nav-link-zh">{{ item.zh }}</span>
            <span class="nav-link-en">{{ item.en }}</span>
          </button>
        </li>
      </ul>
    </nav>

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

const text = ref('')
const result = ref('')
const style = ref('modern')
const sourceLang = ref('KO')
const targetLang = ref('ZH')
const intensity = ref(3)
const loading = ref(false)

const navItems = [
  { key: 'about',     zh: '关于我们', en: 'About' },
  { key: 'changelog', zh: '更新日志', en: 'Changelog' },
  { key: 'history',   zh: '重写历史', en: 'History' }
]
const activeNav = ref('')

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

/* ── Navbar ── */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 4px 14px;
  position: relative;
  z-index: 2;
  border-bottom: 1px solid var(--border);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  user-select: none;
}

.brand-mark {
  font-family: 'Noto Serif SC', serif;
  font-size: 30px;
  font-weight: 600;
  color: var(--red);
  line-height: 1;
  width: 46px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--red-border);
  border-radius: 4px;
  background: var(--red-ghost);
  box-shadow: 0 0 0 4px rgba(192, 56, 40, 0.04);
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.1;
}

.brand-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.22em;
  color: var(--text-parchment);
}

.brand-en {
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.32em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  list-style: none;
}

.nav-link {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 18px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  color: var(--text-aged);
  transition: color 0.25s ease;
}

.nav-link-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 14px;
  letter-spacing: 0.18em;
  line-height: 1.1;
}

.nav-link-en {
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--text-faded);
  text-transform: uppercase;
  transition: color 0.25s ease;
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 0;
  height: 1px;
  background: var(--red);
  transform: translateX(-50%);
  transition: width 0.3s ease;
}

.nav-link:hover {
  color: var(--red);
}
.nav-link:hover .nav-link-en {
  color: var(--red);
  opacity: 0.7;
}
.nav-link:hover::after {
  width: 60%;
}

.nav-link.active {
  color: var(--red);
}
.nav-link.active .nav-link-en {
  color: var(--red);
  opacity: 0.7;
}
.nav-link.active::after {
  width: 60%;
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
</style>
