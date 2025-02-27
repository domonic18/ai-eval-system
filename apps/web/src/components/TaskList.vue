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
    
    <table v-else class="tasks-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>模型</th>
          <th>数据集</th>
          <th>状态</th>
          <th>进度</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id" :class="{ 'running': task.status === 'RUNNING' }">
          <td>{{ task.id }}</td>
          <td>{{ task.model_name }}</td>
          <td>{{ task.dataset_name }}</td>
          <td>
            <span :class="['status', task.status.toLowerCase()]">{{ getStatusText(task.status) }}</span>
          </td>
          <td>
            <div v-if="task.status === 'RUNNING'" class="progress-container">
              <div class="progress-bar" :style="{ width: `${task.progress || 0}%` }"></div>
              <span class="progress-text">{{ task.progress || 0 }}%</span>
            </div>
            <span v-else>-</span>
          </td>
          <td>{{ formatDate(task.created_at) }}</td>
          <td class="actions">
            <button @click="viewLogs(task.id)" class="action-btn log-btn">查看日志</button>
            <button v-if="task.status === 'RUNNING'" @click="terminateTask(task.id)" class="action-btn terminate-btn">终止任务</button>
            <button v-if="task.status === 'COMPLETED'" @click="viewResults(task.id)" class="action-btn results-btn">查看结果</button>
          </td>
        </tr>
      </tbody>
    </table>
    
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
    }
  }
}
</script>

<style scoped>
.task-list {
  width: 100%;
  padding: 20px;
}

.task-list-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.tasks-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.tasks-table th,
.tasks-table td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
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
  padding: 5px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
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

.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 5px 8px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-right: 4px;
}

.log-btn {
  background-color: #e3f2fd;
  color: #1976d2;
}

.log-btn:hover {
  background-color: #bbdefb;
}

.terminate-btn {
  background-color: #ffebee;
  color: #d32f2f;
}

.terminate-btn:hover {
  background-color: #ffcdd2;
}

.results-btn {
  background-color: #e8f5e9;
  color: #388e3c;
}

.results-btn:hover {
  background-color: #c8e6c9;
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

.progress-container {
  position: relative;
  width: 100%;
  height: 20px;
  background-color: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  color: #333;
}
</style> 