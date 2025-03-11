<template>
  <div class="task-form">
    <h2>创建评测任务</h2>
    
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label>模型选择</label>
        <select v-model="form.model" class="form-select">
          <option 
            v-for="model in modelOptions" 
            :value="model.value"
            :key="model.value"
          >
            {{ model.label }}
          </option>
        </select>
      </div>
      
      <div class="form-group">
        <label>评测数据集（多选）</label>
        <select 
          v-model="selectedDatasets" 
          multiple
          class="form-select multi-select"
          size="4"
        >
          <option 
            v-for="dataset in datasetOptions" 
            :value="dataset.value"
            :key="dataset.value"
          >
            {{ dataset.label }}
          </option>
        </select>
      </div>
      
      <div class="form-group">
        <label for="config_file">配置文件</label>
        <input 
          type="text" 
          id="config_file" 
          v-model="form.config_file" 
          placeholder="输入配置文件路径" 
        />
        <div class="helper-text">例如: configs/eval_llama2.py</div>
      </div>
      
      <div class="form-group">
        <label for="num_gpus">GPU数量</label>
        <input 
          type="number" 
          id="num_gpus" 
          v-model.number="form.num_gpus" 
          min="0" 
          max="8" 
          placeholder="输入所需GPU数量" 
          required
        />
      </div>
      
      <div class="form-group">
        <label for="extra_args">额外参数</label>
        <textarea 
          id="extra_args" 
          v-model="form.extra_args" 
          placeholder="输入额外命令行参数" 
          rows="3"
        ></textarea>
        <div class="helper-text">例如: --max-samples 10 --debug</div>
      </div>
      
      <div class="form-actions">
        <button type="button" @click="$emit('cancel')" class="cancel-btn">取消</button>
        <button type="submit" class="submit-btn" :disabled="isSubmitting">
          {{ isSubmitting ? '提交中...' : '创建任务' }}
        </button>
      </div>
    </form>
    
    <div v-if="taskCreated" class="success-message">
      <h3>✓ 任务已成功提交!</h3>
      <p>任务ID: <strong>{{ createdTaskId }}</strong></p>
      <p>任务将在后台异步执行，您可以在任务列表中查看其状态</p>
    </div>
    
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TaskForm',
  data() {
    return {
      form: {
        model: 'hk33smarter_api',
        config_file: '',
        num_gpus: 1,
        extra_args: '',
        modelPath: '/models/llama2-7b',
        modelType: 'huggingface',
        batchSize: 4,
        workers: 2,
        debugMode: false,
        datasetSplit: 'validation',
        sampleSize: 100
      },
      isSubmitting: false,
      error: null,
      taskCreated: false,
      createdTaskId: null,
      selectedDatasets: [],
      modelOptions: [
        { value: 'hk33smarter_api', label: 'hk33smarter_api' },
        { value: 'qwen-14b', label: 'Qwen-14B' }
      ],
      datasetOptions: [
        { value: 'demo_math_chat_gen', label: 'Math 演示数据集' },
        { value: 'demo_gsm8k_chat_gen', label: 'gsm8k 演示数据集' }
      ]
    }
  },
  methods: {
    async submitForm() {
      this.isSubmitting = true;
      this.error = null;
      this.taskCreated = false;
      
      try {
        const requestBody = {
          model_name: this.form.model,
          dataset_name: this.selectedDatasets,
          model_configuration: {
            model_path: this.form.modelPath,
            model_type: this.form.modelType,
            parameters: this.form.modelParams
          },
          dataset_configuration: {
            datasets: this.selectedDatasets,
            split: this.form.datasetSplit,
            sample_size: this.form.sampleSize
          },
          eval_config: {
            workers: this.form.workers,
            batch_size: this.form.batchSize,
            debug_mode: this.form.debugMode
          }
        };
        
        if (this.form.config_file) {
          requestBody.config_file = this.form.config_file;
        }
        
        if (this.form.num_gpus > 0) {
          requestBody.num_gpus = this.form.num_gpus;
        }
        
        if (this.form.extra_args) {
          requestBody.extra_args = this.form.extra_args;
        }
        
        const response = await fetch('/api/v1/evaluations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `创建任务失败: ${response.status} ${response.statusText}`);
        }
        
        const task = await response.json();
        
        // 显示成功消息
        this.taskCreated = true;
        this.createdTaskId = task.id;
        
        // 短暂延迟后重置表单
        setTimeout(() => {
          // 发出事件通知父组件任务已创建
          this.$emit('task-created', task);
          // 重置表单
          this.resetForm();
        }, 2000);
      } catch (err) {
        console.error('创建任务错误:', err);
        this.error = err.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    
    resetForm() {
      this.form = {
        model: 'hk33smarter_api',
        config_file: '',
        num_gpus: 1,
        extra_args: '',
        modelPath: '/models/llama2-7b',
        modelType: 'huggingface',
        batchSize: 4,
        workers: 2,
        debugMode: false,
        datasetSplit: 'validation',
        sampleSize: 100
      };
      this.selectedDatasets = [];
    }
  }
}
</script>

<style scoped>
.task-form {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  margin: 0 auto;
}

h2 {
  margin-top: 0;
  margin-bottom: 24px;
  color: #333;
  font-size: 22px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

input, textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

input:focus, textarea:focus {
  outline: none;
  border-color: #2196f3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.helper-text {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

button {
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: background-color 0.2s;
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.cancel-btn {
  background-color: #e0e0e0;
  color: #333;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #d0d0d0;
}

.submit-btn {
  background-color: #2196f3;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #1976d2;
}

.success-message {
  margin-top: 20px;
  padding: 16px;
  background-color: #e8f5e9;
  border-left: 4px solid #4caf50;
  border-radius: 4px;
}

.success-message h3 {
  margin-top: 0;
  color: #2e7d32;
}

.error-message {
  margin-top: 20px;
  padding: 16px;
  background-color: #ffebee;
  border-left: 4px solid #f44336;
  border-radius: 4px;
  color: #d32f2f;
}

.form-select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.multi-select {
  height: 120px;
  padding: 8px;
}

.config-section {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-top: 10px;
}
</style> 