<template>
  <MainLayout>
    <div class="guide-page page-content">
      <div class="guide-container">
        <div class="guide-header">
          <h1>使用指南</h1>
          <p>了解如何使用OpenCompass在线评测系统</p>
        </div>
        
        <div class="guide-content">
          <div class="guide-toc">
            <div class="toc-title">目录</div>
            <ul class="toc-list">
              <li><a href="#introduction" class="toc-link">平台介绍</a></li>
              <li><a href="#evaluation" class="toc-link">在线评测</a></li>
              <li><a href="#datasets" class="toc-link">数据集管理</a></li>
              <li><a href="#models" class="toc-link">模型管理</a></li>
              <li><a href="#arena" class="toc-link">竞技场</a></li>
              <li><a href="#faq" class="toc-link">常见问题</a></li>
            </ul>
          </div>
          
          <div class="guide-sections">
            <section id="introduction" class="guide-section">
              <h2 class="section-title">平台介绍</h2>
              <div class="section-content">
                <p>OpenCompass 是一个专业、全面的AI大模型评测平台，旨在为研究人员和开发者提供便捷、可靠的模型评测工具。平台基于OpenCompass框架构建，支持多维度、多场景的模型评测，帮助用户全面了解模型性能。</p>
                
                <div class="feature-list">
                  <div class="feature-item">
                    <div class="feature-icon">📊</div>
                    <div class="feature-content">
                      <h3>全面评测</h3>
                      <p>支持多维度评测指标，全方位分析模型性能</p>
                    </div>
                  </div>
                  
                  <div class="feature-item">
                    <div class="feature-icon">⚡</div>
                    <div class="feature-content">
                      <h3>高效快速</h3>
                      <p>分布式评测架构，大幅提升评测速度</p>
                    </div>
                  </div>
                  
                  <div class="feature-item">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-content">
                      <h3>深入分析</h3>
                      <p>提供详细的评测报告和可视化分析</p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
            
            <section id="evaluation" class="guide-section">
              <h2 class="section-title">在线评测</h2>
              <div class="section-content">
                <h3>创建评测任务</h3>
                <p>在"在线评测"页面，您可以创建新的评测任务。创建任务需要以下几个步骤：</p>
                
                <ol class="step-list">
                  <li>
                    <strong>选择模型</strong>：从系统提供的模型库中选择要评测的模型，或添加自定义模型。
                  </li>
                  <li>
                    <strong>选择评测集</strong>：选择一个或多个评测数据集，系统提供了丰富的预设数据集。
                  </li>
                  <li>
                    <strong>配置评测参数</strong>：根据需求设置评测参数，如批处理大小、评测指标等。
                  </li>
                  <li>
                    <strong>提交任务</strong>：点击"开始评测"按钮提交任务。
                  </li>
                </ol>
                
                <div class="note">
                  <strong>注意</strong>：评测任务可能需要较长时间，您可以在任务列表中查看进度，或者开启通知接收任务完成提醒。
                </div>
                
                <h3>查看评测结果</h3>
                <p>评测完成后，您可以：</p>
                <ul>
                  <li>查看详细的评测报告和指标分析</li>
                  <li>下载评测结果数据</li>
                  <li>比较不同模型的评测结果</li>
                  <li>分享评测结果（如果您希望公开）</li>
                </ul>
              </div>
            </section>
            
            <section id="faq" class="guide-section">
              <h2 class="section-title">常见问题</h2>
              <div class="section-content">
                <div class="faq-item">
                  <div class="faq-question">评测需要多长时间？</div>
                  <div class="faq-answer">
                    <p>评测时间取决于多个因素：模型复杂度、数据集大小、评测参数设置等。小型评测可能几分钟内完成，而大型评测可能需要数小时甚至更长时间。</p>
                  </div>
                </div>
                
                <div class="faq-item">
                  <div class="faq-question">如何确保评测结果准确？</div>
                  <div class="faq-answer">
                    <p>平台采用多重验证机制，包括重复测试、统计显著性检验等方法确保结果可靠。对于重要评测，建议执行多次并取平均值。</p>
                  </div>
                </div>
                
                <div class="faq-item">
                  <div class="faq-question">是否支持自定义评测指标？</div>
                  <div class="faq-answer">
                    <p>是的，高级用户可以定义自定义评测指标和评分标准。您需要提供评分函数的具体实现。请参考开发者文档了解详情。</p>
                  </div>
                </div>
                
                <div class="faq-item">
                  <div class="faq-question">如何获取技术支持？</div>
                  <div class="faq-answer">
                    <p>如遇到问题，您可以通过以下方式获取帮助：</p>
                    <ul>
                      <li>查阅详细文档</li>
                      <li>访问GitHub仓库提交Issue</li>
                      <li>联系技术支持团队</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import { defineComponent } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'

export default defineComponent({
  name: 'GuideView',
  components: {
    MainLayout
  }
})
</script>

<style scoped>
.guide-page {
  width: 100%;
}

.guide-container {
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  padding: 20px;
  box-sizing: border-box;
  margin-top: var(--header-height);
}

.guide-header {
  text-align: center;
  margin-bottom: 40px;
}

.guide-header h1 {
  font-size: 2.5rem;
  color: #2c5282;
  margin-bottom: 10px;
}

.guide-header p {
  font-size: 1.2rem;
  color: #718096;
}

.guide-content {
  display: flex;
  gap: 32px;
}

.guide-toc {
  width: 250px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
  align-self: flex-start;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 20px;
}

.toc-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.toc-list {
  list-style: none;
  padding: 0;
}

.toc-link {
  display: block;
  padding: 8px 0;
  color: #4a5568;
  text-decoration: none;
  transition: color 0.3s;
}

.toc-link:hover {
  color: #3182ce;
}

.guide-sections {
  flex: 1;
}

.guide-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 32px;
  margin-bottom: 32px;
}

.section-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #2d3748;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.section-content {
  font-size: 16px;
  line-height: 1.6;
  color: #4a5568;
}

.section-content h3 {
  font-size: 20px;
  margin: 24px 0 16px;
  color: #2d3748;
}

.section-content p {
  margin-bottom: 16px;
}

.feature-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 24px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  background-color: #f7fafc;
  border-radius: 8px;
  padding: 20px;
}

.feature-icon {
  font-size: 24px;
  margin-right: 16px;
}

.feature-content h3 {
  margin: 0 0 8px;
  font-size: 18px;
}

.step-list {
  padding-left: 20px;
  margin-bottom: 20px;
}

.step-list li {
  margin-bottom: 12px;
}

.note {
  background-color: #ebf8ff;
  border-left: 4px solid #3182ce;
  padding: 16px;
  border-radius: 4px;
  margin: 20px 0;
}

pre {
  background-color: #2d3748;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  margin: 20px 0;
}

.faq-item {
  margin-bottom: 24px;
}

.faq-question {
  font-weight: 600;
  font-size: 18px;
  margin-bottom: 12px;
  color: #2d3748;
}

.faq-answer {
  padding-left: 16px;
  border-left: 2px solid #3182ce;
}

@media (max-width: 768px) {
  .guide-content {
    flex-direction: column;
  }
  
  .guide-toc {
    width: 100%;
    position: static;
    margin-bottom: 24px;
  }
}

.page-content {
  min-height: calc(100vh - var(--header-height));
  box-sizing: border-box;
}

.main-content {
  padding-top: 0;
  margin-top: var(--header-height);
}

/* 添加指南页面链接专用样式 */
.guide-link {
  color: #3182ce;
  text-decoration: none;
  transition: color 0.3s;
  padding: 0 2px;
}

.guide-link:hover {
  color: #2c5282;
  text-decoration: underline;
  background-color: transparent; /* 确保指南链接hover时没有背景色 */
}
</style> 