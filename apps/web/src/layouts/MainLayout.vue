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
}

.main-content {
  flex: 1;
  padding-top: 64px; /* 头部高度 */
  padding-bottom: 40px;
}
</style> 