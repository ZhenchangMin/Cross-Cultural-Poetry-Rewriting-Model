<template>
  <div class="box">
    <h3>输入原诗</h3>
    <el-input
      type="textarea"
      :rows="15"
      v-model="inputValue"
      placeholder="请输入诗歌..."
    />
  </div>
</template>

<script setup>
/* eslint-disable */
import { computed } from 'vue'

const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])

const inputValue = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})
</script>

<style scoped>
.box {
  flex: 1;
}
</style>