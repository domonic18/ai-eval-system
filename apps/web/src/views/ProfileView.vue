<template>
  <MainLayout>
    <div class="profile-page">
      <div class="container">
        <div class="profile-header">
          <div class="user-info">
            <div class="avatar-container">
              <img :src="userAvatar" alt="用户头像" class="user-avatar" />
              <div class="avatar-overlay">
                <button class="change-avatar-btn" @click="openAvatarUploader">
                  <i class="fas fa-camera"></i>
                </button>
              </div>
            </div>
            <div class="user-details">
              <h1 class="username">{{ user?.username || '加载中...' }}</h1>
              <p class="email">{{ user?.email || '加载中...' }}</p>
              <p class="join-date" v-if="user?.created_at">
                注册时间: {{ formatDate(user.created_at) }}
              </p>
            </div>
          </div>
          <div class="actions">
            <button class="edit-profile-btn" @click="showEditForm = !showEditForm">
              {{ showEditForm ? '取消编辑' : '编辑资料' }}
            </button>
          </div>
        </div>
        
        <div class="profile-content">
          <div class="profile-tabs">
            <div 
              class="tab" 
              :class="{ active: activeTab === 'info' }" 
              @click="activeTab = 'info'"
            >
              个人资料
            </div>
            <div 
              class="tab" 
              :class="{ active: activeTab === 'evaluations' }" 
              @click="activeTab = 'evaluations'"
            >
              我的评测
            </div>
            <div 
              class="tab" 
              :class="{ active: activeTab === 'models' }" 
              @click="activeTab = 'models'"
            >
              我的模型
            </div>
            <div 
              class="tab" 
              :class="{ active: activeTab === 'datasets' }" 
              @click="activeTab = 'datasets'"
            >
              我的数据集
            </div>
          </div>
          
          <div class="tab-content">
            <!-- 个人资料面板 -->
            <div v-if="activeTab === 'info'" class="info-panel">
              <template v-if="!showEditForm">
                <div class="info-card">
                  <h3 class="card-title">基本信息</h3>
                  <div class="info-item">
                    <span class="info-label">用户名</span>
                    <span class="info-value">{{ user?.username || '-' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">邮箱</span>
                    <span class="info-value">{{ user?.email || '-' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">注册时间</span>
                    <span class="info-value">{{ user?.created_at ? formatDate(user.created_at) : '-' }}</span>
                  </div>
                </div>
                
                <div class="info-card">
                  <h3 class="card-title">个人简介</h3>
                  <p class="bio">{{ user?.bio || '暂无个人简介' }}</p>
                </div>
                
                <div class="info-card">
                  <h3 class="card-title">账号安全</h3>
                  <button class="change-password-btn" @click="showPasswordForm = true">
                    修改密码
                  </button>
                </div>
              </template>
              
              <!-- 编辑信息表单 -->
              <form v-else class="edit-form" @submit.prevent="updateProfile">
                <div class="form-card">
                  <h3 class="card-title">编辑个人资料</h3>
                  
                  <div class="form-group">
                    <label for="username" class="form-label">用户名</label>
                    <input 
                      type="text" 
                      id="username" 
                      v-model="formData.username" 
                      class="form-input" 
                      required
                    />
                  </div>
                  
                  <div class="form-group">
                    <label for="email" class="form-label">邮箱</label>
                    <input 
                      type="email" 
                      id="email" 
                      v-model="formData.email" 
                      class="form-input" 
                      required
                    />
                  </div>
                  
                  <div class="form-group">
                    <label for="bio" class="form-label">个人简介</label>
                    <textarea 
                      id="bio" 
                      v-model="formData.bio" 
                      class="form-textarea"
                      rows="4"
                    ></textarea>
                  </div>
                  
                  <div class="form-error" v-if="error">{{ error }}</div>
                  
                  <div class="form-actions">
                    <button type="submit" class="submit-btn" :disabled="loading">
                      {{ loading ? '保存中...' : '保存修改' }}
                    </button>
                    <button type="button" class="cancel-btn" @click="showEditForm = false">
                      取消
                    </button>
                  </div>
                </div>
              </form>
              
              <!-- 修改密码弹窗 -->
              <div v-if="showPasswordForm" class="password-modal">
                <div class="modal-backdrop" @click="showPasswordForm = false"></div>
                <div class="modal-content">
                  <div class="modal-header">
                    <h3 class="modal-title">修改密码</h3>
                    <button class="close-btn" @click="showPasswordForm = false">×</button>
                  </div>
                  
                  <form class="password-form" @submit.prevent="updatePassword">
                    <div class="form-group">
                      <label for="currentPassword" class="form-label">当前密码</label>
                      <input 
                        type="password" 
                        id="currentPassword" 
                        v-model="passwordData.currentPassword" 
                        class="form-input" 
                        required
                      />
                    </div>
                    
                    <div class="form-group">
                      <label for="newPassword" class="form-label">新密码</label>
                      <input 
                        type="password" 
                        id="newPassword" 
                        v-model="passwordData.newPassword" 
                        class="form-input" 
                        required
                        minlength="6"
                      />
                    </div>
                    
                    <div class="form-group">
                      <label for="confirmPassword" class="form-label">确认新密码</label>
                      <input 
                        type="password" 
                        id="confirmPassword" 
                        v-model="passwordData.confirmPassword" 
                        class="form-input" 
                        required
                      />
                    </div>
                    
                    <div class="form-error" v-if="passwordError">{{ passwordError }}</div>
                    
                    <div class="form-actions">
                      <button type="submit" class="submit-btn" :disabled="passwordLoading">
                        {{ passwordLoading ? '修改中...' : '修改密码' }}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
            
            <!-- 我的评测面板 -->
            <div v-else-if="activeTab === 'evaluations'" class="evaluations-panel">
              <div class="empty-state" v-if="!evaluations.length">
                <div class="empty-icon">📊</div>
                <h3 class="empty-title">暂无评测记录</h3>
                <p class="empty-desc">您还没有进行过任何模型评测</p>
                <router-link to="/evaluation" class="start-btn">开始评测</router-link>
              </div>
              
              <div v-else class="evaluation-list">
                <div v-for="(evaluation, index) in evaluations" :key="index" class="evaluation-card">
                  <div class="evaluation-header">
                    <h3 class="evaluation-title">{{ evaluation.title || '未命名评测' }}</h3>
                    <span class="evaluation-date">{{ formatDate(evaluation.created_at) }}</span>
                  </div>
                  
                  <div class="evaluation-info">
                    <div class="info-item">
                      <span class="info-label">模型</span>
                      <span class="info-value">{{ evaluation.model_name }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">数据集</span>
                      <span class="info-value">{{ evaluation.dataset_name }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">状态</span>
                      <span class="status-badge" :class="getStatusClass(evaluation.status)">
                        {{ getStatusText(evaluation.status) }}
                      </span>
                    </div>
                  </div>
                  
                  <div class="evaluation-footer">
                    <router-link :to="`/evaluation/${evaluation.id}`" class="details-btn">
                      查看详情
                    </router-link>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 我的模型面板 -->
            <div v-else-if="activeTab === 'models'" class="models-panel">
              <div class="empty-state" v-if="!models.length">
                <div class="empty-icon">🤖</div>
                <h3 class="empty-title">暂无模型</h3>
                <p class="empty-desc">您还没有添加任何模型</p>
                <router-link to="/models/add" class="start-btn">添加模型</router-link>
              </div>
              
              <div v-else class="model-list">
                <div v-for="(model, index) in models" :key="index" class="model-card">
                  <div class="model-header">
                    <h3 class="model-title">{{ model.name }}</h3>
                    <span class="model-type">{{ getModelTypeText(model.type) }}</span>
                  </div>
                  
                  <div class="model-body">
                    <p class="model-desc">{{ model.description || '暂无描述' }}</p>
                  </div>
                  
                  <div class="model-footer">
                    <router-link :to="`/models/${model.id}`" class="details-btn">
                      查看详情
                    </router-link>
                    <button class="delete-btn" @click="deleteModel(model.id)">删除</button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 我的数据集面板 -->
            <div v-else-if="activeTab === 'datasets'" class="datasets-panel">
              <div class="empty-state" v-if="!datasets.length">
                <div class="empty-icon">📁</div>
                <h3 class="empty-title">暂无数据集</h3>
                <p class="empty-desc">您还没有添加任何自定义数据集</p>
                <router-link to="/datasets/add" class="start-btn">添加数据集</router-link>
              </div>
              
              <div v-else class="dataset-list">
                <div v-for="(dataset, index) in datasets" :key="index" class="dataset-card">
                  <div class="dataset-header">
                    <h3 class="dataset-title">{{ dataset.name }}</h3>
                    <span class="dataset-size">{{ dataset.items_count }} 条数据</span>
                  </div>
                  
                  <div class="dataset-body">
                    <p class="dataset-desc">{{ dataset.description || '暂无描述' }}</p>
                  </div>
                  
                  <div class="dataset-footer">
                    <router-link :to="`/datasets/${dataset.id}`" class="details-btn">
                      查看详情
                    </router-link>
                    <button class="delete-btn" @click="deleteDataset(dataset.id)">删除</button>
                  </div>
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
import { defineComponent, ref, reactive, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import MainLayout from '@/layouts/MainLayout.vue'

export default defineComponent({
  name: 'ProfileView',
  components: {
    MainLayout
  },
  
  setup() {
    const store = useStore()
    
    // 状态数据
    const activeTab = ref('info')
    const showEditForm = ref(false)
    const showPasswordForm = ref(false)
    const loading = ref(false)
    const error = ref(null)
    const passwordLoading = ref(false)
    const passwordError = ref(null)
    
    // 表单数据
    const formData = reactive({
      username: '',
      email: '',
      bio: ''
    })
    
    const passwordData = reactive({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
    
    // 模拟数据 - 实际应用中应该从API获取
    const evaluations = ref([])
    const models = ref([])
    const datasets = ref([])
    
    // 计算属性
    const user = computed(() => store.state.auth.user)
    
    const userAvatar = computed(() => {
      return user.value?.image || '/assets/images/default-avatar.png'
    })
    
    // 生命周期钩子
    onMounted(() => {
      // 获取用户信息
      store.dispatch('auth/getCurrentUser')
      
      // 加载初始数据
      loadUserData()
    })
    
    // 方法
    const loadUserData = () => {
      // 模拟加载用户数据 - 实际应用中应该从API获取
      if (user.value) {
        formData.username = user.value.username || ''
        formData.email = user.value.email || ''
        formData.bio = user.value.bio || ''
      }
      
      // 模拟加载评测、模型和数据集数据
      // 在实际应用中，这些应该通过API请求获取
      // 这里简单模拟一些数据
      setTimeout(() => {
        evaluations.value = [
          {
            id: 1,
            title: 'GPT-4性能评测',
            model_name: 'GPT-4',
            dataset_name: 'MMLU',
            status: 'completed',
            created_at: '2023-10-15T08:30:00Z'
          },
          {
            id: 2,
            title: 'Claude 3性能评测',
            model_name: 'Claude 3',
            dataset_name: 'GSM8K',
            status: 'running',
            created_at: '2023-10-20T14:15:00Z'
          }
        ]
        
        models.value = [
          {
            id: 1,
            name: 'GPT-4',
            type: 'api',
            description: 'OpenAI的GPT-4模型'
          },
          {
            id: 2,
            name: 'Claude 3',
            type: 'api',
            description: 'Anthropic的Claude 3模型'
          }
        ]
        
        datasets.value = [
          {
            id: 1,
            name: '中文能力测试集',
            items_count: 1200,
            description: '用于测试模型中文理解和生成能力的综合数据集'
          },
          {
            id: 2,
            name: '代码能力评测集',
            items_count: 500,
            description: '用于评估模型编程和算法能力的数据集'
          }
        ]
      }, 500)
    }
    
    const updateProfile = async () => {
      error.value = null
      loading.value = true
      
      try {
        // 在这里调用API更新用户资料
        await store.dispatch('auth/update', {
          username: formData.username,
          email: formData.email,
          bio: formData.bio
        })
        
        showEditForm.value = false
      } catch (err) {
        error.value = err.response?.data?.detail || '更新资料失败'
      } finally {
        loading.value = false
      }
    }
    
    const updatePassword = async () => {
      // 验证确认密码
      if (passwordData.newPassword !== passwordData.confirmPassword) {
        passwordError.value = '两次输入的密码不一致'
        return
      }
      
      passwordError.value = null
      passwordLoading.value = true
      
      try {
        // 这里调用API更新密码
        // await api.updatePassword({
        //   current_password: passwordData.currentPassword,
        //   new_password: passwordData.newPassword
        // })
        
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 800))
        
        // 成功后关闭弹窗并重置表单
        showPasswordForm.value = false
        passwordData.currentPassword = ''
        passwordData.newPassword = ''
        passwordData.confirmPassword = ''
        
        // 可以添加成功提示
      } catch (err) {
        passwordError.value = err.response?.data?.detail || '密码修改失败'
      } finally {
        passwordLoading.value = false
      }
    }
    
    const openAvatarUploader = () => {
      // 实现头像上传功能
      console.log('开启头像上传')
    }
    
    const deleteModel = (id) => {
      // 实现删除模型功能
      if (confirm('确定要删除这个模型吗？')) {
        models.value = models.value.filter(model => model.id !== id)
      }
    }
    
    const deleteDataset = (id) => {
      // 实现删除数据集功能
      if (confirm('确定要删除这个数据集吗？')) {
        datasets.value = datasets.value.filter(dataset => dataset.id !== id)
      }
    }
    
    const formatDate = (dateString) => {
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    }
    
    const getStatusClass = (status) => {
      switch (status) {
        case 'completed': return 'status-success'
        case 'running': return 'status-running'
        case 'failed': return 'status-error'
        default: return 'status-default'
      }
    }
    
    const getStatusText = (status) => {
      switch (status) {
        case 'completed': return '已完成'
        case 'running': return '进行中'
        case 'failed': return '失败'
        default: return '未知'
      }
    }
    
    const getModelTypeText = (type) => {
      switch (type) {
        case 'api': return 'API模型'
        case 'local': return '本地模型'
        case 'huggingface': return 'HuggingFace模型'
        default: return '未知类型'
      }
    }
    
    return {
      activeTab,
      user,
      userAvatar,
      evaluations,
      models,
      datasets,
      showEditForm,
      showPasswordForm,
      loading,
      error,
      formData,
      passwordData,
      passwordLoading,
      passwordError,
      
      updateProfile,
      updatePassword,
      openAvatarUploader,
      deleteModel,
      deleteDataset,
      formatDate,
      getStatusClass,
      getStatusText,
      getModelTypeText
    }
  }
})
</script>

<style scoped>
.profile-page {
  padding: 30px 0;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
  background-color: white;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.user-info {
  display: flex;
  align-items: center;
}

.avatar-container {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 24px;
}

.user-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  padding: 8px 0;
  opacity: 0;
  transition: opacity 0.3s;
}

.avatar-container:hover .avatar-overlay {
  opacity: 1;
}

.change-avatar-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 18px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #2d3748;
}

.email {
  font-size: 16px;
  color: #718096;
  margin: 0 0 8px;
}

.join-date {
  font-size: 14px;
  color: #a0aec0;
  margin: 0;
}

.edit-profile-btn {
  background-color: #3182ce;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.edit-profile-btn:hover {
  background-color: #2c5282;
}

.profile-content {
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.profile-tabs {
  display: flex;
  border-bottom: 1px solid #e2e8f0;
}

.tab {
  padding: 16px 24px;
  font-size: 16px;
  font-weight: 500;
  color: #718096;
  cursor: pointer;
  transition: color 0.3s, border-color 0.3s;
  border-bottom: 2px solid transparent;
}

.tab:hover {
  color: #3182ce;
}

.tab.active {
  color: #3182ce;
  border-bottom-color: #3182ce;
}

.tab-content {
  padding: 24px;
}

/* 个人资料面板样式 */
.info-card {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 16px;
  color: #2d3748;
}

.info-item {
  display: flex;
  margin-bottom: 12px;
}

.info-label {
  width: 80px;
  font-weight: 600;
  color: #4a5568;
}

.info-value {
  color: #2d3748;
  flex: 1;
}

.bio {
  color: #4a5568;
  line-height: 1.6;
  white-space: pre-line;
}

.change-password-btn {
  background-color: #ebf8ff;
  color: #3182ce;
  border: 1px solid #bee3f8;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.change-password-btn:hover {
  background-color: #bee3f8;
}

/* 表单样式 */
.form-card {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
  color: #4a5568;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-input:focus, .form-textarea:focus {
  border-color: #3182ce;
  outline: none;
}

.form-error {
  color: #e53e3e;
  margin-top: 16px;
  padding: 8px;
  background-color: #fff5f5;
  border-radius: 4px;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.submit-btn {
  background-color: #3182ce;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover {
  background-color: #2c5282;
}

.submit-btn:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
}

.cancel-btn {
  background-color: #e2e8f0;
  color: #4a5568;
  border: none;
  border-radius: 4px;
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.cancel-btn:hover {
  background-color: #cbd5e0;
}

/* 弹窗样式 */
.password-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
  position: relative;
  width: 400px;
  max-width: 90%;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 101;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #a0aec0;
  cursor: pointer;
  transition: color 0.3s;
}

.close-btn:hover {
  color: #4a5568;
}

.password-form {
  padding: 20px;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px;
  color: #2d3748;
}

.empty-desc {
  font-size: 16px;
  color: #718096;
  margin: 0 0 24px;
}

.start-btn {
  background-color: #3182ce;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  padding: 10px 20px;
  font-size: 16px;
  transition: background-color 0.3s;
}

.start-btn:hover {
  background-color: #2c5282;
}

/* 评测卡片样式 */
.evaluation-list, .model-list, .dataset-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.evaluation-card, .model-card, .dataset-card {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  transition: transform 0.3s, box-shadow 0.3s;
}

.evaluation-card:hover, .model-card:hover, .dataset-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.evaluation-header, .model-header, .dataset-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.evaluation-title, .model-title, .dataset-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.evaluation-date, .model-type, .dataset-size {
  font-size: 14px;
  color: #a0aec0;
}

.evaluation-info {
  margin-bottom: 16px;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-success {
  background-color: #c6f6d5;
  color: #2f855a;
}

.status-running {
  background-color: #bee3f8;
  color: #2b6cb0;
}

.status-error {
  background-color: #fed7d7;
  color: #c53030;
}

.status-default {
  background-color: #e2e8f0;
  color: #4a5568;
}

.evaluation-footer, .model-footer, .dataset-footer {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.details-btn {
  background-color: #ebf8ff;
  color: #3182ce;
  text-decoration: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 14px;
  transition: background-color 0.3s;
}

.details-btn:hover {
  background-color: #bee3f8;
}

.delete-btn {
  background-color: #fff5f5;
  color: #e53e3e;
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.delete-btn:hover {
  background-color: #fed7d7;
}

.model-body, .dataset-body {
  margin-bottom: 16px;
}

.model-desc, .dataset-desc {
  font-size: 14px;
  color: #718096;
  margin: 0;
  line-height: 1.6;
  min-height: 50px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
  }
  
  .user-info {
    margin-bottom: 20px;
  }
  
  .evaluation-list, .model-list, .dataset-list {
    grid-template-columns: 1fr;
  }
  
  .tab {
    padding: 12px 16px;
    font-size: 14px;
  }
}
</style> 