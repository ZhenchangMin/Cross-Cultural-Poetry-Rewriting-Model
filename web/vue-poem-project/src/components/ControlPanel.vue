<template>
  <div class="control-panel">
    <div class="param-row">

      <!-- 输入语言 -->
      <div class="param-group">
        <span class="param-label">输入语言</span>
        <div class="pill-bar">
          <button
            v-for="opt in langs" :key="opt.value"
            class="pill" :class="{ active: sourceLangVal === opt.value }"
            @click="sourceLangVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
        </div>
      </div>

      <div class="arrow-sep">→</div>

      <!-- 输出语言（与输入相同的选项禁用） -->
      <div class="param-group">
        <span class="param-label">输出语言</span>
        <div class="pill-bar">
          <button
            v-for="opt in langs" :key="opt.value"
            class="pill"
            :class="{ active: targetLangVal === opt.value, disabled: opt.value === sourceLangVal }"
            :disabled="opt.value === sourceLangVal"
            @click="targetLangVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
        </div>
      </div>

      <!-- 诗歌风格 -->
      <div class="param-group">
        <span class="param-label">输出诗歌的风格</span>
        <div class="pill-bar">
          <button
            v-for="opt in currentStyles" :key="opt.value"
            class="pill" :class="{ active: styleVal === opt.value }"
            @click="styleVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
        </div>
      </div>

      <!-- 文化适配强度 -->
      <div class="param-group intensity-group">
        <div class="label-row">
          <span class="param-label">文化适配强度</span>
          <button type="button" class="help-btn" aria-label="什么是异化和归化">
            ?
            <span class="help-tip" role="tooltip">
              <span class="tip-line">
                <strong>异化 (Foreignization)</strong>
                以源文化为中心，最大限度保留原诗内容——意象、典故、句法都向源文化贴近，读者读完会明确感到"这是一首外国诗"，可能略生硬，但完整保留了原诗的文化独特性。
              </span>
              <span class="tip-line">
                <strong>归化 (Domestication)</strong>
                以目标文化为中心，让作品读起来像本国本土原创——源语意象、典故置换为目标文化对应物，消除翻译腔，读者会感到"这是一首本国诗"，但失去了原诗的异国情调。
              </span>
              <span class="tip-cite">— Venuti, L. (1995). <em>The Translator's Invisibility</em>.</span>
            </span>
          </button>
        </div>
        <div class="intensity-wrap">
          <span class="intensity-pole">
            <span class="pole-zh">异化</span>
            <span class="pole-en">Foreignization</span>
          </span>
          <input
            type="range" min="1" max="5" step="1"
            v-model.number="intensityVal"
            class="intensity-slider"
          />
          <span class="intensity-pole">
            <span class="pole-zh">归化</span>
            <span class="pole-en">Domestication</span>
          </span>
        </div>
      </div>

    </div>

    <button class="gen-btn" @click="$emit('generate')">
      <span class="gen-zh">生 成</span>
      <span class="gen-en">Generate</span>
    </button>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps(['style', 'sourceLang', 'targetLang', 'intensity'])
const emit = defineEmits(['update:style', 'update:sourceLang', 'update:targetLang', 'update:intensity', 'generate'])

const langs = [
  { value: 'ZH', zh: '中文', en: 'ZH' },
  { value: 'KO', zh: '韩语', en: 'KO' },
  { value: 'RU', zh: '俄语', en: 'RU' },
]

// 按目标语言切换可选诗学形式
const stylesByLang = {
  ZH: [
    { value: 'jueju',  zh: '绝句',   en: 'Jueju'  },
    { value: 'lvshi',  zh: '律诗',   en: 'Lüshi'  },
    { value: 'ci',     zh: '宋词',   en: 'Ci'     },
    { value: 'qu',     zh: '元曲',   en: 'Qu'     },
    { value: 'modern', zh: '现代诗', en: 'Modern' },
  ],
  KO: [
    { value: 'sijo',   zh: '时调',   en: 'Sijo'   },
    { value: 'gasa',   zh: '歌辞',   en: 'Gasa'   },
    { value: 'modern', zh: '现代诗', en: 'Modern' },
  ],
  RU: [
    { value: 'sonnet', zh: '十四行', en: 'Sonnet' },
    { value: 'ode',    zh: '颂诗',   en: 'Ode'    },
    { value: 'lyric',  zh: '抒情诗', en: 'Lyric'  },
    { value: 'modern', zh: '现代诗', en: 'Modern' },
  ],
}

const sourceLangVal = computed({ get: () => props.sourceLang, set: v => emit('update:sourceLang', v) })
const targetLangVal = computed({ get: () => props.targetLang, set: v => emit('update:targetLang', v) })
const styleVal      = computed({ get: () => props.style,      set: v => emit('update:style', v) })
const intensityVal  = computed({ get: () => props.intensity,  set: v => emit('update:intensity', v) })

const currentStyles = computed(() => stylesByLang[targetLangVal.value] || stylesByLang.ZH)

// 当输入语言切换到与输出语言相同时，自动切到第一个不同的选项
watch(sourceLangVal, (newVal) => {
  if (newVal === targetLangVal.value) {
    const other = langs.find(l => l.value !== newVal)
    if (other) targetLangVal.value = other.value
  }
})

// 切换目标语言时，始终回到该语言下的第一个诗歌形式（即第一个按钮）
watch(targetLangVal, () => {
  const list = currentStyles.value
  if (list.length > 0) {
    styleVal.value = list[0].value
  }
}, { immediate: true })
</script>

<style scoped>
.control-panel {
  display: flex;
  align-items: center;
  gap: 36px;
  padding: 20px 0;
  flex-wrap: wrap;
}

.param-row {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  flex: 1;
  flex-wrap: wrap;
}

.param-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-label {
  font-family: 'Noto Serif SC', serif;
  font-size: 12px;
  letter-spacing: 0.22em;
  color: var(--text-faded);
}

.arrow-sep {
  font-family: 'Cinzel', serif;
  font-size: 18px;
  color: var(--gold-dim);
  opacity: 0.5;
  padding-bottom: 6px;
  flex-shrink: 0;
}

.pill-bar {
  display: flex;
  gap: 2px;
  background: var(--ink-raised);
  border: 1px solid var(--border);
  padding: 3px;
  box-shadow: inset 0 1px 3px rgba(120, 80, 20, 0.06);
}

.pill {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 7px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  transition: background 0.2s, opacity 0.2s;
}

.pill:hover:not(.disabled) { background: var(--ink-surface); }

.pill.active {
  background: var(--red-ghost);
  box-shadow: inset 0 0 0 1px var(--red-border);
}

.pill.disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.pill-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  color: var(--text-aged);
  transition: color 0.2s;
  letter-spacing: 0.05em;
}

.pill-en {
  font-family: 'Cinzel', serif;
  font-size: 8px;
  color: var(--text-faded);
  letter-spacing: 0.12em;
  transition: color 0.2s;
}

.pill.active .pill-zh { color: var(--red); }
.pill.active .pill-en  { color: var(--red-dim); opacity: 0.6; }

/* ── 文化适配强度滑块 ── */
.intensity-group { min-width: 280px; }

.label-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.help-btn {
  width: 17px;
  height: 17px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--border-bright);
  background: transparent;
  color: var(--text-faded);
  font-family: 'Cinzel', serif;
  font-size: 11px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: help;
  position: relative;
  transition: color 0.2s, border-color 0.2s, box-shadow 0.2s;
  flex-shrink: 0;
}

.help-btn:hover,
.help-btn:focus-visible {
  color: var(--red);
  border-color: var(--red-border);
  box-shadow: 0 0 6px rgba(192, 56, 40, 0.25);
  outline: none;
}

.help-tip {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  width: 380px;
  padding: 16px 18px;
  background: var(--ink-surface);
  border: 1px solid var(--border-bright);
  color: var(--text-aged);
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  line-height: 1.8;
  letter-spacing: 0.02em;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(160, 104, 24, 0.08);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.22s ease, transform 0.22s ease, visibility 0.22s;
  z-index: 100;
  white-space: normal;
  cursor: default;
}

.help-tip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--border-bright);
}

.help-btn:hover .help-tip,
.help-btn:focus-visible .help-tip {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

.tip-line strong {
  color: var(--red);
  font-weight: 500;
  font-size: 14px;
  letter-spacing: 0.04em;
  display: block;
  margin-bottom: 4px;
}

.tip-cite {
  font-family: 'Cinzel', serif;
  font-size: 10.5px;
  color: var(--text-faded);
  letter-spacing: 0.08em;
  border-top: 1px solid var(--border);
  padding-top: 10px;
  margin-top: 2px;
}
.tip-cite em { font-style: italic; }

.intensity-wrap {
  display: flex;
  align-items: stretch;
  gap: 2px;
  background: var(--ink-raised);
  border: 1px solid var(--border);
  padding: 3px;
  box-shadow: inset 0 1px 3px rgba(120, 80, 20, 0.06);
}

.intensity-pole {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 7px 14px;
  flex-shrink: 0;
}

/* 字体规格与 .pill-zh / .pill-en 严格一致，不设 line-height 让其继承浏览器默认，确保两框高度相同 */
.pole-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 13px;
  color: var(--text-aged);
  letter-spacing: 0.05em;
}

.pole-en {
  font-family: 'Cinzel', serif;
  font-size: 8px;
  color: var(--text-faded);
  letter-spacing: 0.12em;
}

.intensity-slider {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  min-width: 80px;
  height: 2px;
  align-self: center;
  margin: 0 6px;
  background: linear-gradient(to right, var(--gold-dim), var(--red));
  border-radius: 1px;
  outline: none;
  cursor: pointer;
}

.intensity-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--red);
  border: 1.5px solid var(--ink-surface);
  box-shadow: 0 0 6px rgba(192, 56, 40, 0.35);
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.intensity-slider::-webkit-slider-thumb:hover {
  box-shadow: 0 0 10px rgba(192, 56, 40, 0.55);
}

.intensity-slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--red);
  border: 1.5px solid var(--ink-surface);
  box-shadow: 0 0 6px rgba(192, 56, 40, 0.35);
  cursor: pointer;
}

/* ── 生成按钮 ── */
.gen-btn {
  background: var(--red-ghost);
  border: 1px solid var(--red-border);
  cursor: pointer;
  padding: 14px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
  flex-shrink: 0;
}

.gen-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(192,56,40,0.0) 0%, rgba(192,56,40,0.05) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.gen-btn:hover {
  border-color: var(--red);
  background: rgba(192, 56, 40, 0.07);
  box-shadow: 0 0 24px rgba(192, 56, 40, 0.12);
}
.gen-btn:hover::after { opacity: 1; }
.gen-btn:active       { transform: scale(0.975); }

.gen-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 17px;
  font-weight: 500;
  letter-spacing: 0.35em;
  color: var(--red);
  position: relative;
  z-index: 1;
}

.gen-en {
  font-family: 'Cinzel', serif;
  font-size: 8px;
  letter-spacing: 0.32em;
  color: var(--red-dim);
  opacity: 0.55;
  text-transform: uppercase;
  position: relative;
  z-index: 1;
}

/* ── Responsive (mobile) ── */
@media (max-width: 820px) {
  .control-panel {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
    padding: 16px 0 4px;
  }

  .param-row {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    flex: none;
  }

  .param-group {
    gap: 6px;
  }

  .arrow-sep {
    display: none;
  }

  .pill-bar {
    flex-wrap: wrap;
  }

  .pill {
    flex: 1 1 auto;
    padding: 6px 10px;
  }

  .pill-zh { font-size: 12px; }

  /* 文化适配强度滑块 */
  .intensity-group { min-width: 0; }

  .intensity-pole {
    padding: 6px 10px;
  }

  .pole-zh { font-size: 12px; }

  /* tooltip 在小屏改成靠左定位，避免溢出视口 */
  .help-tip {
    width: min(320px, calc(100vw - 32px));
    left: 0;
    transform: translateX(0) translateY(4px);
    font-size: 12.5px;
    line-height: 1.7;
  }
  .tip-line strong { font-size: 13px; }
  .tip-cite { font-size: 10px; }
  .help-tip::after { left: 12px; transform: translateX(0); }
  .help-btn:hover .help-tip,
  .help-btn:focus-visible .help-tip {
    transform: translateX(0) translateY(0);
  }

  /* 生成按钮：占满整行，作为页面的主要触发器 */
  .gen-btn {
    align-self: stretch;
    width: 100%;
    padding: 12px;
    margin-top: 4px;
  }

  .gen-zh { font-size: 16px; letter-spacing: 0.3em; }
}
</style>
