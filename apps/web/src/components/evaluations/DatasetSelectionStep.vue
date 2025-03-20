<template>
  <div class="dataset-selection">
    <h3>选择评测数据集</h3>
    
    <div class="dataset-selection-container">
      <!-- 使用Element Plus的Cascader组件替代Multiselect -->
      <el-cascader
        v-model="selectedDatasets"
        :options="formatDatasetOptions"
        :props="cascaderProps"
        placeholder="选择或搜索数据集"
        clearable
        filterable
        multiple
        collapse-tags
        collapse-tags-tooltip
        class="dataset-cascader"
        @change="handleDatasetChange"
      />
      
      <!-- 所选数据集展示 -->
      <div class="selected-datasets-container" v-if="selectedDatasets.length > 0">
        <h4>已选择的数据集 ({{ selectedDatasets.length }})</h4>
        <div class="selected-datasets-list">
          <el-tag
            v-for="dataset in selectedDatasetsInfo"
            :key="dataset.id"
            closable
            class="dataset-tag"
            @close="removeDataset(dataset)"
            @mouseenter="startHoverTimer(dataset)"
            @mouseleave="clearHoverTimer"
          >
            {{ dataset.name }}
            <div class="tooltip" v-if="hoveredOption && hoveredOption.id === dataset.id">
              <div class="tooltip-content">
                <div class="tooltip-title">{{ dataset.name }}</div>
                <div class="tooltip-description">{{ dataset.description || '暂无描述' }}</div>
                <div class="tooltip-meta" v-if="dataset.itemCount">
                  <span class="tooltip-count">包含 {{ dataset.itemCount }} 条数据</span>
                </div>
              </div>
              <div class="tooltip-arrow"></div>
            </div>
          </el-tag>
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
// 替换Multiselect导入为Element Plus组件
import { ElCascader, ElTag } from 'element-plus'
import 'element-plus/dist/index.css'

export default {
  name: 'DatasetSelectionStep',
  components: {
    ElCascader,
    ElTag
  },
  props: {
    initialSelectedDatasets: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      selectedDatasets: [],
      datasetOptions: [],
      hoveredOption: null,
      hoverTimer: null,
      // 配置Cascader组件属性
      cascaderProps: {
        multiple: true,
        value: 'id',
        label: 'name',
        children: 'datasets',
        emitPath: false
      },
      // 默认数据集保持不变
      defaultDatasets: [
        { 
          id: 'demo_cmmlu_chat_gen', 
          name: 'CMMLU', 
          description: '中文通用语言理解测试数据集，覆盖多个学科和领域',
          category: 'Demo演示',
          itemCount: 42 
        },
        { 
          id: 'demo_math_chat_gen', 
          name: 'Math', 
          description: '数学问题测试集，包含基础算术、代数和几何问题',
          category: 'Demo演示',
          itemCount: 64 
        }
      ]
    }
  },
  computed: {
    // 将数据集格式化为Cascader需要的格式
    formatDatasetOptions() {
      console.log('格式化Cascader选项:', this.datasetOptions);
      const grouped = {};
      
      // 如果没有数据，返回空数组
      if (!this.datasetOptions || this.datasetOptions.length === 0) {
        return [];
      }
      
      // 根据category分组
      this.datasetOptions.forEach(dataset => {
        const category = dataset.category || '未分类';
        if (!grouped[category]) {
          grouped[category] = {
            id: `category_${category}`,
            name: category,
            datasets: []
          };
        }
        grouped[category].datasets.push(dataset);
      });
      
      // 转换为数组格式
      const result = Object.values(grouped);
      console.log('Cascader格式的数据:', result);
      return result;
    },
    
    // 获取已选数据集的详细信息
    selectedDatasetsInfo() {
      return this.selectedDatasets.map(id => {
        // 在所有数据集中查找匹配的ID
        const allDatasets = this.datasetOptions.flat();
        return allDatasets.find(d => d.id === id) || { id, name: id, description: '未知数据集' };
      });
    }
  },
  created() {
    // 初始化数据集为默认数据集
    this.datasetOptions = [...this.defaultDatasets];
    // 处理初始选中的数据集
    if (this.initialSelectedDatasets && this.initialSelectedDatasets.length > 0) {
      this.selectedDatasets = this.initialSelectedDatasets.map(d => d.id);
    }
  },
  mounted() {
    // 尝试从服务器获取数据集
    this.fetchDatasets();
  },
  beforeDestroy() {
    this.clearHoverTimer();
  },
  methods: {
    // 处理数据集选择变化
    handleDatasetChange(value) {
      console.log('选中的数据集变更:', value);
    },
    
    // 开始悬停计时器
    startHoverTimer(option) {
      this.clearHoverTimer();
      this.hoverTimer = setTimeout(() => {
        this.hoveredOption = option;
      }, 300); // 300毫秒后显示提示
    },
    
    // 清除悬停计时器
    clearHoverTimer() {
      if (this.hoverTimer) {
        clearTimeout(this.hoverTimer);
        this.hoverTimer = null;
      }
      this.hoveredOption = null;
    },
    
    // 移除已选数据集
    removeDataset(dataset) {
      this.selectedDatasets = this.selectedDatasets.filter(id => id !== dataset.id);
    },
    
    async fetchDatasets() {
      try {
        console.log('正在尝试获取数据集列表...');
        const token = localStorage.getItem('token');
        
        // 如果没有令牌，则使用默认数据集
        if (!token) {
          console.log('未找到登录令牌，使用默认数据集');
          return;
        }
        
        const response = await fetch('/api/v1/datasets', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('成功获取数据集列表:', data);
          
          if (Array.isArray(data) && data.length > 0) {
            // 将获取到的数据集格式化
            const formattedDatasets = data.map(dataset => ({
              id: dataset.id || dataset.name,
              name: dataset.name,
              description: dataset.description || '',
              category: dataset.category || '未分类',
              itemCount: dataset.item_count || 0
            }));
            
            // 直接赋值
            this.datasetOptions = formattedDatasets;
            console.log('处理后的数据集列表:', this.datasetOptions);
          } else {
            console.log('服务器返回的数据集为空，使用默认数据集');
            // 确保使用默认数据集
            this.datasetOptions = [...this.defaultDatasets];
          }
        } else {
          console.error('获取数据集列表失败，状态码:', response.status);
          // 如果API请求失败，确保使用默认数据集
          this.datasetOptions = [...this.defaultDatasets];
        }
      } catch (error) {
        console.error('获取数据集列表出错:', error);
        // 如果发生异常，确保使用默认数据集
        this.datasetOptions = [...this.defaultDatasets];
      }
    },
    
    goToPrevStep() {
      this.$emit('prev-step');
    },
    
    goToNextStep() {
      // 获取选中数据集的完整信息
      const selectedDatasetInfo = this.selectedDatasets.map(id => {
        // 在所有数据集中查找匹配的ID
        for (const dataset of this.datasetOptions) {
          if (dataset.id === id) {
            return dataset;
          }
        }
        return { id, name: id }; // 默认信息
      });
      
      this.$emit('next-step', {
        selectedDatasets: selectedDatasetInfo
      });
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

.dataset-selection-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Cascader样式 */
.dataset-cascader {
  width: 100%;
}

/* 已选数据集展示区域 */
.selected-datasets-container {
  margin-top: 15px;
}

.selected-datasets-container h4 {
  font-size: 14px;
  color: #4a5568;
  margin-bottom: 10px;
  font-weight: 500;
}

.selected-datasets-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dataset-tag {
  position: relative;
  margin: 4px;
}

/* 悬停提示样式 */
.tooltip {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translate(-50%, -100%);
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 200px;
  max-width: 300px;
  animation: fadeIn 0.2s;
  padding: 0;
  pointer-events: none;
}

.tooltip-content {
  padding: 12px;
}

.tooltip-title {
  font-weight: 600;
  font-size: 14px;
  color: #2d3748;
  margin-bottom: 6px;
}

.tooltip-description {
  font-size: 12px;
  color: #4a5568;
  margin-bottom: 8px;
  line-height: 1.5;
}

.tooltip-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #718096;
}

.tooltip-arrow {
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid white;
}

/* 按钮样式 */
.step-buttons {
  margin-top: 30px;
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
  font-size: 14px;
}

.btn-prev:hover {
  background-color: #e2e8f0;
}

.btn-next {
  padding: 10px 25px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #3182ce;
  color: white;
  border: none;
  font-size: 14px;
}

.btn-next:hover:not(:disabled) {
  background-color: #2c5282;
}

.btn-next:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style> 