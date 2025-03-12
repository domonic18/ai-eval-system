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
  min-width: 1200px;
  overflow-x: auto;
 }

.main-content {
  flex: 1;
  padding-bottom: 40px;
  width: 100%;
  overflow-x: auto;
}
</style> 