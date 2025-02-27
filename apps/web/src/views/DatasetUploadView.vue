<template>
  <MainLayout>
    <div class="datasets-page">
      <div class="container">
        <h1 class="page-title">上传数据集</h1>
        
        <div class="evaluation-container">
          <div class="evaluation-content">
            <!-- 左侧边栏 -->
            <div class="sidebar">
              <div class="sidebar-section">
                <h2 class="sidebar-title">我的评测</h2>
                <ul class="sidebar-list">
                  <li class="sidebar-item">
                    <router-link to="/evaluation" exact class="sidebar-link">创建评测</router-link>
                  </li>
                  <li class="sidebar-item">
                    <router-link to="/evaluation/records" class="sidebar-link">评测记录</router-link>
                  </li>
                </ul>
              </div>
              
              <div class="sidebar-section">
                <h2 class="sidebar-title">我的数据集</h2>
                <ul class="sidebar-list">
                  <li class="sidebar-item">
                    <router-link to="/evaluation/datasets" class="sidebar-link">所有数据集</router-link>
                  </li>
                  <li class="sidebar-item">
                    <router-link to="/evaluation/datasets/upload" class="sidebar-link">上传数据集</router-link>
                  </li>
                </ul>
              </div>
            </div>
            
            <!-- 右侧主内容 -->
            <div class="main-content">
              <div class="content-header">
                <h2 class="content-title">上传新数据集</h2>
              </div>
              
              <!-- 上传表单 -->
              <div class="upload-form">
                <div class="form-group">
                  <label for="datasetName">数据集名称</label>
                  <input type="text" id="datasetName" v-model="datasetName" class="form-input" placeholder="请输入数据集名称">
                </div>
                
                <div class="form-group">
                  <label for="datasetDesc">数据集描述</label>
                  <textarea id="datasetDesc" v-model="datasetDesc" class="form-input" rows="4" placeholder="请输入数据集描述"></textarea>
                </div>
                
                <div class="form-group">
                  <label for="datasetCategory">分类</label>
                  <select id="datasetCategory" v-model="datasetCategory" class="form-input">
                    <option value="">请选择分类</option>
                    <option value="通用能力">通用能力</option>
                    <option value="中文理解">中文理解</option>
                    <option value="代码能力">代码能力</option>
                    <option value="数学推理">数学推理</option>
                  </select>
                </div>
                
                <div class="form-group">
                  <label>上传文件</label>
                  <div class="file-upload-box">
                    <input type="file" id="fileUpload" ref="fileUpload" @change="handleFileChange" style="display: none">
                    <div class="upload-area" @click="triggerFileUpload">
                      <div v-if="!uploadedFile">
                        <i class="upload-icon">📁</i>
                        <p>点击或拖拽文件到此处上传</p>
                        <p class="upload-hint">支持 .json, .jsonl, .csv 格式</p>
                      </div>
                      <div v-else class="file-preview">
                        <span>{{ uploadedFile.name }}</span>
                        <button class="btn btn-sm" @click.stop="removeFile">移除</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="form-actions">
                  <button class="btn btn-secondary" @click="$router.push('/evaluation/datasets')">取消</button>
                  <button class="btn btn-primary" @click="uploadDataset" :disabled="!canUpload || uploading">
                    {{ uploading ? '上传中...' : '上传数据集' }}
                  </button>
                </div>
                
                <p class="info-text">
                  功能开发中，敬请期待...
                </p>
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
  name: 'DatasetUploadView',
  components: {
    MainLayout
  },
  data() {
    return {
      datasetName: '',
      datasetDesc: '',
      datasetCategory: '',
      uploadedFile: null,
      uploading: false
    }
  },
  computed: {
    canUpload() {
      return this.datasetName && this.datasetDesc && this.datasetCategory && this.uploadedFile;
    }
  },
  methods: {
    triggerFileUpload() {
      this.$refs.fileUpload.click();
    },
    handleFileChange(event) {
      const file = event.target.files[0];
      if (file) {
        this.uploadedFile = file;
      }
    },
    removeFile() {
      this.uploadedFile = null;
      this.$refs.fileUpload.value = '';
    },
    uploadDataset() {
      if (!this.canUpload) return;
      
      this.uploading = true;
      
      // 模拟上传过程
      setTimeout(() => {
        this.uploading = false;
        alert('上传功能正在开发中');
        // 成功后跳转到数据集列表页
        this.$router.push('/evaluation/datasets');
      }, 1500);
    }
  }
}
</script>

<style scoped>
.datasets-page {
  padding: 0 0 40px;
}

.page-title {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.evaluation-container {
  width: 100%;
  max-width: 1600px;
  margin: 60px auto 20px;
  padding: 0 20px;
  box-sizing: border-box;
}

.evaluation-content {
  display: flex;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  padding: 0;
  overflow: hidden;
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background-color: #f8fafc;
  padding: 24px 0;
  border-right: 1px solid #e2e8f0;
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  padding: 0 24px 16px;
  color: #4a5568;
}

.sidebar-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar-item {
  margin: 2px 0;
}

.sidebar-link {
  display: block;
  padding: 10px 24px;
  color: #4a5568;
  text-decoration: none;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.sidebar-link:hover,
.router-link-active {
  background-color: #edf2f7;
  color: #3182ce;
  border-left-color: #3182ce;
}

.main-content {
  flex: 1;
  padding: 30px;
  min-height: 600px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.content-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.upload-form {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 30px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #4a5568;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-input:focus {
  border-color: #3182ce;
  outline: none;
}

.file-upload-box {
  margin-top: 8px;
}

.upload-area {
  border: 2px dashed #cbd5e0;
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #3182ce;
  background-color: #ebf8ff;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: block;
}

.upload-hint {
  font-size: 14px;
  color: #718096;
  margin-top: 8px;
}

.file-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
}

.info-text {
  text-align: center;
  margin-top: 20px;
  color: #718096;
  font-style: italic;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.3s;
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

.btn-sm {
  padding: 4px 8px;
  font-size: 14px;
}

@media (max-width: 1600px) {
  .evaluation-container {
    max-width: 1400px;
  }
}

@media (max-width: 1400px) {
  .evaluation-container {
    max-width: 1200px;
  }
}

@media (max-width: 1200px) {
  .evaluation-container {
    max-width: 992px;
  }
}

@media (max-width: 992px) {
  .evaluation-container {
    max-width: 768px;
    padding: 0 15px;
  }
  
  .evaluation-content {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 20px;
  }
  
  .sidebar-link {
    padding: 10px 16px;
  }
  
  .main-content {
    padding: 20px;
  }
}
</style> 