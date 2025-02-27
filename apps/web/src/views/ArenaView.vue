<template>
  <MainLayout>
    <div class="arena-page">
      <div class="container">
        <h1 class="page-title">模型竞技场</h1>
        
        <div class="arena-content">
          <div class="arena-header">
            <p class="arena-description">
              在竞技场中，您可以选择多个模型进行同一评测任务的对抗比较，直观地了解各模型在相同条件下的表现差异。
            </p>
            <button @click="showCreateArena = true" class="btn">创建竞技场</button>
          </div>
          
          <!-- 当前活跃的竞技场 -->
          <div class="arena-section">
            <h2 class="section-title">活跃竞技场</h2>
            
            <div v-if="activeArenas.length === 0" class="empty-state">
              <p>当前没有活跃的竞技场，点击"创建竞技场"开始一场新的模型对抗。</p>
            </div>
            
            <div v-else class="arena-list">
              <div v-for="arena in activeArenas" :key="arena.id" class="arena-card">
                <div class="arena-card-header">
                  <h3 class="arena-name">{{ arena.name }}</h3>
                  <span class="arena-status" :class="arena.status.toLowerCase()">{{ getStatusText(arena.status) }}</span>
                </div>
                
                <div class="arena-info">
                  <div class="info-item">
                    <strong>数据集:</strong> {{ arena.dataset }}
                  </div>
                  <div class="info-item">
                    <strong>创建时间:</strong> {{ formatDate(arena.created_at) }}
                  </div>
                  <div class="info-item">
                    <strong>参与模型:</strong> {{ arena.participants.length }}个
                  </div>
                </div>
                
                <div class="arena-progress" v-if="arena.status === 'RUNNING'">
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: `${arena.progress}%` }"></div>
                  </div>
                  <div class="progress-text">{{ arena.progress }}%</div>
                </div>
                
                <div class="arena-actions">
                  <button @click="viewArenaDetails(arena.id)" class="arena-btn details-btn">查看详情</button>
                  <button 
                    v-if="arena.status === 'RUNNING'"
                    @click="terminateArena(arena.id)" 
                    class="arena-btn terminate-btn"
                  >
                    终止
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 历史竞技场 -->
          <div class="arena-section">
            <h2 class="section-title">历史竞技场</h2>
            
            <div class="arena-table-container">
              <table class="arena-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>数据集</th>
                    <th>状态</th>
                    <th>参与模型</th>
                    <th>冠军模型</th>
                    <th>完成时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="arena in completedArenas" :key="arena.id">
                    <td>{{ arena.name }}</td>
                    <td>{{ arena.dataset }}</td>
                    <td>
                      <span class="status-badge" :class="arena.status.toLowerCase()">
                        {{ getStatusText(arena.status) }}
                      </span>
                    </td>
                    <td>{{ arena.participants.length }}</td>
                    <td>{{ getChampionName(arena) }}</td>
                    <td>{{ formatDate(arena.completed_at) }}</td>
                    <td>
                      <button @click="viewArenaDetails(arena.id)" class="arena-btn details-btn small">
                        详情
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 创建竞技场弹窗 -->
      <div v-if="showCreateArena" class="modal">
        <div class="modal-content arena-modal">
          <div class="modal-header">
            <h2>创建竞技场</h2>
            <button @click="showCreateArena = false" class="close-btn">&times;</button>
          </div>
          
          <div class="modal-body">
            <form @submit.prevent="createArena" class="arena-form">
              <div class="form-group">
                <label for="arena-name" class="form-label">竞技场名称</label>
                <input 
                  type="text" 
                  id="arena-name" 
                  v-model="newArena.name" 
                  class="form-input" 
                  placeholder="输入竞技场名称" 
                  required
                >
              </div>
              
              <div class="form-group">
                <label for="arena-description" class="form-label">描述</label>
                <textarea 
                  id="arena-description" 
                  v-model="newArena.description" 
                  class="form-input" 
                  placeholder="描述此次竞技场的目的和内容"
                  rows="3"
                ></textarea>
              </div>
              
              <div class="form-group">
                <label for="arena-dataset" class="form-label">选择数据集</label>
                <select id="arena-dataset" v-model="newArena.dataset_id" class="form-input" required>
                  <option value="">-- 请选择数据集 --</option>
                  <option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
                    {{ dataset.name }}
                  </option>
                </select>
              </div>
              
              <div class="form-group">
                <label class="form-label">选择参与模型</label>
                <div class="model-selection">
                  <div 
                    v-for="model in availableModels" 
                    :key="model.id" 
                    class="model-option"
                    :class="{ selected: selectedModels.includes(model.id) }"
                    @click="toggleModelSelection(model.id)"
                  >
                    <div class="model-option-header">
                      <div class="model-checkbox">
                        <input 
                          type="checkbox" 
                          :id="`model-${model.id}`" 
                          :checked="selectedModels.includes(model.id)"
                        >
                        <label :for="`model-${model.id}`">{{ model.name }}</label>
                      </div>
                    </div>
                    <div class="model-option-body">
                      <div class="model-provider">提供商: {{ model.provider }}</div>
                      <div class="model-type">类型: {{ model.type }}</div>
                    </div>
                  </div>
                </div>
                <div class="form-error" v-if="formErrors.models">{{ formErrors.models }}</div>
              </div>
              
              <div class="form-actions">
                <button type="button" @click="showCreateArena = false" class="btn btn-secondary">取消</button>
                <button type="submit" class="btn" :disabled="isSubmitting">
                  {{ isSubmitting ? '创建中...' : '创建竞技场' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
      
      <!-- 竞技场详情弹窗 -->
      <div v-if="selectedArena" class="modal">
        <div class="modal-content arena-details-modal">
          <div class="modal-header">
            <h2>{{ selectedArena.name }} 详情</h2>
            <button @click="selectedArena = null" class="close-btn">&times;</button>
          </div>
          
          <div class="modal-body">
            <div class="arena-details-info">
              <div class="info-row">
                <div class="info-col">
                  <div class="info-item">
                    <strong>数据集:</strong> {{ selectedArena.dataset }}
                  </div>
                  <div class="info-item">
                    <strong>状态:</strong> 
                    <span class="status-badge" :class="selectedArena.status.toLowerCase()">
                      {{ getStatusText(selectedArena.status) }}
                    </span>
                  </div>
                  <div class="info-item">
                    <strong>创建时间:</strong> {{ formatDate(selectedArena.created_at) }}
                  </div>
                </div>
                <div class="info-col">
                  <div class="info-item">
                    <strong>参与模型:</strong> {{ selectedArena.participants.length }}个
                  </div>
                  <div class="info-item">
                    <strong>完成时间:</strong> 
                    {{ selectedArena.completed_at ? formatDate(selectedArena.completed_at) : '进行中' }}
                  </div>
                  <div class="info-item">
                    <strong>评估指标:</strong> {{ selectedArena.metric || '准确率' }}
                  </div>
                </div>
              </div>
              
              <div class="info-item description">
                <strong>描述:</strong> {{ selectedArena.description || '无描述' }}
              </div>
            </div>
            
            <h3 class="details-subtitle">参与模型排名</h3>
            
            <div class="ranking-table-container">
              <table class="ranking-table">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>模型</th>
                    <th>提供商</th>
                    <th>得分</th>
                    <th>详情</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(participant, index) in sortedParticipants" :key="participant.id">
                    <td>
                      <div class="rank" :class="{ 'rank-first': index === 0, 'rank-second': index === 1, 'rank-third': index === 2 }">
                        {{ index + 1 }}
                      </div>
                    </td>
                    <td>{{ participant.name }}</td>
                    <td>{{ participant.provider }}</td>
                    <td>{{ formatScore(participant.score) }}</td>
                    <td>
                      <button class="arena-btn small" @click="viewParticipantDetails(participant)">
                        查看
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <h3 class="details-subtitle">评测结果对比</h3>
            
            <div class="comparison-chart">
              <!-- 这里可以集成图表库展示比较结果 -->
              <div class="chart-placeholder">
                <div class="radar-chart">
                  <!-- 雷达图占位 -->
                  <div class="radar-message">雷达图区域，展示模型在各维度的表现对比</div>
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
  name: 'ArenaView',
  components: {
    MainLayout
  },
  data() {
    return {
      showCreateArena: false,
      selectedArena: null,
      isSubmitting: false,
      formErrors: {},
      selectedModels: [],
      newArena: {
        name: '',
        description: '',
        dataset_id: ''
      },
      // 模拟数据
      arenas: [
        {
          id: 1,
          name: 'MMLU Challenge Arena',
          description: '在MMLU数据集上进行多模型对抗评测，全面评估模型的多学科知识能力',
          dataset: 'MMLU',
          status: 'COMPLETED',
          progress: 100,
          created_at: '2023-10-05',
          completed_at: '2023-10-06',
          metric: '准确率',
          participants: [
            { id: 1, name: 'GPT-4', provider: 'OpenAI', score: 0.89 },
            { id: 2, name: 'Claude 2', provider: 'Anthropic', score: 0.86 },
            { id: 3, name: 'Llama 2-70B', provider: 'Meta', score: 0.81 },
            { id: 4, name: 'ChatGLM-6B', provider: 'THUDM', score: 0.73 }
          ]
        },
        {
          id: 2,
          name: '中文能力评测Arena',
          description: '专注评测各模型在中文语言理解和生成能力方面的表现',
          dataset: 'CMMLU',
          status: 'RUNNING',
          progress: 65,
          created_at: '2023-10-15',
          completed_at: null,
          metric: '准确率',
          participants: [
            { id: 1, name: 'GPT-4', provider: 'OpenAI', score: null },
            { id: 5, name: 'Baichuan2-13B', provider: 'Baichuan', score: null },
            { id: 6, name: 'ChatGLM2-6B', provider: 'THUDM', score: null }
          ]
        },
        {
          id: 3,
          name: '代码能力评测',
          description: '评测各大模型在代码生成和理解方面的能力',
          dataset: 'HumanEval',
          status: 'COMPLETED',
          progress: 100,
          created_at: '2023-09-20',
          completed_at: '2023-09-21',
          metric: '通过率',
          participants: [
            { id: 1, name: 'GPT-4', provider: 'OpenAI', score: 0.92 },
            { id: 7, name: 'Claude 2', provider: 'Anthropic', score: 0.88 },
            { id: 8, name: 'CodeLlama-34B', provider: 'Meta', score: 0.86 }
          ]
        }
      ],
      datasets: [
        { id: 1, name: 'MMLU (多学科知识评测)' },
        { id: 2, name: 'CMMLU (中文多学科知识评测)' },
        { id: 3, name: 'HumanEval (代码生成评测)' },
        { id: 4, name: 'HellaSwag (常识推理)' },
        { id: 5, name: 'GSM8K (数学推理)' }
      ],
      availableModels: [
        { id: 1, name: 'GPT-4', provider: 'OpenAI', type: '对话型' },
        { id: 2, name: 'Claude 2', provider: 'Anthropic', type: '对话型' },
        { id: 3, name: 'Llama 2-70B', provider: 'Meta', type: '基础模型' },
        { id: 4, name: 'ChatGLM-6B', provider: 'THUDM', type: '对话型' },
        { id: 5, name: 'Baichuan2-13B', provider: 'Baichuan', type: '基础模型' },
        { id: 6, name: 'ChatGLM2-6B', provider: 'THUDM', type: '对话型' },
        { id: 7, name: 'Falcon-40B', provider: 'TII', type: '基础模型' },
        { id: 8, name: 'CodeLlama-34B', provider: 'Meta', type: '代码模型' }
      ]
    }
  },
  computed: {
    activeArenas() {
      return this.arenas.filter(arena => 
        arena.status === 'PENDING' || arena.status === 'RUNNING'
      )
    },
    completedArenas() {
      return this.arenas.filter(arena => 
        arena.status === 'COMPLETED' || arena.status === 'FAILED'
      )
    },
    sortedParticipants() {
      if (!this.selectedArena) return []
      
      return [...this.selectedArena.participants].sort((a, b) => {
        // 未完成的竞技场，可能有null分数
        if (a.score === null && b.score === null) return 0
        if (a.score === null) return 1
        if (b.score === null) return -1
        return b.score - a.score
      })
    }
  },
  methods: {
    getStatusText(status) {
      const statusMap = {
        'PENDING': '等待中',
        'RUNNING': '进行中',
        'COMPLETED': '已完成',
        'FAILED': '失败'
      }
      return statusMap[status] || status
    },
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString('zh-CN')
    },
    formatScore(score) {
      if (score === null || score === undefined) return '-'
      return (score * 100).toFixed(2) + '%'
    },
    getChampionName(arena) {
      if (arena.status !== 'COMPLETED' || !arena.participants || arena.participants.length === 0) {
        return '-'
      }
      
      // 找到得分最高的参与者
      const champion = [...arena.participants].sort((a, b) => b.score - a.score)[0]
      return champion ? champion.name : '-'
    },
    viewArenaDetails(arenaId) {
      this.selectedArena = this.arenas.find(arena => arena.id === arenaId)
    },
    viewParticipantDetails(participant) {
      // 查看参与者详情的逻辑
      console.log('查看参与者详情:', participant)
    },
    terminateArena(arenaId) {
      if (confirm('确定要终止这个竞技场吗？')) {
        // 终止竞技场的逻辑
        console.log('终止竞技场:', arenaId)
      }
    },
    toggleModelSelection(modelId) {
      const index = this.selectedModels.indexOf(modelId)
      if (index === -1) {
        this.selectedModels.push(modelId)
      } else {
        this.selectedModels.splice(index, 1)
      }
    },
    createArena() {
      this.formErrors = {}
      
      // 表单验证
      if (this.selectedModels.length < 2) {
        this.formErrors.models = '请至少选择两个模型进行对比'
        return
      }
      
      this.isSubmitting = true
      
      // 模拟API调用
      setTimeout(() => {
        console.log('创建竞技场:', {
          ...this.newArena,
          selectedModels: this.selectedModels
        })
        
        // 重置表单
        this.newArena = {
          name: '',
          description: '',
          dataset_id: ''
        }
        this.selectedModels = []
        this.showCreateArena = false
        this.isSubmitting = false
        
        // 提示创建成功
        alert('竞技场创建成功！')
      }, 1000)
    }
  }
}
</script>

<style scoped>
.arena-page {
  padding: 0 0 40px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.arena-content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.arena-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.arena-description {
  max-width: 700px;
  margin: 0;
  color: #4a5568;
  line-height: 1.6;
}

.arena-section {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.section-title {
  font-size: 20px;
  margin-top: 0;
  margin-bottom: 24px;
  color: #2d3748;
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: #718096;
}

.arena-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.arena-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.3s;
}

.arena-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.arena-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
}

.arena-name {
  margin: 0;
  font-size: 18px;
  color: #2d3748;
}

.arena-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.arena-status.running {
  background-color: #ebf8ff;
  color: #3182ce;
}

.arena-status.pending {
  background-color: #fefcbf;
  color: #d69e2e;
}

.arena-status.completed {
  background-color: #e6fffa;
  color: #38b2ac;
}

.arena-status.failed {
  background-color: #fed7d7;
  color: #e53e3e;
}

.arena-info {
  padding: 16px;
}

.info-item {
  margin-bottom: 8px;
  color: #4a5568;
}

.info-item:last-child {
  margin-bottom: 0;
}

.arena-progress {
  padding: 0 16px 16px;
}

.progress-bar {
  height: 8px;
  background-color: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.progress-fill {
  height: 100%;
  background-color: #3182ce;
  border-radius: 4px;
}

.progress-text {
  text-align: right;
  font-size: 12px;
  color: #718096;
}

.arena-actions {
  display: flex;
  padding: 16px;
  border-top: 1px solid #e2e8f0;
  gap: 8px;
}

.arena-btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: background-color 0.3s;
}

.arena-btn.small {
  padding: 4px 8px;
  font-size: 12px;
}

.details-btn {
  background-color: #3182ce;
  color: white;
}

.details-btn:hover {
  background-color: #2c5282;
}

.terminate-btn {
  background-color: #e53e3e;
  color: white;
}

.terminate-btn:hover {
  background-color: #c53030;
}

.arena-table-container {
  overflow-x: auto;
}

.arena-table {
  width: 100%;
  border-collapse: collapse;
}

.arena-table th,
.arena-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.arena-table th {
  background-color: #f7fafc;
  font-weight: 600;
  color: #4a5568;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.running {
  background-color: #ebf8ff;
  color: #3182ce;
}

.status-badge.pending {
  background-color: #fefcbf;
  color: #d69e2e;
}

.status-badge.completed {
  background-color: #e6fffa;
  color: #38b2ac;
}

.status-badge.failed {
  background-color: #fed7d7;
  color: #e53e3e;
}

/* 创建竞技场弹窗样式 */
.arena-modal {
  max-width: 800px;
}

.arena-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-selection {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.model-option {
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 12px;
  cursor: pointer;
  transition: background-color 0.3s, border-color 0.3s;
}

.model-option:hover {
  background-color: #f7fafc;
}

.model-option.selected {
  border-color: #3182ce;
  background-color: #ebf8ff;
}

.model-option-header {
  margin-bottom: 8px;
}

.model-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-option-body {
  font-size: 12px;
  color: #718096;
}

.model-provider,
.model-type {
  margin-top: 4px;
}

.form-error {
  color: #e53e3e;
  font-size: 14px;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 16px;
}

/* 竞技场详情弹窗样式 */
.arena-details-modal {
  max-width: 900px;
}

.arena-details-info {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.info-row {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}

.info-col {
  flex: 1;
}

.description {
  margin-top: 16px;
}

.details-subtitle {
  font-size: 18px;
  margin: 24px 0 16px;
  color: #2d3748;
}

.ranking-table-container {
  overflow-x: auto;
  margin-bottom: 24px;
}

.ranking-table {
  width: 100%;
  border-collapse: collapse;
}

.ranking-table th,
.ranking-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.ranking-table th {
  background-color: #f7fafc;
  font-weight: 600;
  color: #4a5568;
}

.rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #e2e8f0;
  font-weight: 600;
}

.rank-first {
  background-color: #fbd38d;
  color: #975a16;
}

.rank-second {
  background-color: #cbd5e0;
  color: #2d3748;
}

.rank-third {
  background-color: #feb2b2;
  color: #9b2c2c;
}

.comparison-chart {
  height: 300px;
  position: relative;
}

.chart-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radar-chart {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f7fafc;
  border-radius: 8px;
}

.radar-message {
  color: #718096;
  text-align: center;
}

@media (max-width: 768px) {
  .arena-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .info-row {
    flex-direction: column;
    gap: 8px;
  }
  
  .arena-actions {
    flex-direction: column;
  }
  
  .model-selection {
    grid-template-columns: 1fr;
  }
}
</style> 