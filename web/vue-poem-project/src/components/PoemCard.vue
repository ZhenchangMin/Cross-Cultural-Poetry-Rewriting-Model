<template>
  <div class="output-pane">
    <div class="pane-label">
      <span class="label-seq">二</span>
      <span class="label-zh">译 诗</span>
      <span class="label-en">Generated Poem</span>
    </div>

    <div class="result-wrap" :class="{ 'has-result': parsed && !loading }">
      <div class="corner tl"></div>
      <div class="corner tr"></div>
      <div class="corner bl"></div>
      <div class="corner br"></div>

      <!-- 加载动画 -->
      <div v-if="loading" class="state-loading">
        <div class="ink-drop">
          <span
            v-for="(c, i) in inkChars" :key="i"
            class="ink-char"
            :style="{ animationDelay: i * 0.12 + 's' }"
          >{{ c }}</span>
        </div>
        <p class="loading-label">正在转写…</p>
      </div>

      <!-- 结构化结果 -->
      <div v-else-if="parsed" class="result-body">
        <div class="result-seal">转</div>

        <p class="result-text">{{ parsed.poem }}</p>

        <div v-if="parsed.analysis" class="analysis-block">
          <div class="analysis-divider">
            <div class="analysis-rule"></div>
            <span class="analysis-label">转写思路</span>
            <div class="analysis-rule"></div>
          </div>
          <p class="analysis-text">{{ parsed.analysis }}</p>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="state-empty">
        <span class="empty-glyph">詩</span>
        <p class="empty-hint">生成的诗歌将显示于此</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['result', 'loading'])

const inkChars = ['春','风','又','绿','江','南','岸','，','明','月','何','时','照','我','还']

const parsed = computed(() => {
  if (!props.result) return null
  const poemMatch    = props.result.match(/【转写结果】\s*([\s\S]*?)(?=【转写思路】|$)/)
  const analysisMatch = props.result.match(/【转写思路】\s*([\s\S]*)$/)
  const poem = poemMatch ? poemMatch[1].trim() : props.result.trim()
  const analysis = analysisMatch ? analysisMatch[1].trim() : null
  return { poem, analysis }
})
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
  overflow: hidden; /* 防止 corner -1px 偏移触发滚动条 */
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
  pointer-events: none;
}
.tl { top: -1px;    left: -1px;  border-top:    1px solid var(--gold-dim); border-left:   1px solid var(--gold-dim); }
.tr { top: -1px;    right: -1px; border-top:    1px solid var(--gold-dim); border-right:  1px solid var(--gold-dim); }
.bl { bottom: -1px; left: -1px;  border-bottom: 1px solid var(--gold-dim); border-left:   1px solid var(--gold-dim); }
.br { bottom: -1px; right: -1px; border-bottom: 1px solid var(--gold-dim); border-right:  1px solid var(--gold-dim); }

/* ── 加载动画 ── */
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
  opacity: 0.15;
  animation: char-wave 1.6s ease-in-out infinite;
  animation-fill-mode: backwards;
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

/* ── 转写结果 ── */
.result-body {
  padding: 22px 24px;
  width: 100%;
  animation: reveal 0.5s ease;
  position: relative;
  overflow-y: auto;
  max-height: 100%;
}

@keyframes reveal {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

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
}

.result-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  line-height: 2;
  color: var(--text-parchment);
  white-space: pre-wrap;
  padding-right: 36px; /* 避免与印章重叠 */
}

/* ── 转写思路 ── */
.analysis-block {
  margin-top: 20px;
}

.analysis-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.analysis-rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--border-bright), transparent);
}

.analysis-label {
  font-family: 'Noto Serif SC', serif;
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--text-faded);
  white-space: nowrap;
}

.analysis-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  line-height: 1.9;
  color: var(--text-faded);
  white-space: pre-wrap;
}

/* ── 空状态 ── */
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

/* ── Responsive (mobile) ── */
@media (max-width: 820px) {
  .output-pane { gap: 8px; }
  .pane-label { height: auto; gap: 8px; }
  .label-zh { font-size: 13px; letter-spacing: 0.18em; }

  /* 与输入框保持一致的视觉强度：加深边框 + 阴影 + 边角标识放大 */
  .result-wrap {
    min-height: 240px;
    border-color: var(--border-bright);
    box-shadow: 0 1px 8px rgba(80, 50, 15, 0.06), inset 0 0 0 1px rgba(160, 104, 24, 0.04);
  }

  .corner { width: 14px; height: 14px; }
  .tl, .tr, .bl, .br { border-width: 1.5px; }

  .result-body { padding: 16px 18px; }

  .result-seal {
    top: 12px;
    right: 12px;
    width: 24px;
    height: 24px;
    font-size: 11px;
  }

  .result-text {
    font-size: 14px;
    line-height: 1.9;
    padding-right: 30px;
  }

  .analysis-text { font-size: 12px; line-height: 1.8; }

  .ink-char { font-size: 16px; }
  .empty-glyph { font-size: 40px; }
}
</style>
