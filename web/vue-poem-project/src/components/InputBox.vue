<template>
  <div class="input-pane">
    <div class="pane-label">
      <span class="label-seq">一</span>
      <span class="label-zh">原 诗</span>
      <span class="label-en">Source Poem</span>
    </div>

    <div class="field-wrap" :class="{ focused }">
      <div class="corner tl"></div>
      <div class="corner tr"></div>
      <div class="corner bl"></div>
      <div class="corner br"></div>
      <textarea
        v-model="inputValue"
        class="poem-field"
        placeholder="在此输入原诗…&#10;&#10;Enter poem here…"
        spellcheck="false"
        @focus="focused = true"
        @blur="focused = false"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const focused = ref(false)

const inputValue = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})
</script>

<style scoped>
.input-pane {
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

.field-wrap {
  flex: 1;
  position: relative;
  background: var(--ink-surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.field-wrap.focused {
  border-color: var(--border-bright);
  box-shadow: var(--glow), var(--shadow);
}

.poem-field {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  padding: 22px 24px;
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  line-height: 2;
  color: var(--text-parchment);
  caret-color: var(--red);
}

.poem-field::placeholder {
  color: var(--text-faded);
  font-style: italic;
  line-height: 2;
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
</style>
