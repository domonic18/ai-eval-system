<template>
  <footer class="footer">
    <div class="container footer-container">
      <div class="footer-left">
        <p>&copy; {{ currentYear }} OpenCompass在线评测系统. 保留所有权利。</p>
        <div class="version-info">
          <span>版本号：v1.0.0</span>
          <span class="build-info">Build: 20240615</span>
        </div>
      </div>
      <div class="footer-right">
        <a href="https://github.com/domonic18/ai-eval-system" target="_blank" class="github-link">
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
  background-color: #4a5568;
  color: #f7fafc;
  padding: 24px 0;
  margin-top: auto;
  border-top: 1px solid rgba(255,255,255,0.1);
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
  color: #cbd5e0;
  text-decoration: none;
  transition: color 0.3s;
}

.github-link:hover {
  color: #fff;
  text-decoration: underline;
}

.github-icon {
  margin-right: 8px;
}

.version-info {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.8;
  display: flex;
  gap: 12px;
  
  .build-info {
    font-family: monospace;
  }
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