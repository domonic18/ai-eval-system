<template>
  <footer class="footer">
    <div class="container footer-container">
      <div class="footer-left">
        <p>&copy; {{ currentYear }} OpenCompass在线评测系统. 保留所有权利。</p>
      </div>
      <div class="footer-right">
        <a href="https://github.com/InternLM/opencompass" target="_blank" class="github-link">
          <svg class="github-icon" viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
          </svg>
          <span>GitHub</span>
        </a>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'TheFooter',
  computed: {
    currentYear() {
      return new Date().getFullYear()
    }
  }
}
</script>

<style scoped>
.footer {
  background-color: #2d3748;
  color: #e2e8f0;
  padding: 24px 0;
  margin-top: auto; /* 确保footer始终在底部 */
}

.footer-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  font-size: 14px;
}

.github-link {
  display: flex;
  align-items: center;
  color: #e2e8f0;
  text-decoration: none;
  transition: color 0.3s;
}

.github-link:hover {
  color: #fff;
}

.github-icon {
  margin-right: 8px;
}

@media (max-width: 768px) {
  .footer-container {
    flex-direction: column;
    text-align: center;
  }
  
  .footer-left {
    margin-bottom: 16px;
  }
}
</style>