<template>
  <div class="app-root">
    <div class="paper-texture"></div>
    <div class="bg-watermark">詩</div>
    <router-view />
    <SplashScreen v-if="showSplash" @done="showSplash = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SplashScreen from './components/SplashScreen.vue'

// 移动端跳过启动动画，避免在小屏上出现闪现；桌面端保持不变
const isMobile = window.matchMedia('(max-width: 820px)').matches
const showSplash = ref(!isMobile)
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  /* ── Backgrounds (warm rice paper) ── */
  --ink-void:       #e8e0d4;
  --ink-deep:       #f4efe6;
  --ink-surface:    #fdfaf5;
  --ink-raised:     #ede8de;
  --ink-hover:      #e4dcd0;

  /* ── Amber / Gold ── */
  --gold-bright:    #a06818;
  --gold-warm:      #7a5010;
  --gold-dim:       #c08830;
  --gold-ghost:     #f5ecd8;

  /* ── Cinnabar red (朱砂) — accent ── */
  --red:            #c03828;
  --red-dim:        #8b2818;
  --red-ghost:      #fdf2f0;
  --red-border:     rgba(192, 56, 40, 0.28);

  /* ── Ink text ── */
  --text-parchment: #1c1208;
  --text-aged:      #50381e;
  --text-faded:     #9a7850;

  /* ── Borders & shadows ── */
  --border:         rgba(160, 120, 40, 0.18);
  --border-bright:  rgba(160, 104, 24, 0.38);
  --glow:           0 0 28px rgba(160, 104, 24, 0.1);
  --glow-strong:    0 0 52px rgba(160, 104, 24, 0.16);
  --shadow:         0 2px 28px rgba(80, 50, 15, 0.07);
}

html, body {
  height: 100%;
  background: var(--ink-deep);
  color: var(--text-parchment);
  font-family: 'Noto Serif SC', 'Noto Serif', serif;
  -webkit-font-smoothing: antialiased;
}

#app { min-height: 100vh; }

.app-root {
  position: relative;
  min-height: 100vh;
}

/* Subtle paper texture via SVG noise */
.paper-texture {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.028;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* Faint watermark character */
.bg-watermark {
  position: fixed;
  right: -60px;
  bottom: -80px;
  font-family: 'Noto Serif SC', serif;
  font-size: 480px;
  font-weight: 700;
  color: rgba(160, 104, 24, 0.035);
  pointer-events: none;
  z-index: 0;
  user-select: none;
  line-height: 1;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--ink-raised); }
::-webkit-scrollbar-thumb { background: var(--gold-dim); border-radius: 2px; }

/* ── Responsive (mobile) ── */
@media (max-width: 820px) {
  .bg-watermark {
    font-size: 240px;
    right: -40px;
    bottom: -50px;
  }
}
</style>
