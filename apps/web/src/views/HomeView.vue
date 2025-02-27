<template>
  <MainLayout>
    <div class="home">
      <section class="hero">
        <div class="container">
          <div class="hero-content">
            <h1 class="hero-title">司南 OpenCompass</h1>
            <p class="hero-description">专业、全面的AI大模型评测平台</p>
            <div class="hero-actions">
              <router-link to="/evaluation" class="btn">开始评测</router-link>
              <router-link to="/guide" class="btn btn-secondary">了解更多</router-link>
            </div>
          </div>
        </div>
      </section>
      
      <section class="features">
        <div class="container">
          <h2 class="section-title">平台特点</h2>
          
          <div class="feature-grid">
            <div class="feature-card">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
              </div>
              <h3 class="feature-title">全面的评测指标</h3>
              <p class="feature-description">涵盖准确性、流畅性、创造力等多维度评测指标，全方位评估模型性能。</p>
            </div>
            
            <div class="feature-card">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M12 8v4l3 3"></path>
                </svg>
              </div>
              <h3 class="feature-title">高效快速</h3>
              <p class="feature-description">采用高性能分布式计算架构，显著提升评测速度，快速获取评测结果。</p>
            </div>
            
            <div class="feature-card">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                  <polyline points="7.5 4.21 12 6.81 16.5 4.21"></polyline>
                  <polyline points="7.5 19.79 7.5 14.6 3 12"></polyline>
                  <polyline points="21 12 16.5 14.6 16.5 19.79"></polyline>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                  <line x1="12" y1="22.08" x2="12" y2="12"></line>
                </svg>
              </div>
              <h3 class="feature-title">丰富的数据集</h3>
              <p class="feature-description">提供多语言、多任务、多场景的评测数据集，满足不同评测需求。</p>
            </div>
            
            <div class="feature-card">
              <div class="feature-icon">
                <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 7h-9"></path>
                  <path d="M14 17H5"></path>
                  <circle cx="17" cy="17" r="3"></circle>
                  <circle cx="7" cy="7" r="3"></circle>
                </svg>
              </div>
              <h3 class="feature-title">模型对比</h3>
              <p class="feature-description">支持多模型同时评测对比，直观展示各模型的优劣势。</p>
            </div>
          </div>
        </div>
      </section>
      
      <section class="cta">
        <div class="container">
          <div class="cta-content">
            <h2 class="cta-title">立即开始您的模型评测</h2>
            <p class="cta-description">使用专业的评测工具，全面了解您的模型性能</p>
            <router-link to="/evaluation" class="btn">开始评测</router-link>
          </div>
        </div>
      </section>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '@/layouts/MainLayout.vue'

export default {
  name: 'HomeView',
  components: {
    MainLayout
  }
}
</script>

<style scoped>
.hero {
  padding: 80px 0;
  background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
  color: white;
  text-align: center;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
}

.hero-description {
  font-size: 20px;
  max-width: 600px;
  margin: 0 auto 32px;
  opacity: 0.9;
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.hero-actions .btn {
  padding: 12px 24px;
  font-size: 16px;
}

.features {
  padding: 80px 0;
  background-color: #f7fafc;
}

.section-title {
  text-align: center;
  font-size: 32px;
  margin-bottom: 48px;
  color: #2d3748;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 32px;
}

.feature-card {
  background-color: white;
  border-radius: 8px;
  padding: 32px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  color: #3182ce;
  margin-bottom: 24px;
}

.feature-title {
  font-size: 20px;
  margin-bottom: 16px;
  color: #2d3748;
}

.feature-description {
  color: #718096;
  line-height: 1.6;
}

.cta {
  padding: 80px 0;
  background-color: #2c5282;
  color: white;
  text-align: center;
}

.cta-content {
  max-width: 700px;
  margin: 0 auto;
}

.cta-title {
  font-size: 32px;
  margin-bottom: 16px;
}

.cta-description {
  font-size: 18px;
  margin-bottom: 32px;
  opacity: 0.9;
}

.cta .btn {
  padding: 12px 32px;
  font-size: 18px;
  background-color: white;
  color: #2c5282;
}

.cta .btn:hover {
  background-color: #f7fafc;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 36px;
  }
  
  .hero-description {
    font-size: 18px;
  }
  
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style> 