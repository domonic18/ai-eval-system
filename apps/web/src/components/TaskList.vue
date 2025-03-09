<template>
  <div class="task-list">
    <!-- 如果hideHeader为false或未定义，则显示标题和按钮 -->
    <div class="task-list-header" v-if="!hideHeader">
      <h3>评测任务列表</h3>
      <div class="task-list-actions">
        <button @click="fetchTasks" class="btn btn-secondary">刷新任务列表</button>
        <button @click="$emit('create-task')" class="btn btn-primary">创建新任务</button>
      </div>
    </div>
    
    <div v-if="loading" class="loading">
      <p>加载中...</p>
    </div>
    
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchTasks">重试</button>
    </div>
    
    <div v-else class="table-responsive">
      <table class="tasks-table">
        <colgroup>
          <col width="20%">
          <col width="20%">
          <col width="18%">
          <col width="12%">
          <col width="15%">
          <col width="15%">
        </colgroup>
        <thead>
          <tr>
            <th class="resizable">
              任务名称
            </th>
            <th class="resizable">评测模型</th>
            <th class="resizable">评测集</th>
            <th class="resizable">评测状态</th>
            <th class="resizable sort-header" @click="toggleSort">
              创建时间
              <span class="sort-icon">{{ sortDirection === 'desc' ? '↓' : '↑' }}</span>
            </th>
            <th class="resizable">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in sortedTasks" :key="task.id" :class="{ 'running': getTaskStatusType(task.status) === 'running' }">
            <td>
              <div class="task-name-container">
                <span v-if="!isEditing(task.id)">
                  {{ task.name || `评测任务-${task.id}` }}
                  <button class="edit-name-btn" @click="startEditing(task)">
                    <i class="fas fa-edit"></i>
                  </button>
                </span>
                <div v-else class="edit-name-form">
                  <input 
                    type="text" 
                    v-model="editingName" 
                    @keyup.enter="saveTaskName(task.id)"
                    @keyup.esc="cancelEditing"
                    class="edit-name-input"
                    ref="nameInput"
                  />
                  <div class="edit-actions">
                    <button class="save-btn" @click="saveTaskName(task.id)">保存</button>
                    <button class="cancel-btn" @click="cancelEditing">取消</button>
                  </div>
                </div>
              </div>
            </td>
            <td>{{ task.model_name }}</td>
            <td>{{ task.dataset_name }}</td>
            <td>
              <span :class="['status', getTaskStatusType(task.status)]">{{ formatStatus(task.status) }}</span>
            </td>
            <td class="date-cell">
              <div class="date-container">
                <div class="date-part">{{ formatDatePart(task.created_at) }}</div>
                <div class="time-part">{{ formatTimePart(task.created_at) }}</div>
              </div>
            </td>
            <td class="actions">
              <div class="action-buttons">
                <button class="action-btn log-btn" @click="viewLogs(task.id)">日志</button>
                
                <button v-if="getTaskStatusType(task.status) === 'running'" 
                      class="action-btn stop-btn" 
                      @click="terminateTask(task.id)">
                  停止
                </button>
                
                <button class="action-btn delete-btn" @click="deleteTask(task.id)">
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div v-if="tasks.length === 0 && !loading && !error" class="no-tasks">
      <p>暂无评测任务，请创建新任务。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TaskList',
  props: {
    hideHeader: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      tasks: [],
      loading: true,
      error: null,
      refreshInterval: null,
      activeTasks: new Set(), // 跟踪活动任务ID
      loadingTaskId: null,
      editingTaskId: null,
      editingName: '',
      sortDirection: 'desc' // 默认按创建时间降序排列（最新的在前）
    }
  },
  computed: {
    sortedTasks() {
      if (!this.tasks.length) return [];
      
      return [...this.tasks].sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        
        return this.sortDirection === 'desc' 
          ? dateB - dateA  // 降序，最新的在前
          : dateA - dateB; // 升序，最早的在前
      });
    }
  },
  mounted() {
    this.fetchTasks();
    // 每10秒自动刷新任务列表，更及时地反映状态变化
    this.refreshInterval = setInterval(this.fetchTasks, 10000);
    
    // 添加列宽调整功能
    this.$nextTick(() => {
      this.setupResizableColumns();
    });
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  },
  methods: {
    async fetchTasks() {
      // 如果已经在加载中，不重复请求
      if (this.loading && this.tasks.length > 0) return;
      
      // 首次加载显示loading状态，后续静默更新
      const isFirstLoad = this.tasks.length === 0;
      if (isFirstLoad) this.loading = true;
      this.error = null;
      
      try {
        // 更新API端点路径，保持与后端一致
        const response = await fetch('/api/v1/evaluations');
        
        if (!response.ok) {
          throw new Error(`获取任务列表失败: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        // 更新：适配新的API响应格式，使用data.items而不是直接使用data
        console.log('API响应数据格式:', data);
        this.tasks = data.items || [];
        console.log('更新后的任务列表:', this.tasks);
        
        // 更新活动任务集合
        this.activeTasks.clear();
        this.tasks.forEach(task => {
          if (task.status === 'RUNNING' || task.status === 'PENDING') {
            this.activeTasks.add(task.id);
          }
        });
        
        // 如果有活动任务，加速刷新间隔
        if (this.activeTasks.size > 0 && this.refreshInterval) {
          clearInterval(this.refreshInterval);
          this.refreshInterval = setInterval(this.fetchTasks, 5000); // 每5秒刷新
        } else if (this.activeTasks.size === 0 && this.refreshInterval) {
          // 没有活动任务，恢复正常刷新间隔
          clearInterval(this.refreshInterval);
          this.refreshInterval = setInterval(this.fetchTasks, 30000); // 每30秒刷新
        }
      } catch (err) {
        console.error('获取任务列表错误:', err);
        this.error = `获取任务列表失败: ${err.message}`;
      } finally {
        this.loading = false;
      }
    },
    
    viewLogs(taskId) {
      // 发出事件，通知父组件显示日志
      this.$emit('view-logs', taskId);
    },
    
    async terminateTask(taskId) {
      if (!confirm('确定要终止此任务吗？')) return;
      
      this.loadingTaskId = taskId;
      
      try {
        const response = await fetch(`/api/v1/evaluations/${taskId}/terminate`, {
          method: 'POST',
        });
        
        if (!response.ok) {
          throw new Error(`终止任务失败: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        alert(result.message || '任务终止操作已执行');
        this.fetchTasks(); // 刷新列表
      } catch (err) {
        console.error('终止任务错误:', err);
        alert(`终止任务失败: ${err.message}`);
      }
    },
    
    async deleteTask(taskId) {
      if (!confirm('确定要删除此任务吗？此操作不可恢复。')) return;
      
      try {
        const response = await fetch(`/api/v1/evaluations/${taskId}`, {
          method: 'DELETE',
        });
        
        if (!response.ok) {
          throw new Error(`删除任务失败: ${response.status} ${response.statusText}`);
        }
        
        alert('任务已成功删除');
        this.fetchTasks(); // 刷新列表
      } catch (err) {
        console.error('删除任务错误:', err);
        alert(`删除任务失败: ${err.message}`);
      }
    },
    
    // 任务名称编辑相关方法
    isEditing(taskId) {
      return this.editingTaskId === taskId;
    },
    
    startEditing(task) {
      this.editingTaskId = task.id;
      this.editingName = task.name || `评测任务-${task.id}`;
      
      // 下一个DOM更新周期后自动聚焦输入框
      this.$nextTick(() => {
        if (this.$refs.nameInput) {
          this.$refs.nameInput.focus();
        }
      });
    },
    
    cancelEditing() {
      this.editingTaskId = null;
      this.editingName = '';
    },
    
    async saveTaskName(taskId) {
      if (!this.editingName.trim()) {
        alert('任务名称不能为空');
        return;
      }
      
      try {
        const response = await fetch(`/api/v1/evaluations/${taskId}/name`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ name: this.editingName.trim() })
        });
        
        if (!response.ok) {
          throw new Error(`更新任务名称失败: ${response.status} ${response.statusText}`);
        }
        
        // 更新本地任务名称
        const taskIndex = this.tasks.findIndex(t => t.id === taskId);
        if (taskIndex !== -1) {
          this.tasks[taskIndex].name = this.editingName.trim();
        }
        
        this.cancelEditing();
      } catch (err) {
        console.error('更新任务名称错误:', err);
        alert(`更新任务名称失败: ${err.message}`);
      }
    },
    
    // 排序相关方法
    toggleSort() {
      this.sortDirection = this.sortDirection === 'desc' ? 'asc' : 'desc';
    },
    
    getStatusText(status) {
      const statusMap = {
        'PENDING': '等待中',
        'RUNNING': '运行中',
        'COMPLETED': '已完成',
        'FAILED': '失败',
        'TERMINATED': '已终止'
      };
      return statusMap[status] || status;
    },
    
    // 新增方法，用于处理内部状态码
    getTaskStatusType(status) {
      if (!status) return 'unknown';
      
      // 规范化状态，全部转为小写并移除前缀
      const normalizedStatus = String(status).toLowerCase();
      
      if (normalizedStatus.includes('pending') || normalizedStatus.includes('waiting')) return 'pending';
      if (normalizedStatus.includes('running')) return 'running';
      if (normalizedStatus.includes('completed') || normalizedStatus.includes('success')) return 'completed';
      if (normalizedStatus.includes('failed') || normalizedStatus.includes('error')) return 'failed';
      if (normalizedStatus.includes('terminated') || normalizedStatus.includes('stopped')) return 'terminated';
      
      return 'unknown';
    },
    
    // 格式化状态显示
    formatStatus(status) {
      if (!status) return '未知状态';
      
      // 处理内部枚举格式，如 EVALUATIONSTATUS.RUNNING
      if (status.includes('EVALUATIONSTATUS.')) {
        const pureName = status.replace('EVALUATIONSTATUS.', '');
        return this.getStatusText(pureName);
      }
      
      // 正常状态码处理
      return this.getStatusText(status);
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '';
      
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date);
    },
    
    formatDatePart(dateStr) {
      if (!dateStr) return '';
      
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).format(date);
    },
    
    formatTimePart(dateStr) {
      if (!dateStr) return '';
      
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date);
    },
    
    // 改进列宽调整功能
    setupResizableColumns() {
      const table = document.querySelector('.tasks-table');
      if (!table) return;
      
      const cols = table.querySelectorAll('th.resizable');
      
      cols.forEach((col, index) => {
        // 创建调整手柄
        const resizer = document.createElement('div');
        resizer.classList.add('column-resizer');
        
        let startWidth, startX, currentColumn, nextColumn;
        
        // 鼠标按下事件
        const mouseDownHandler = function(e) {
          startX = e.pageX;
          
          currentColumn = col;
          const colIndex = Array.from(col.parentElement.children).indexOf(col);
          
          // 获取当前列宽度
          const styles = window.getComputedStyle(currentColumn);
          startWidth = parseInt(styles.width, 10);
          
          // 禁用文本选择
          document.body.style.userSelect = 'none';
          
          // 添加事件监听
          document.addEventListener('mousemove', mouseMoveHandler);
          document.addEventListener('mouseup', mouseUpHandler);
          
          resizer.classList.add('resizing');
        };
        
        // 鼠标移动事件
        const mouseMoveHandler = function(e) {
          const widthChange = e.pageX - startX;
          
          if (startWidth + widthChange > 30) {
            currentColumn.style.width = `${startWidth + widthChange}px`;
            
            // 更新colgroup中对应的col元素
            const colgroup = table.querySelector('colgroup');
            if (colgroup && colgroup.children[index]) {
              colgroup.children[index].style.width = `${startWidth + widthChange}px`;
            }
          }
        };
        
        // 鼠标释放事件
        const mouseUpHandler = function() {
          document.body.style.userSelect = '';
          document.removeEventListener('mousemove', mouseMoveHandler);
          document.removeEventListener('mouseup', mouseUpHandler);
          resizer.classList.remove('resizing');
        };
        
        // 添加事件监听
        resizer.addEventListener('mousedown', mouseDownHandler);
        
        col.appendChild(resizer);
        col.style.position = 'relative';
      });
    }
  }
}
</script>

<style scoped>
.task-list {
  width: 100%;
}

.task-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.task-list-actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  border: none;
  background-color: #f0f0f0;
  transition: background-color 0.2s;
}

button:hover {
  background-color: #e0e0e0;
}

.btn-secondary {
  background-color: #f0f0f0;
}

.btn-primary {
  background-color: #4caf50;
  color: white;
}

.btn-primary:hover {
  background-color: #45a049;
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-bottom: 20px;
  border-radius: 4px;
}

.tasks-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  table-layout: fixed;
  font-size: smaller; /* 调整表格整体字体大小 */
}

.tasks-table th,
.tasks-table td {
  border: 1px solid #ddd;
  padding: 8px; /* 减小内边距以适应更小字体 */
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tasks-table th {
  background-color: #f2f2f2;
  font-weight: bold;
  position: relative; /* 确保相对定位以支持调整手柄 */
}

.sort-header {
  cursor: pointer;
}

.sort-icon {
  margin-left: 5px;
  display: inline-block;
}

.tasks-table tr:nth-child(even) {
  background-color: #f9f9f9;
}

.tasks-table tr.running {
  background-color: #e8f5e9;
}

.status {
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  display: inline-block;
  min-width: 50px;
  text-align: center;
}

.status.pending {
  background-color: #e3f2fd;
  color: #1976d2;
}

.status.running {
  background-color: #e8f5e9;
  color: #4caf50;
}

.status.completed {
  background-color: #e8f5e9;
  color: #388e3c;
}

.status.failed {
  background-color: #ffebee;
  color: #d32f2f;
}

.status.terminated {
  background-color: #e0e0e0;
  color: #616161;
}

.status.unknown {
  background-color: #f5f5f5;
  color: #9e9e9e;
}

.loading, .error, .no-tasks {
  padding: 20px;
  text-align: center;
  margin-top: 20px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.error {
  color: #d32f2f;
  background-color: #ffebee;
}

/* 操作图标样式 */
.action-buttons {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
}

.action-btn {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  border: none;
  font-size: 11px;
  font-weight: 500;
  min-width: 45px;
  color: #fff;
  transition: all 0.2s;
}

.log-btn {
  background-color: #3182ce;
}

.log-btn:hover {
  background-color: #2c5282;
}

.stop-btn {
  background-color: #e53e3e;
}

.stop-btn:hover {
  background-color: #c53030;
}

.delete-btn {
  background-color: #718096;
}

.delete-btn:hover {
  background-color: #4a5568;
}

/* 改进列宽调整样式 */
.tasks-table th.resizable {
  position: relative;
  user-select: none;
}

.column-resizer {
  position: absolute;
  top: 0;
  right: 0;
  width: 5px;
  height: 100%;
  background-color: transparent;
  cursor: col-resize;
  z-index: 1;
}

.column-resizer:hover,
.column-resizer.resizing {
  background-color: #2c5282;
}

/* 日期单元格样式优化 */
.date-cell {
  padding: 4px 8px !important;
}

.date-container {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.date-part {
  font-weight: 500;
}

.time-part {
  color: #666;
  font-size: 0.9em;
}

/* 任务名称编辑样式 */
.task-name-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.edit-name-btn {
  opacity: 0.2;
  cursor: pointer;
  background: none;
  border: none;
  font-size: 12px;
  color: #4a5568;
  padding: 2px 4px;
  margin-left: 5px;
  transition: opacity 0.2s;
}

.task-name-container:hover .edit-name-btn {
  opacity: 1;
}

.edit-name-form {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.edit-name-input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid #3182ce;
  border-radius: 3px;
  font-size: 12px;
  margin-bottom: 4px;
}

.edit-actions {
  display: flex;
  gap: 5px;
}

.save-btn, .cancel-btn {
  padding: 2px 6px;
  font-size: 11px;
  border-radius: 3px;
  cursor: pointer;
  border: none;
}

.save-btn {
  background-color: #3182ce;
  color: white;
}

.cancel-btn {
  background-color: #e2e8f0;
  color: #4a5568;
}

@media (max-width: 1200px) {
  .actions {
    flex-direction: column;
    gap: 3px;
  }
  
  .edit-actions {
    flex-direction: row;
  }
}

/* 响应式表格优化 */
@media (max-width: 1600px) {
  .tasks-table th,
  .tasks-table td {
    padding: 6px 4px;
  }
}

@media (max-width: 1400px) {
  .tasks-table th:nth-child(1) {
    width: 22%;
  }
  
  .tasks-table th:nth-child(2),
  .tasks-table th:nth-child(3) {
    width: 18%;
  }
  
  .tasks-table th:nth-child(4) {
    width: 12%;
  }
  
  .tasks-table th:nth-child(5) {
    width: 15%;
  }
  
  .tasks-table th:nth-child(6) {
    width: 15%;
  }
  
  .action-btn {
    font-size: 10px;
    padding: 3px 6px;
    min-width: 40px;
  }
}

/* 终止按钮图标样式 */
.stop-icon {
  color: #e53935;
}

.stop-icon:hover {
  color: #c62828;
}
</style> 