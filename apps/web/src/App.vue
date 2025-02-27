<script>
import TaskList from './components/TaskList.vue'
import LogViewer from './components/LogViewer.vue'
import TaskForm from './components/TaskForm.vue'

export default {
  name: 'App',
  components: {
    TaskList,
    LogViewer,
    TaskForm
  },
  data() {
    return {
      showTaskForm: false,
      currentLogTaskId: null
    }
  },
  methods: {
    viewTaskLogs(taskId) {
      this.currentLogTaskId = taskId;
    },
    
    onTaskCreated(task) {
      // 关闭表单
      this.showTaskForm = false;
      
      // 刷新任务列表
      if (this.$refs.taskList) {
        this.$refs.taskList.fetchTasks();
      }
      
      // 显示成功消息
      alert(`任务 #${task.id} 已创建！`);
      
      // 自动打开日志查看器
      this.viewTaskLogs(task.id);
    }
  }
}
</script>

<template>
  <div class="app">
    <header>
      <h1>OpenCompass 评测系统</h1>
    </header>

    <main>
      <!-- 任务表单弹窗 -->
      <div v-if="showTaskForm" class="modal">
        <div class="modal-content">
          <TaskForm 
            @cancel="showTaskForm = false" 
            @task-created="onTaskCreated" 
          />
        </div>
      </div>
      
      <!-- 日志查看器弹窗 -->
      <div v-if="currentLogTaskId" class="modal log-modal">
        <div class="modal-content log-modal-content">
          <LogViewer 
            :taskId="currentLogTaskId" 
            @close="currentLogTaskId = null" 
          />
        </div>
      </div>
      
      <!-- 任务列表 -->
      <TaskList 
        @create-task="showTaskForm = true" 
        @view-logs="viewTaskLogs" 
        ref="taskList"
      />
    </main>

    <footer>
      <p>OpenCompass 评测系统 &copy; {{ new Date().getFullYear() }}</p>
    </footer>
  </div>
</template>

<style>
/* 全局样式 */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

/* App容器 */
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 头部 */
header {
  background-color: #2196f3;
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

header h1 {
  font-size: 24px;
  font-weight: 500;
}

/* 主体内容 */
main {
  flex: 1;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* 页脚 */
footer {
  background-color: #f0f0f0;
  color: #666;
  text-align: center;
  padding: 12px;
  font-size: 14px;
  margin-top: auto;
}

/* 模态框 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  max-width: 600px;
  width: 100%;
  overflow: hidden;
  animation: fadeIn 0.3s;
}

.log-modal-content {
  max-width: 90%;
  height: 80vh;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 响应式调整 */
@media (max-width: 768px) {
  main {
    padding: 10px;
  }
  
  .modal {
    padding: 10px;
  }
  
  .log-modal-content {
    max-width: 95%;
    height: 90vh;
  }
}
</style>
