<template>
  <div class="dataset-selection">
    <h3>选择评测数据集</h3>
    <Multiselect
      v-model="selectedDatasets"
      :options="datasetOptions"
      mode="tags"
      :searchable="true"
      placeholder="选择或搜索数据集"
      :close-on-select="false"
      label="value"
      track-by="value"
      ref="datasetMultiselect"
      class="dataset-multiselect"
    >
      <template #option="{ option }">
        <div class="dataset-option">
          <div class="option-value">{{ option.value }}</div>
          <div class="option-label">{{ option.label }}</div>
        </div>
      </template>
      <template #tag="{ option, handleTagRemove }">
        <div class="multiselect-tag">
          <span class="tag-value">{{ option.value }}</span>
          <span class="tag-remove" @click="handleTagRemove(option)">×</span>
        </div>
      </template>
    </Multiselect>

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
        class="btn-next"
        @click="goToNextStep"
        :disabled="selectedDatasets.length === 0"
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
  name: 'DatasetSelectionStep',
  components: {
    Multiselect
  },
  props: {
    initialSelectedDatasets: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      selectedDatasets: [...this.initialSelectedDatasets],
      datasetOptions: [],
      defaultDatasets: [
        { value: 'demo_cmmlu_chat_gen', label: '中文通用语言理解测试' },
        { value: 'demo_math_chat_gen', label: '数学问题测试集' }
      ]
    }
  },
  mounted() {
    this.fetchDatasets();
    // 添加窗口调整事件监听
    window.addEventListener('resize', this.adjustDropdownHeight);
    // 初始调整高度
    this.$nextTick(() => {
      this.adjustDropdownHeight();
    });
  },
  beforeDestroy() {
    // 移除事件监听
    window.removeEventListener('resize', this.adjustDropdownHeight);
  },
  methods: {
    // 调整下拉列表高度
    adjustDropdownHeight() {
      if (this.$refs.datasetMultiselect) {
        const viewportHeight = window.innerHeight;
        // 计算合适的最大高度，保留上下边距和额外空间
        const maxHeight = viewportHeight - 320; // 保留顶部导航栏和底部按钮的空间
        // 设置CSS变量
        this.$refs.datasetMultiselect.$el.style.setProperty('--ms-max-height', `${maxHeight}px`);
      }
    },
    
    async fetchDatasets() {
      try {
        const response = await fetch('/api/v1/datasets', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          this.datasetOptions = data.map(dataset => ({
            value: dataset.name,
            label: dataset.description
          }));
        } else {
          this.datasetOptions = [...this.defaultDatasets];
        }
      } catch (error) {
        console.error('获取数据集列表失败:', error);
        this.datasetOptions = [...this.defaultDatasets];
      }
    },
    
    goToPrevStep() {
      this.$emit('prev-step');
    },
    
    goToNextStep() {
      this.$emit('next-step', {
        selectedDatasets: this.selectedDatasets
      });
    }
  },
  watch: {
    // 当切换到数据集选择步骤时调整下拉高度
    '$parent.currentStep'(newStep) {
      if (newStep === 2) {
        // 在DOM更新后调整高度
        this.$nextTick(() => {
          this.adjustDropdownHeight();
        });
      }
    }
  }
}
</script>

<style scoped>
.dataset-selection h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2d3748;
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

/* 数据集下拉列表样式优化 */
.dataset-multiselect {
  --ms-max-height: calc(100vh - 320px);
  --ms-option-padding: 8px 16px;
  --ms-py: 6px;
}

/* 修正数据集选项样式 */
.dataset-option {
  padding: 6px 0;
}

.dataset-option .option-value {
  font-weight: 500;
  color: #2d3748;
  font-size: 14px;
  line-height: 1.3;
}

.dataset-option .option-label {
  font-size: 12px;
  color: #718096;
  margin-top: 2px;
  line-height: 1.2;
}

/* 修正标签样式 */
.multiselect-tag {
  display: flex;
  align-items: center;
  background-color: #ebf8ff;
  color: #2b6cb0;
  padding: 2px 8px;
  border-radius: 4px;
  margin: 2px;
}

.multiselect-tag .tag-value {
  font-size: 14px;
}

.multiselect-tag .tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 6px;
  border-radius: 50%;
  background-color: #4299e1;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.multiselect-tag .tag-remove:hover {
  background-color: #3182ce;
}
</style> 