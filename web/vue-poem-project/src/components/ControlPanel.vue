import { computed } from 'vue'
<template>
  <div class="box">
    <h3>参数设置</h3>

    <el-form label-width="80px">
      <el-form-item label="文化">
        <el-select v-model="cultureVal">
          <el-option label="中文" value="Chinese" />
          <el-option label="韩语" value="Korean" />
          <el-option label="俄语" value="Russian" />
        </el-select>
      </el-form-item>

      <el-form-item label="风格">
        <el-select v-model="styleVal">
          <el-option label="古典" value="classical" />
          <el-option label="现代" value="modern" />
        </el-select>
      </el-form-item>

      <el-form-item label="情感">
        <el-select v-model="emotionVal">
          <el-option label="中性" value="neutral" />
          <el-option label="忧郁" value="melancholy" />
          <el-option label="欢快" value="joyful" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-button type="primary" @click="$emit('generate')">
      生成
    </el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['style', 'culture', 'emotion'])
const emit = defineEmits([
  'update:style',
  'update:culture',
  'update:emotion',
  'generate'
])

const styleVal = computed({
  get: () => props.style,
  set: val => emit('update:style', val)
})

const cultureVal = computed({
  get: () => props.culture,
  set: val => emit('update:culture', val)
})

const emotionVal = computed({
  get: () => props.emotion,
  set: val => emit('update:emotion', val)
})
</script>

<style scoped>
.box {
  width: 250px;
}
</style>