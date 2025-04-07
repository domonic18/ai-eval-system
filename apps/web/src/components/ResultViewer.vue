<template>
  <div class="result-viewer">
    <div class="result-header">
      <h2>评测结果 - {{ taskId ? `#${taskId}` : '' }}</h2>
      <button @click="close" class="close-btn">&times;</button>
    </div>
    
    <div v-if="loading" class="result-loading">
      <div class="spinner"></div>
      <p>正在加载评测结果...</p>
    </div>
    
    <div v-else-if="error" class="result-error">
      <div class="error-icon">!</div>
      <p>{{ error }}</p>
      <button @click="close" class="btn btn-secondary">关闭</button>
    </div>
    
    <div v-else-if="!hasResults" class="result-empty">
      <div class="info-icon">i</div>
      <p>{{ resultData.message || '暂无评测结果' }}</p>
      <button @click="close" class="btn btn-secondary">关闭</button>
    </div>
    
    <div v-else class="result-content">
      <!-- 结果概览部分 -->
      <div class="result-summary">
        <div class="summary-item">
          <h3>基本信息</h3>
          <div class="info-grid">
            <div>
              <strong>模型:</strong>
              <span>{{ resultData.model_name }}</span>
            </div>
            <div>
              <strong>数据集:</strong>
              <span>{{ formatDatasetNames(resultData.dataset_names) }}</span>
            </div>
            <div>
              <strong>状态:</strong>
              <span :class="'status-' + resultData.status.toLowerCase()">
                {{ formatStatus(resultData.status) }}
              </span>
            </div>
            <div>
              <strong>创建时间:</strong>
              <span>{{ formatDate(resultData.created_at) }}</span>
            </div>
            <div>
              <strong>完成时间:</strong>
              <span>{{ formatDate(resultData.updated_at) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 摘要部分 -->
      <div class="result-summary-data" v-if="resultData.results && resultData.results.summary && resultData.results.summary.length">
        <h3>评测摘要</h3>
        <div class="summary-table-container">
          <table class="summary-table">
            <thead>
              <tr>
                <th v-for="(_, key) in resultData.results.summary[0]" :key="key">{{ formatColumnHeader(key) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in resultData.results.summary" :key="index">
                <td v-for="(value, key) in item" :key="`${index}-${key}`">{{ value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- 下载按钮 -->
      <div class="result-actions">
        <button @click="downloadResults" class="btn btn-primary" :disabled="downloading">
          <span v-if="!downloading">下载完整结果</span>
          <span v-else>下载中...</span>
        </button>
        <button @click="close" class="btn btn-secondary">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultViewer',
  props: {
    taskId: {
      type: [Number, String],
      required: true
    }
  },
  data() {
    return {
      loading: true,
      error: null,
      resultData: null,
      hasResults: false,
      downloading: false
    }
  },
  mounted() {
    this.fetchResults()
  },
  methods: {
    async fetchResults() {
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch(`/api/v1/evaluations/${this.taskId}/results`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '获取评测结果失败')
        }
        
        this.resultData = await response.json()
        this.hasResults = this.resultData.has_results
        
      } catch (error) {
        console.error('获取评测结果失败:', error)
        this.error = error.message || '获取评测结果失败，请稍后再试'
      } finally {
        this.loading = false
      }
    },
    
    async downloadResults() {
      this.downloading = true
      
      try {
        // 创建下载链接，使用原生浏览器下载
        const token = localStorage.getItem('token')
        const downloadUrl = `/api/v1/evaluations/${this.taskId}/download`
        
        // 创建一个临时链接并模拟点击，自动开始下载
        const link = document.createElement('a')
        link.href = downloadUrl
        link.setAttribute('download', `evaluation_${this.taskId}_results.zip`)
        
        // 添加授权头（如果服务器支持URL参数授权，也可以使用URL参数）
        // 注意：对于某些服务器配置，这可能不起作用，因为浏览器下载不会携带自定义头
        // 这种情况下，你可能需要在后端实现一个特殊的下载端点，它接受token作为URL参数
        if (token) {
          // 如果后端支持查询参数授权，可以使用：
          link.href = `${downloadUrl}?token=${token}`
        }
        
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
      } catch (error) {
        console.error('下载结果失败:', error)
        this.$notify({
          type: 'error',
          title: '下载失败',
          text: error.message || '下载结果失败，请稍后再试'
        })
      } finally {
        this.downloading = false
      }
    },
    
    close() {
      this.$emit('close')
    },
    
    formatDatasetNames(datasets) {
      if (!datasets) return '无'
      if (typeof datasets === 'string') return datasets
      if (Array.isArray(datasets)) return datasets.join(', ')
      return JSON.stringify(datasets)
    },
    
    formatStatus(status) {
      const statusMap = {
        'PENDING': '等待中',
        'RUNNING': '运行中',
        'COMPLETED': '已完成',
        'FAILED': '失败',
        'TERMINATED': '已终止',
        'UNKNOWN': '未知'
      }
      return statusMap[status] || status
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '无'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN')
    },
    
    formatPercent(value) {
      if (value === undefined || value === null) return '无数据'
      const num = parseFloat(value)
      return isNaN(num) ? value : `${(num * 1).toFixed(2)}`
    },
    
    formatMetricValue(value) {
      if (typeof value === 'number') {
        return value.toFixed(4)
      }
      return value
    },
    
    formatColumnHeader(header) {
      // 将snake_case转换为更友好的显示格式
      return header
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
    },
    
    getAdditionalMetrics(metrics) {
      const result = {}
      if (!metrics) return result
      
      // 过滤掉accuracy和file_path，只保留其他指标
      Object.keys(metrics).forEach(key => {
        if (key !== 'accuracy' && key !== 'file_path') {
          result[key] = metrics[key]
        }
      })
      
      return result
    }
  }
}
</script>

<style scoped>
.result-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f8fafc;
}

.result-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #2d3748;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #718096;
  line-height: 1;
}

.result-content {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.result-loading, .result-error, .result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  height: 100%;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #3182ce;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon, .info-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  margin-bottom: 16px;
  font-size: 24px;
  font-weight: bold;
}

.error-icon {
  background-color: #fed7d7;
  color: #e53e3e;
}

.info-icon {
  background-color: #bee3f8;
  color: #3182ce;
}

.result-summary {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.info-grid > div {
  display: flex;
  flex-direction: column;
}

.info-grid strong {
  font-size: 0.85rem;
  color: #718096;
  margin-bottom: 4px;
}

.status-completed {
  color: #38a169;
}

.status-running {
  color: #3182ce;
}

.status-failed, .status-terminated {
  color: #e53e3e;
}

.status-pending {
  color: #d69e2e;
}

.metrics-table-container, .summary-table-container {
  overflow-x: auto;
  margin-top: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.metrics-table, .summary-table {
  width: 100%;
  border-collapse: collapse;
}

.metrics-table th, .metrics-table td,
.summary-table th, .summary-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.metrics-table th, .summary-table th {
  background-color: #f8fafc;
  font-weight: 600;
  color: #4a5568;
}

.metrics-table tr:hover, .summary-table tr:hover {
  background-color: #f8fafc;
}

.metric-badge {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px;
  background-color: #ebf4ff;
  color: #3182ce;
  border-radius: 12px;
  font-size: 0.8rem;
}

.result-metrics, .result-summary-data {
  margin-bottom: 24px;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
}

.btn-primary {
  background-color: #3182ce;
  color: white;
}

.btn-primary:hover {
  background-color: #2c5282;
}

.btn-primary:disabled {
  background-color: #90cdf4;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #e2e8f0;
  color: #4a5568;
}

.btn-secondary:hover {
  background-color: #cbd5e0;
}

h3 {
  font-size: 1.2rem;
  color: #2d3748;
  margin-bottom: 0.5rem;
}
</style> 