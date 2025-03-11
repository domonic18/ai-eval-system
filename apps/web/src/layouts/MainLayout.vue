<template>
  <div class="main-layout">
    <TheHeader />
    <main class="main-content">
      <slot></slot>
    </main>
    <TheFooter />
  </div>
</template>

<script>
import TheHeader from '@/components/TheHeader.vue'
import TheFooter from '@/components/TheFooter.vue'

export default {
  name: 'MainLayout',
  components: {
    TheHeader,
    TheFooter
  }
}
</script>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  width: 100%;
  min-width: 1200px; /* 设置最小宽度，确保内容不会太窄 */
}

.main-content {
  flex: 1;
  /* 不在这里设置统一的padding-top，而是在TheHeader.vue中设置固定高度，并在各页面根元素设置margin-top */
  padding-bottom: 40px;
  width: 100%;
  overflow-x: auto; /* 允许内容横向滚动 */
}
</style> 