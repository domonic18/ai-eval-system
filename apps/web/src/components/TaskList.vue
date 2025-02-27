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
          <col width="6%">
          <col width="22%">
          <col width="22%">
          <col width="14%">
          <col width="20%">
          <col width="10%">
        </colgroup>
        <thead>
          <tr>
            <th class="resizable">ID</th>
            <th class="resizable">模型</th>
            <th class="resizable">数据集</th>
            <th class="resizable">状态</th>
            <th class="resizable">创建时间</th>
            <th class="resizable">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id" :class="{ 'running': getTaskStatusType(task.status) === 'running' }">
            <td>{{ task.id }}</td>
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
              <div class="action-icons">
                <span class="icon-btn log-icon" @click="viewLogs(task.id)" title="查看日志">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svg-icon">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                  </svg>
                </span>
                
                <span v-if="getTaskStatusType(task.status) === 'running'" 
                      class="icon-btn terminate-icon" 
                      @click="terminateTask(task.id)"
                      title="终止任务">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svg-icon stop-icon">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  </svg>
                </span>
                
                <span v-if="getTaskStatusType(task.status) === 'completed'" 
                      class="icon-btn results-icon" 
                      @click="viewResults(task.id)"
                      title="查看结果">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svg-icon">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                  </svg>
                </span>
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
      loadingTaskId: null
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
        this.tasks = data;
        
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
    
    viewResults(taskId) {
      // 查找任务
      const task = this.tasks.find(t => t.id === taskId);
      if (!task || !task.results) {
        alert('暂无结果数据');
        return;
      }
      
      // 显示结果，这里简单用alert，实际应使用模态框或页面
      alert(`任务 #${taskId} 结果:\n${JSON.stringify(task.results, null, 2)}`);
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
    
    // 添加列宽调整功能的方法
    setupResizableColumns() {
      const table = document.querySelector('.tasks-table');
      if (!table) return;
      
      const cols = table.querySelectorAll('th.resizable');
      
      cols.forEach((col) => {
        // 创建调整手柄
        const resizer = document.createElement('div');
        resizer.classList.add('column-resizer');
        
        // 添加事件监听
        resizer.addEventListener('mousedown', this.initResize);
        
        col.appendChild(resizer);
        col.style.position = 'relative';
      });
    },
    
    // 初始化拖动调整
    initResize(e) {
      const th = e.target.parentElement;
      const startX = e.pageX;
      const startWidth = th.offsetWidth;
      
      // 添加临时样式到body以防止文本选择
      document.body.style.userSelect = 'none';
      
      // 列索引
      const thIndex = Array.from(th.parentElement.children).indexOf(th);
      
      // 调整handler
      const mouseMoveHandler = (e) => {
        const table = document.querySelector('.tasks-table');
        const colGroup = table.querySelector('colgroup');
        const col = colGroup.children[thIndex];
        
        const width = startWidth + (e.pageX - startX);
        if (width > 50) { // 最小宽度限制
          col.style.width = `${width}px`;
        }
      };
      
      // 停止调整handler
      const mouseUpHandler = () => {
        document.removeEventListener('mousemove', mouseMoveHandler);
        document.removeEventListener('mouseup', mouseUpHandler);
        document.body.style.userSelect = '';
      };
      
      // 添加临时事件监听
      document.addEventListener('mousemove', mouseMoveHandler);
      document.addEventListener('mouseup', mouseUpHandler);
      
      e.preventDefault();
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
}

.tasks-table th,
.tasks-table td {
  border: 1px solid #ddd;
  padding: 10px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tasks-table th {
  background-color: #f2f2f2;
  font-weight: bold;
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
  font-size: 12px;
  font-weight: bold;
  display: inline-block;
  min-width: 60px;
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
.action-icons {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.icon-btn {
  cursor: pointer;
  padding: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s, transform 0.2s;
  position: relative;
}

.svg-icon {
  color: #666;
  transition: color 0.2s;
}

.icon-btn:hover {
  background-color: #f0f0f0;
  transform: scale(1.1);
}

.icon-btn:hover .svg-icon {
  color: #333;
}

.log-icon:hover {
  background-color: #e3f2fd;
}

.terminate-icon:hover {
  background-color: #ffebee;
}

.results-icon:hover {
  background-color: #e8f5e9;
}

/* 可调整列宽样式 */
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
}

.column-resizer:hover,
.column-resizer:active {
  background-color: #ddd;
}

/* 日期单元格样式优化 */
.date-cell {
  padding: 5px 10px !important;
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

@media (max-width: 1200px) {
  .actions {
    flex-direction: column;
    gap: 3px;
  }
}

/* 响应式表格优化 */
@media (max-width: 1600px) {
  .tasks-table th,
  .tasks-table td {
    padding: 8px 6px;
  }
}

@media (max-width: 1400px) {
  .tasks-table th:nth-child(1) {
    width: 5%;
  }
  
  .tasks-table th:nth-child(2),
  .tasks-table th:nth-child(3) {
    width: 20%;
  }
  
  .tasks-table th:nth-child(4) {
    width: 12%;
  }
  
  .tasks-table th:nth-child(5) {
    width: 20%;
  }
  
  .tasks-table th:nth-child(6) {
    width: 10%;
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