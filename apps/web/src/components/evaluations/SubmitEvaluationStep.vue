<template>
  <div class="config-section">
    <h3>评测确认</h3>
    <div class="evaluation-summary">
      <div class="summary-section">
        <h4>模型信息</h4>
        <div v-if="modelType === 'preset'" class="summary-item">
          <span class="item-label">选择的模型:</span>
          <span class="item-value">{{ selectedModelName }}</span>
        </div>
        <div v-else class="summary-item">
          <span class="item-label">API配置:</span>
          <pre class="api-config-display">{{ customApiConfig }}</pre>
        </div>
      </div>
      
      <div class="summary-section">
        <h4>数据集信息</h4>
        <div class="summary-list">
          <div v-for="(dataset, index) in formattedDatasets" :key="index" class="dataset-item">
            <span class="dataset-name">{{ dataset.value }}</span>
            <span v-if="dataset.label" class="dataset-description">{{ dataset.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 步骤导航按钮 -->
    <div class="step-buttons">
      <button 
        type="button" 
        class="btn-prev"
        @click="goToPrevStep"
      >
        上一步
      </button>
      <button 
        type="button" 
        class="btn-submit"
        @click="submitForm"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? '提交中...' : '开始评测' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SubmitEvaluationStep',
  props: {
    modelType: {
      type: String,
      required: true
    },
    selectedModel: {
      type: [String, Number, null],
      default: null
    },
    customApiConfig: {
      type: String,
      default: ''
    },
    selectedDatasets: {
      type: Array,
      required: true
    },
    modelOptions: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      isSubmitting: false
    }
  },
  computed: {
    selectedModelName() {
      if (!this.selectedModel) return '';
      const model = this.modelOptions.find(m => m.value === this.selectedModel);
      return model ? model.label : this.selectedModel;
    },
    formattedDatasets() {
      return this.selectedDatasets.map(dataset => {
        if (typeof dataset === 'object' && dataset.value) {
          return dataset;
        }
        return { value: dataset, label: '' };
      });
    }
  },
  methods: {
    goToPrevStep() {
      this.$emit('prev-step');
    },
    
    async submitForm() {
      this.isSubmitting = true;
      try {
        // 处理API配置转换
        const envVars = {}
        if (this.modelType === 'custom') {
          this.customApiConfig.split('\n').forEach(line => {
            const [key, value] = line.split('=')
            if (key && value) {
              envVars[key.trim()] = value.trim()
            }
          })
        }

        // 处理数据集选择的格式转换
        // 如果selectedDatasets是对象数组，提取value属性作为字符串数组
        const datasetNames = this.selectedDatasets.map(dataset => {
          return typeof dataset === 'object' && dataset.value ? dataset.value : dataset
        });
        
        // 获取选中模型的名称
        let modelName = 'custom_api'
        if (this.modelType === 'preset' && this.selectedModel) {
          // 根据选中的模型ID查找对应的模型名称
          const selectedModelOption = this.modelOptions.find(model => model.value === this.selectedModel)
          modelName = selectedModelOption ? selectedModelOption.label : this.selectedModel
        }

        // 构建请求体
        const requestBody = {
          model_name: modelName,
          dataset_names: datasetNames,
          env_vars: envVars,
          model_configuration: {
            model_type: this.modelType,
            ...(this.modelType === 'preset' && { preset_model: this.selectedModel })
          },
          dataset_configuration: {},
          eval_config: {
            // 可以添加其他评估配置参数
            timestamp: new Date().toISOString()
          }
        }

        // 发送创建评测请求
        const response = await fetch('/api/v1/evaluations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(requestBody)
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '创建评测任务失败')
        }

        const result = await response.json()
        
        // 提交成功后通知父组件
        this.$emit('submit-success', result);
      } catch (error) {
        console.error('提交评测任务失败:', error)
        this.$emit('submit-error', error.message || '请检查配置后重试');
      } finally {
        this.isSubmitting = false
      }
    }
  }
}
</script>

<style scoped>
.config-section h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2d3748;
}

.evaluation-summary {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.summary-section {
  margin-bottom: 20px;
}

.summary-section h4 {
  font-size: 16px;
  color: #4a5568;
  margin-bottom: 10px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e2e8f0;
}

.summary-item {
  display: flex;
  margin-bottom: 8px;
}

.item-label {
  font-weight: 500;
  min-width: 120px;
  color: #4a5568;
}

.api-config-display {
  background-color: #f7fafc;
  padding: 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  white-space: pre-wrap;
  margin-top: 10px;
  border: 1px solid #e2e8f0;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dataset-item {
  background-color: #f7fafc;
  padding: 8px 12px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.dataset-name {
  font-weight: 500;
  color: #2d3748;
}

.dataset-description {
  font-size: 13px;
  color: #718096;
  margin-top: 3px;
}

.step-buttons {
  margin-top: 25px;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.btn-prev {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
}

.btn-submit {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #38a169;
  color: white;
  border: none;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style> 