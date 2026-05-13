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
        <span class="param-label">文化适配强度</span>
        <div class="intensity-wrap">
          <span class="intensity-pole">异化</span>
          <div class="slider-track-wrap">
            <input
              type="range" min="1" max="5" step="1"
              v-model.number="intensityVal"
              class="intensity-slider"
            />
            <div class="tick-row">
              <span
                v-for="n in 5" :key="n"
                class="tick" :class="{ active: intensityVal === n }"
              >{{ n }}</span>
            </div>
          </div>
          <span class="intensity-pole">归化</span>
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

// 切换目标语言时，如当前形式不在新列表中，自动重置为该语言下第一个形式
watch(targetLangVal, () => {
  const list = currentStyles.value
  if (!list.some(s => s.value === styleVal.value)) {
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
  font-size: 10px;
  letter-spacing: 0.28em;
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
.intensity-group { min-width: 200px; }

.intensity-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ink-raised);
  border: 1px solid var(--border);
  padding: 3px 12px; /* 与 pill-bar 外层 padding 一致 */
  box-shadow: inset 0 1px 3px rgba(120, 80, 20, 0.06);
}

.intensity-pole {
  font-family: 'Noto Serif SC', serif;
  font-size: 10px;
  color: var(--text-faded);
  letter-spacing: 0.05em;
  white-space: nowrap;
  flex-shrink: 0;
}

.slider-track-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 2px;
  padding: 20px 0 8px; /* 总高与 pill-bar 一致，红色滑轨偏下 */
}

.intensity-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 2px;
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

.tick-row {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
}

.tick {
  font-family: 'Cinzel', serif;
  font-size: 8px;
  color: var(--text-faded);
  opacity: 0.4;
  transition: opacity 0.2s, color 0.2s;
  line-height: 1;
}

.tick.active {
  color: var(--red);
  opacity: 0.8;
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
</style>
