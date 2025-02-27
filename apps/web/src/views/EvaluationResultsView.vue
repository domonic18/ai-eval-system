<template>
  <MainLayout>
    <div class="results-page">
      <div class="container">
        <h1 class="page-title">评测结果</h1>
        
        <div class="results-filters">
          <div class="filter-group">
            <label class="filter-label">模型类型</label>
            <select v-model="filters.modelType" class="filter-select">
              <option value="">全部</option>
              <option value="text">文本生成</option>
              <option value="chat">对话</option>
              <option value="code">代码</option>
              <option value="multimodal">多模态</option>
            </select>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">数据集</label>
            <select v-model="filters.dataset" class="filter-select">
              <option value="">全部</option>
              <option value="mmlu">MMLU</option>
              <option value="cmmlu">CMMLU</option>
              <option value="agieval">AGIEval</option>
              <option value="mbpp">MBPP</option>
            </select>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">评估指标</label>
            <select v-model="filters.metric" class="filter-select">
              <option value="accuracy">准确率</option>
              <option value="f1">F1 分数</option>
              <option value="rouge">ROUGE</option>
              <option value="bleu">BLEU</option>
            </select>
          </div>
          
          <button @click="applyFilters" class="btn">应用筛选</button>
        </div>
        
        <div class="results-content">
          <div class="results-table-container">
            <table class="results-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>模型</th>
                  <th>提供商</th>
                  <th>参数规模</th>
                  <th>
                    {{ getMetricLabel() }}
                    <span class="sort-icon" @click="toggleSort">
                      {{ sortAsc ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th>评测时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(model, index) in sortedResults" :key="model.id">
                  <td>{{ index + 1 }}</td>
                  <td>{{ model.name }}</td>
                  <td>{{ model.provider }}</td>
                  <td>{{ model.parameters }}</td>
                  <td>{{ formatScore(model.score) }}</td>
                  <td>{{ formatDate(model.date) }}</td>
                  <td>
                    <button @click="viewDetails(model.id)" class="action-btn details-btn">详情</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="results-chart">
            <h2 class="chart-title">模型性能比较</h2>
            <!-- 这里可以集成图表库，如ECharts或Chart.js -->
            <div class="chart-placeholder">
              <div class="chart-bars">
                <div 
                  v-for="model in topModels" 
                  :key="model.id" 
                  class="chart-bar"
                  :style="{ height: `${model.score * 100}%` }"
                >
                  <div class="bar-label">{{ model.name }}</div>
                  <div class="bar-value">{{ formatScore(model.score) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 详情弹窗 -->
      <div v-if="selectedModel" class="modal">
        <div class="modal-content details-modal">
          <div class="modal-header">
            <h2>{{ selectedModel.name }} 详细评测结果</h2>
            <button @click="selectedModel = null" class="close-btn">&times;</button>
          </div>
          <div class="modal-body">
            <div class="model-info">
              <div class="info-item">
                <span class="info-label">模型名称:</span>
                <span class="info-value">{{ selectedModel.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">提供商:</span>
                <span class="info-value">{{ selectedModel.provider }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">参数规模:</span>
                <span class="info-value">{{ selectedModel.parameters }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">评测日期:</span>
                <span class="info-value">{{ formatDate(selectedModel.date) }}</span>
              </div>
            </div>
            
            <h3 class="details-subtitle">评测结果</h3>
            <div class="metrics-grid">
              <div class="metric-card" v-for="(value, key) in selectedModel.metrics" :key="key">
                <div class="metric-name">{{ getMetricName(key) }}</div>
                <div class="metric-value">{{ formatScore(value) }}</div>
              </div>
            </div>
            
            <h3 class="details-subtitle">分类性能</h3>
            <div class="category-chart">
              <!-- 这里可以放置分类性能图表 -->
              <div class="category-bars">
                <div 
                  v-for="(value, category) in selectedModel.categories" 
                  :key="category"
                  class="category-bar"
                >
                  <div class="category-name">{{ category }}</div>
                  <div class="category-bar-container">
                    <div class="category-bar-fill" :style="{ width: `${value * 100}%` }"></div>
                  </div>
                  <div class="category-value">{{ formatScore(value) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script>
import MainLayout from '@/layouts/MainLayout.vue'

export default {
  name: 'EvaluationResultsView',
  components: {
    MainLayout
  },
  data() {
    return {
      filters: {
        modelType: '',
        dataset: '',
        metric: 'accuracy'
      },
      sortAsc: false,
      selectedModel: null,
      // 模拟数据
      models: [
        {
          id: 1,
          name: 'ChatGPT-4',
          provider: 'OpenAI',
          parameters: '1.76T',
          score: 0.89,
          date: '2023-10-15',
          metrics: {
            accuracy: 0.89,
            f1: 0.87,
            rouge: 0.82,
            bleu: 0.78
          },
          categories: {
            '常识推理': 0.92,
            '数学': 0.85,
            '编程': 0.88,
            '语言理解': 0.91,
            '知识问答': 0.87
          }
        },
        {
          id: 2,
          name: 'Claude 2',
          provider: 'Anthropic',
          parameters: '800B',
          score: 0.85,
          date: '2023-09-22',
          metrics: {
            accuracy: 0.85,
            f1: 0.83,
            rouge: 0.79,
            bleu: 0.75
          },
          categories: {
            '常识推理': 0.87,
            '数学': 0.81,
            '编程': 0.83,
            '语言理解': 0.90,
            '知识问答': 0.84
          }
        },
        {
          id: 3,
          name: 'Llama 2-70B',
          provider: 'Meta',
          parameters: '70B',
          score: 0.82,
          date: '2023-08-10',
          metrics: {
            accuracy: 0.82,
            f1: 0.80,
            rouge: 0.76,
            bleu: 0.72
          },
          categories: {
            '常识推理': 0.85,
            '数学': 0.79,
            '编程': 0.81,
            '语言理解': 0.86,
            '知识问答': 0.80
          }
        },
        {
          id: 4,
          name: 'ChatGLM-6B',
          provider: 'THUDM',
          parameters: '6B',
          score: 0.78,
          date: '2023-07-18',
          metrics: {
            accuracy: 0.78,
            f1: 0.76,
            rouge: 0.73,
            bleu: 0.69
          },
          categories: {
            '常识推理': 0.80,
            '数学': 0.75,
            '编程': 0.76,
            '语言理解': 0.82,
            '知识问答': 0.78
          }
        },
        {
          id: 5,
          name: 'Falcon-40B',
          provider: 'TII',
          parameters: '40B',
          score: 0.80,
          date: '2023-08-25',
          metrics: {
            accuracy: 0.80,
            f1: 0.78,
            rouge: 0.75,
            bleu: 0.71
          },
          categories: {
            '常识推理': 0.83,
            '数学': 0.77,
            '编程': 0.79,
            '语言理解': 0.85,
            '知识问答': 0.79
          }
        }
      ]
    }
  },
  computed: {
    filteredResults() {
      let results = [...this.models]
      
      if (this.filters.modelType) {
        // 实际应用中，需要根据模型类型进行过滤
        // 这里仅为示例
      }
      
      if (this.filters.dataset) {
        // 实际应用中，需要根据数据集进行过滤
        // 这里仅为示例
      }
      
      return results
    },
    sortedResults() {
      return this.filteredResults.sort((a, b) => {
        const scoreA = a.metrics[this.filters.metric]
        const scoreB = b.metrics[this.filters.metric]
        return this.sortAsc ? scoreA - scoreB : scoreB - scoreA
      })
    },
    topModels() {
      // 返回得分最高的5个模型用于图表显示
      return this.sortedResults.slice(0, 5)
    }
  },
  methods: {
    applyFilters() {
      // 实际应用中，可能需要从API获取数据
      console.log('应用筛选:', this.filters)
    },
    toggleSort() {
      this.sortAsc = !this.sortAsc
    },
    viewDetails(modelId) {
      this.selectedModel = this.models.find(model => model.id === modelId)
    },
    formatScore(score) {
      return (score * 100).toFixed(2) + '%'
    },
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString('zh-CN')
    },
    getMetricLabel() {
      return this.getMetricName(this.filters.metric)
    },
    getMetricName(key) {
      const metricNames = {
        'accuracy': '准确率',
        'f1': 'F1 分数',
        'rouge': 'ROUGE',
        'bleu': 'BLEU'
      }
      return metricNames[key] || key
    }
  }
}
</script>

<style scoped>
.results-page {
  padding: 0 0 40px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.results-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.filter-group {
  display: flex;
  flex-direction: column;
}

.filter-label {
  font-size: 14px;
  margin-bottom: 4px;
  color: #4a5568;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  min-width: 150px;
}

.results-content {
  display: flex;
  gap: 24px;
}

.results-table-container {
  flex: 2;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.results-table th {
  background-color: #f7fafc;
  font-weight: 600;
  color: #4a5568;
}

.sort-icon {
  cursor: pointer;
  display: inline-block;
  margin-left: 4px;
}

.action-btn {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 4px;
}

.details-btn {
  background-color: #3182ce;
  color: white;
  border: none;
  cursor: pointer;
}

.results-chart {
  flex: 1;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: 16px;
}

.chart-title {
  font-size: 18px;
  margin-bottom: 16px;
  color: #2d3748;
}

.chart-placeholder {
  height: 300px;
  position: relative;
}

.chart-bars {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 250px;
  position: relative;
  padding-top: 20px;
}

.chart-bar {
  width: 18%;
  background-color: #3182ce;
  border-radius: 4px 4px 0 0;
  position: relative;
  transition: height 0.3s;
  margin-top: auto;
}

.bar-label {
  position: absolute;
  bottom: -25px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-value {
  position: absolute;
  top: -20px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: #4a5568;
}

/* 详情弹窗样式 */
.details-modal {
  max-width: 800px;
}

.modal-body {
  padding: 24px;
}

.model-info {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.info-item {
  margin-bottom: 8px;
}

.info-label {
  font-weight: 600;
  width: 100px;
  display: inline-block;
}

.details-subtitle {
  font-size: 18px;
  margin: 24px 0 16px;
  color: #2d3748;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background-color: #f7fafc;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.metric-name {
  font-size: 14px;
  color: #4a5568;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #3182ce;
}

.category-bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.category-bar {
  display: flex;
  align-items: center;
}

.category-name {
  width: 100px;
  font-size: 14px;
  margin-right: 16px;
}

.category-bar-container {
  flex: 1;
  height: 12px;
  background-color: #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.category-bar-fill {
  height: 100%;
  background-color: #3182ce;
  border-radius: 6px;
}

.category-value {
  width: 60px;
  font-size: 14px;
  margin-left: 16px;
  text-align: right;
}

@media (max-width: 768px) {
  .results-content {
    flex-direction: column;
  }
  
  .results-filters {
    flex-direction: column;
  }
  
  .filter-group {
    width: 100%;
  }
}
</style> 