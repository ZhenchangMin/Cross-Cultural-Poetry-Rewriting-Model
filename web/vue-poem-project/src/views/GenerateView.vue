<template>
  <div class="container">
    <h1>诗歌跨文化重写系统</h1>

    <div class="main">
      <!-- 输入 -->
      <InputBox v-model="text" />

      <!-- 控制 -->
      <ControlPanel
        v-model:style="style"
        v-model:culture="culture"
        v-model:emotion="emotion"
        @generate="handleGenerate"
      />

      <!-- 输出 -->
      <PoemCard :result="result" :loading="loading" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InputBox from '../components/InputBox.vue'
import ControlPanel from '../components/ControlPanel.vue'
import PoemCard from '../components/PoemCard.vue'

// ⭐先用假数据测试（后面再接后端）
const mockAPI = (data) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        result: `【${data.targetCulture}-${data.style}-${data.emotion}风格】\n${data.text}\n（AI改写示例）`
      })
    }, 1000)
  })
}

const text = ref('')
const result = ref('')
const style = ref('modern')
const culture = ref('Chinese')
const emotion = ref('neutral')
const loading = ref(false)

const handleGenerate = async () => {
  if (!text.value) {
    alert('请输入诗歌')
    return
  }

  loading.value = true

  try {
    const res = await mockAPI({
      text: text.value,
      style: style.value,
      targetCulture: culture.value,
      emotion: emotion.value
    })

    result.value = res.result
  } catch (e) {
    result.value = '生成失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.container {
  padding: 20px;
}

.main {
  display: flex;
  gap: 20px;
}
</style>