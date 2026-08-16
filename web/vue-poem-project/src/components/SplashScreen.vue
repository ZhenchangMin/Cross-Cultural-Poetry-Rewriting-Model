<template>
  <div class="splash" :class="{ 'opening': opening, 'gone': gone }">
    <div class="curtain curtain-left">
      <div class="curtain-edge"></div>
    </div>
    <div class="curtain curtain-right">
      <div class="curtain-edge curtain-edge-right"></div>
    </div>

    <div class="logo-wrap" :class="{ 'logo-out': opening }">
      <div class="logo-frame">
        <span class="frame-corner tl"></span>
        <span class="frame-corner tr"></span>
        <span class="frame-corner bl"></span>
        <span class="frame-corner br"></span>
        <div class="logo-rune">詩</div>
      </div>
      <div class="logo-divider">
        <span class="divider-dot"></span>
        <span class="divider-line"></span>
        <span class="divider-mark">⊕</span>
        <span class="divider-line"></span>
        <span class="divider-dot"></span>
      </div>
      <div class="logo-title-zh">詩歌跨文化轉寫</div>
      <div class="logo-title-en">Cross-Cultural Poetry Rewriting</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['done'])
const opening = ref(false)
const gone = ref(false)

onMounted(() => {
  setTimeout(() => { opening.value = true }, 800)
  setTimeout(() => { gone.value = true; emit('done') }, 2000)
})
</script>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  z-index: 99998;
  pointer-events: none;
  overflow: hidden;
}
.splash.gone { display: none; }

/* ── Curtains ── */
.curtain {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 50%;
  background:
    radial-gradient(ellipse at center, #f9f3e6 0%, #ede2cb 60%, #d8c8a8 100%);
  transition: transform 1.3s cubic-bezier(0.76, 0, 0.24, 1);
  box-shadow: inset 0 0 80px rgba(160, 104, 24, 0.08);
}
.curtain-left  { left: 0;     transform: translateX(0); }
.curtain-right { left: 50%;   transform: translateX(0); }

.opening .curtain-left  { transform: translateX(-100%); }
.opening .curtain-right { transform: translateX(100%); }

/* Subtle vertical seam highlight on the inner edge */
.curtain-edge {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 2px;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(160, 104, 24, 0.35) 20%,
    rgba(160, 104, 24, 0.55) 50%,
    rgba(160, 104, 24, 0.35) 80%,
    transparent 100%
  );
}
.curtain-edge-right { right: auto; left: 0; }

/* ── Logo ── */
.logo-wrap {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 2;
  animation: logo-in 1.1s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.logo-out {
  animation: logo-out 0.55s cubic-bezier(0.7, 0, 0.84, 0) both;
}

@keyframes logo-in {
  0%   { opacity: 0; transform: translate(-50%, -50%) scale(0.78); filter: blur(8px); }
  60%  { opacity: 1; filter: blur(0); }
  100% { opacity: 1; transform: translate(-50%, -50%) scale(1); filter: blur(0); }
}
@keyframes logo-out {
  0%   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(1.18); filter: blur(6px); }
}

.logo-frame {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(160, 104, 24, 0.4);
  background:
    radial-gradient(ellipse at center, rgba(253, 250, 245, 0.6) 0%, transparent 70%);
}
.frame-corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid #a06818;
}
.frame-corner.tl { top: -6px; left: -6px;  border-right: none; border-bottom: none; }
.frame-corner.tr { top: -6px; right: -6px; border-left: none;  border-bottom: none; }
.frame-corner.bl { bottom: -6px; left: -6px;  border-right: none; border-top: none; }
.frame-corner.br { bottom: -6px; right: -6px; border-left: none;  border-top: none; }

.logo-rune {
  font-family: 'Noto Serif SC', serif;
  font-size: 140px;
  font-weight: 700;
  line-height: 1;
  color: #c03828;
  text-shadow:
    0 0 24px rgba(192, 56, 40, 0.25),
    0 0 1px rgba(28, 18, 8, 0.4);
  animation: rune-pulse 2.4s ease-in-out infinite;
}

@keyframes rune-pulse {
  0%, 100% { text-shadow: 0 0 24px rgba(192, 56, 40, 0.25), 0 0 1px rgba(28, 18, 8, 0.4); }
  50%      { text-shadow: 0 0 40px rgba(192, 56, 40, 0.45), 0 0 1px rgba(28, 18, 8, 0.4); }
}

.logo-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin: 28px 0 14px;
  color: #a06818;
}
.divider-line {
  width: 56px;
  height: 1px;
  background: linear-gradient(to right, transparent, #a06818, transparent);
}
.divider-dot {
  width: 4px;
  height: 4px;
  background: #a06818;
  border-radius: 50%;
}
.divider-mark {
  font-size: 14px;
  color: #c03828;
}

.logo-title-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.4em;
  padding-left: 0.4em;
  color: #1c1208;
}
.logo-title-en {
  margin-top: 10px;
  font-family: 'Noto Serif', serif;
  font-size: 13px;
  letter-spacing: 0.35em;
  color: #50381e;
  text-transform: uppercase;
  font-style: italic;
}
</style>
