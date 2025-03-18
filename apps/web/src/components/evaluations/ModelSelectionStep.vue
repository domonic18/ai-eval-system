<template>
  <div class="model-selection">
    <h3>选择模型</h3>
    
    <!-- 模型类型选择 -->
    <div class="model-type-select">
      <label>
        <input 
          type="radio" 
          v-model="modelType" 
          value="preset"
        /> 预置模型
      </label>
      <label>
        <input 
          type="radio" 
          v-model="modelType" 
          value="custom" 
        /> 自定义API
      </label>
    </div>

    <!-- 多选模型下拉 -->
    <div class="form-group">
      <label v-if="modelType === 'preset'">选择预置模型</label>
      <label v-else>API配置</label>
      <Multiselect
        v-if="modelType === 'preset'"
        v-model="selectedModel"
        :options="modelOptions"
        mode="single"
        :searchable="true"
        placeholder="选择或搜索模型"
        :close-on-select="true"
      />
      <textarea
        v-else
        v-model="customApiConfig"
        class="api-config-input"
        placeholder="输入API配置"
        rows="4"
      ></textarea>
    </div>

    <!-- 步骤导航按钮 -->
    <div class="step-buttons">
      <button 
        type="button" 
        class="btn-next"
        @click="goToNextStep"
        :disabled="!canGoNext"
      >
        下一步
      </button>
    </div>
  </div>
</template>

<script>
import Multiselect from '@vueform/multiselect'
import '@vueform/multiselect/themes/default.css'

export default {
  name: 'ModelSelectionStep',
  components: {
    Multiselect
  },
  props: {
    initialModelType: {
      type: String,
      default: 'preset'
    },
    initialSelectedModel: {
      type: [String, Number, null],
      default: null
    },
    initialCustomApiConfig: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      modelType: this.initialModelType,
      selectedModel: this.initialSelectedModel,
      customApiConfig: this.initialCustomApiConfig,
      lastCustomApiConfig: null,
      modelOptions: [],
      defaultModels: [
        { value: 'hk33smarter_api', label: 'HK33 Smarter API' },
        { value: 'gpt-4', label: 'GPT-4' },
        { value: 'claude-3', label: 'Claude 3' }
      ]
    }
  },
  computed: {
    defaultApiConfig() {
      return `API_URL=https://guanghua-api.hk33smarter.com/v1
API_KEY=sk-xxxx
MODEL=Qwen/qwen2-1.5b-instruct`
    },
    canGoNext() {
      return this.modelType === 'preset' 
        ? this.selectedModel !== null
        : this.customApiConfig.trim() !== ''
    }
  },
  mounted() {
    this.fetchModels();
    this.loadApiConfigFromStorage();
  },
  methods: {
    loadApiConfigFromStorage() {
      try {
        const savedConfig = localStorage.getItem('evaluation_custom_api_config');
        if (savedConfig) {
          this.lastCustomApiConfig = savedConfig;
        }
        this.customApiConfig = this.lastCustomApiConfig || this.defaultApiConfig;
      } catch (error) {
        console.error('从本地存储加载配置失败:', error);
        this.customApiConfig = this.defaultApiConfig;
      }
    },
    
    saveApiConfigToStorage(config) {
      try {
        localStorage.setItem('evaluation_custom_api_config', config);
      } catch (error) {
        console.error('保存配置到本地存储失败:', error);
      }
    },
    
    async fetchModels() {
      try {
        const response = await fetch('/api/v1/models', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          this.modelOptions = data.map(model => ({
            value: model.id,
            label: model.name
          }));
        } else {
          this.modelOptions = [...this.defaultModels];
        }
      } catch (error) {
        console.error('获取模型列表失败:', error);
        this.modelOptions = [...this.defaultModels];
      }
    },
    
    goToNextStep() {
      // 向父组件发送当前选择的状态
      this.$emit('next-step', {
        modelType: this.modelType,
        selectedModel: this.selectedModel,
        customApiConfig: this.customApiConfig
      });
    }
  },
  watch: {
    modelType(newType) {
      if (newType === 'custom') {
        this.customApiConfig = this.lastCustomApiConfig || this.defaultApiConfig;
      }
    },
    customApiConfig(newConfig) {
      if (this.modelType === 'custom' && newConfig !== this.defaultApiConfig) {
        this.lastCustomApiConfig = newConfig;
        this.saveApiConfigToStorage(newConfig);
      }
    }
  }
}
</script>

<style scoped>
.model-selection h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2d3748;
}

.model-type-select {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.model-type-select label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.api-config-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
}

.step-buttons {
  margin-top: 25px;
  display: flex;
  gap: 15px;
  justify-content: flex-end;
}

.btn-next {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #3182ce;
  color: white;
  border: none;
}

.btn-next:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style> 