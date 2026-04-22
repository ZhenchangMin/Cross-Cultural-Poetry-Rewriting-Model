<template>
  <div class="box">
    <h3>生成结果</h3>

    <div v-if="loading">生成中...</div>

    <el-input
      v-else
      type="textarea"
      :rows="15"
      :model-value="result"
      readonly
    />
  </div>
</template>

<script setup>
defineProps(['result', 'loading'])
</script>

<style scoped>
.box {
  flex: 1;
}
</style>