<template>
  <div class="control-panel">
    <div class="param-row">

      <div class="param-group">
        <span class="param-label">文化语境</span>
        <div class="pill-bar">
          <button
            v-for="opt in cultures" :key="opt.value"
            class="pill" :class="{ active: cultureVal === opt.value }"
            @click="cultureVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
        </div>
      </div>

      <div class="param-group">
        <span class="param-label">诗歌风格</span>
        <div class="pill-bar">
          <button
            v-for="opt in styles" :key="opt.value"
            class="pill" :class="{ active: styleVal === opt.value }"
            @click="styleVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
        </div>
      </div>

      <div class="param-group">
        <span class="param-label">情感基调</span>
        <div class="pill-bar">
          <button
            v-for="opt in emotions" :key="opt.value"
            class="pill" :class="{ active: emotionVal === opt.value }"
            @click="emotionVal = opt.value"
          >
            <span class="pill-zh">{{ opt.zh }}</span>
            <span class="pill-en">{{ opt.en }}</span>
          </button>
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
import { computed } from 'vue'

const props = defineProps(['style', 'culture', 'emotion'])
const emit = defineEmits(['update:style', 'update:culture', 'update:emotion', 'generate'])

const cultures = [
  { value: 'Chinese', zh: '中文', en: 'ZH' },
  { value: 'Korean',  zh: '韩语', en: 'KO' },
  { value: 'Russian', zh: '俄语', en: 'RU' },
]
const styles = [
  { value: 'classical', zh: '古典', en: 'Classical' },
  { value: 'modern',    zh: '现代', en: 'Modern'    },
]
const emotions = [
  { value: 'neutral',    zh: '中性', en: 'Neutral'    },
  { value: 'melancholy', zh: '忧郁', en: 'Melancholy' },
  { value: 'joyful',     zh: '欢快', en: 'Joyful'     },
]

const styleVal   = computed({ get: () => props.style,   set: v => emit('update:style', v) })
const cultureVal = computed({ get: () => props.culture, set: v => emit('update:culture', v) })
const emotionVal = computed({ get: () => props.emotion, set: v => emit('update:emotion', v) })
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
  gap: 32px;
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
  transition: background 0.2s;
}

.pill:hover { background: var(--ink-surface); }

.pill.active {
  background: var(--red-ghost);
  box-shadow: inset 0 0 0 1px var(--red-border);
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

/* ── Generate button (朱砂 red) ── */
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
