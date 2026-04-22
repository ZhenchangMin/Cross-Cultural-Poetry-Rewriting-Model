<template>
  <div class="output-pane">
    <div class="pane-label">
      <span class="label-seq">二</span>
      <span class="label-zh">译 诗</span>
      <span class="label-en">Generated Poem</span>
    </div>

    <div class="result-wrap" :class="{ 'has-result': result && !loading }">
      <div class="corner tl"></div>
      <div class="corner tr"></div>
      <div class="corner bl"></div>
      <div class="corner br"></div>

      <div v-if="loading" class="state-loading">
        <div class="ink-drop">
          <span
            v-for="(c, i) in inkChars" :key="i"
            class="ink-char"
            :style="{ animationDelay: i * 0.12 + 's' }"
          >{{ c }}</span>
        </div>
        <p class="loading-label">正在生成…</p>
      </div>

      <div v-else-if="result" class="result-body">
        <div class="result-seal">生</div>
        <p class="result-text">{{ result }}</p>
      </div>

      <div v-else class="state-empty">
        <span class="empty-glyph">詩</span>
        <p class="empty-hint">生成的诗歌将显示于此</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps(['result', 'loading'])
const inkChars = ['春','风','又','绿','江','南','岸','明','月','何','时','照']
</script>

<style scoped>
.output-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pane-label {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-left: 2px;
  height: 22px;
}

.label-seq {
  font-family: 'Noto Serif SC', serif;
  font-size: 10px;
  color: var(--gold-dim);
  letter-spacing: 0.05em;
}

.label-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.22em;
  color: var(--text-aged);
}

.label-en {
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.result-wrap {
  flex: 1;
  position: relative;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  transition: border-color 0.4s, box-shadow 0.4s;
}

.result-wrap.has-result {
  align-items: flex-start;
  justify-content: flex-start;
  border-color: rgba(192, 56, 40, 0.2);
  box-shadow: 0 0 48px rgba(192, 56, 40, 0.06), var(--shadow);
}

/* Corner brackets */
.corner {
  position: absolute;
  width: 9px;
  height: 9px;
  z-index: 2;
}
.tl { top: -1px;    left: -1px;  border-top:    1px solid var(--gold-dim); border-left:   1px solid var(--gold-dim); }
.tr { top: -1px;    right: -1px; border-top:    1px solid var(--gold-dim); border-right:  1px solid var(--gold-dim); }
.bl { bottom: -1px; left: -1px;  border-bottom: 1px solid var(--gold-dim); border-left:   1px solid var(--gold-dim); }
.br { bottom: -1px; right: -1px; border-bottom: 1px solid var(--gold-dim); border-right:  1px solid var(--gold-dim); }

/* ── Loading ── */
.state-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.ink-drop { display: flex; gap: 3px; }

.ink-char {
  font-family: 'Noto Serif SC', serif;
  font-size: 18px;
  color: var(--red);
  opacity: 0;
  animation: char-wave 1.6s ease-in-out infinite;
}

@keyframes char-wave {
  0%, 100% { opacity: 0.15; transform: translateY(3px); }
  50%       { opacity: 0.85; transform: translateY(-3px); }
}

.loading-label {
  font-family: 'Noto Serif SC', serif;
  font-size: 11px;
  letter-spacing: 0.25em;
  color: var(--text-faded);
}

/* ── Result ── */
.result-body {
  padding: 22px 24px;
  width: 100%;
  animation: reveal 0.5s ease;
  position: relative;
}

@keyframes reveal {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Red seal stamp decoration */
.result-seal {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  border: 1.5px solid var(--red);
  color: var(--red);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.45;
  letter-spacing: 0;
}

.result-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  line-height: 2;
  color: var(--text-parchment);
  white-space: pre-wrap;
}

/* ── Empty ── */
.state-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  opacity: 0.2;
}

.empty-glyph {
  font-family: 'Noto Serif SC', serif;
  font-size: 52px;
  font-weight: 300;
  color: var(--gold-bright);
  line-height: 1;
}

.empty-hint {
  font-family: 'Noto Serif SC', serif;
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--text-faded);
}
</style>
