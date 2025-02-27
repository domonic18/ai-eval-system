<template>
  <div class="log-viewer">
    <div class="log-header">
      <h2>任务 #{{ taskId }} 日志</h2>
      <div class="log-controls">
        <span class="status-indicator" :class="connectionStatus">
          {{ connectionStatusText }}
        </span>
        <button @click="toggleAutoScroll" :class="{ active: autoScroll }">
          {{ autoScroll ? '自动滚动：开' : '自动滚动：关' }}
        </button>
        <button @click="clearLogs">清空</button>
        <button @click="downloadLogs">下载</button>
        <button @click="$emit('close')" class="close-btn">关闭</button>
      </div>
    </div>
    
    <div class="task-info" v-if="taskStatus">
      <div class="task-status">
        <strong>状态:</strong> <span :class="['status', taskStatus.status?.toLowerCase()]">{{ getStatusText(taskStatus.status) }}</span>
      </div>
      <div class="task-progress" v-if="taskStatus.status === 'RUNNING'">
        <strong>进度:</strong> {{ taskStatus.progress || 0 }}%
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: `${taskStatus.progress || 0}%` }"></div>
        </div>
      </div>
    </div>
    
    <div ref="logContainer" class="log-container">
      <div v-if="logs.length === 0" class="empty-logs">
        <p>暂无日志信息</p>
      </div>
      <div v-for="(log, index) in logs" :key="index" class="log-line">
        <pre>{{ log }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogViewer',
  props: {
    taskId: {
      type: [Number, String],
      required: true
    }
  },
  data() {
    return {
      logs: [],
      socket: null,
      connectionStatus: 'disconnected',
      connectionError: '',
      autoScroll: true,
      reconnectAttempts: 0,
      maxReconnectAttempts: 5,
      reconnectInterval: null,
      taskStatus: null,
      statusInterval: null
    }
  },
  computed: {
    connectionStatusText() {
      switch(this.connectionStatus) {
        case 'connecting': return '正在连接...';
        case 'connected': return '已连接';
        case 'disconnected': return '已断开连接';
        case 'error': return `连接错误: ${this.connectionError}`;
        default: return '未知状态';
      }
    }
  },
  mounted() {
    this.connectWebSocket();
    // 初始加载REST API的日志
    this.fetchInitialLogs();
    // 定期更新任务状态
    this.fetchTaskStatus();
    this.statusInterval = setInterval(this.fetchTaskStatus, 5000);
  },
  beforeUnmount() {
    this.closeWebSocket();
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
    }
    if (this.statusInterval) {
      clearInterval(this.statusInterval);
    }
  },
  watch: {
    // 当任务ID变化时重新连接
    taskId() {
      this.closeWebSocket();
      this.logs = [];
      this.connectWebSocket();
      this.fetchInitialLogs();
    }
  },
  methods: {
    connectWebSocket() {
      this.connectionStatus = 'connecting';
      
      // 关闭现有连接
      this.closeWebSocket();
      
      // 创建新的WebSocket连接
      try {
        // 根据部署环境调整WebSocket URL
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/evaluations/${this.taskId}/ws_logs`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
          this.connectionStatus = 'connected';
          this.reconnectAttempts = 0;
          console.log(`WebSocket连接已建立: ${wsUrl}`);
        };
        
        this.socket.onmessage = (event) => {
          try {
            // 尝试解析为JSON，检查是否为信息或错误消息
            const data = JSON.parse(event.data);
            if (data.error) {
              console.error('WebSocket错误消息:', data.error);
              this.logs.push(`[错误] ${data.error}`);
            } else if (data.info) {
              this.logs.push(`[信息] ${data.info}`);
            }
          } catch (e) {
            // 如果不是JSON，则为普通日志行
            this.logs.push(event.data);
          }
          
          // 自动滚动到底部
          if (this.autoScroll) {
            this.$nextTick(this.scrollToBottom);
          }
        };
        
        this.socket.onclose = (event) => {
          this.connectionStatus = 'disconnected';
          console.log('WebSocket连接已关闭', event);
          
          // 尝试重新连接
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const timeout = Math.pow(2, this.reconnectAttempts) * 1000; // 指数退避
            this.logs.push(`[系统] 连接已断开，${timeout/1000}秒后尝试重新连接...`);
            
            setTimeout(() => {
              this.connectWebSocket();
            }, timeout);
          } else {
            this.logs.push('[系统] 多次重连失败，请手动刷新页面重试。');
          }
        };
        
        this.socket.onerror = (error) => {
          this.connectionStatus = 'error';
          this.connectionError = '连接服务器失败';
          console.error('WebSocket错误:', error);
        };
      } catch (err) {
        this.connectionStatus = 'error';
        this.connectionError = err.message;
        console.error('创建WebSocket连接错误:', err);
      }
    },
    
    closeWebSocket() {
      if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
        this.socket.close();
        this.socket = null;
      }
    },
    
    async fetchInitialLogs() {
      try {
        const response = await fetch(`/api/v1/evaluations/${this.taskId}/logs?lines=100`);
        
        if (!response.ok) {
          throw new Error(`获取日志失败: ${response.status} ${response.statusText}`);
        }
        
        const logs = await response.json();
        this.logs = logs;
        
        if (this.autoScroll) {
          this.$nextTick(this.scrollToBottom);
        }
      } catch (err) {
        console.error('获取初始日志错误:', err);
        this.logs.push(`[错误] 获取初始日志失败: ${err.message}`);
      }
    },
    
    scrollToBottom() {
      const container = this.$refs.logContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    
    toggleAutoScroll() {
      this.autoScroll = !this.autoScroll;
      if (this.autoScroll) {
        this.scrollToBottom();
      }
    },
    
    clearLogs() {
      this.logs = [];
    },
    
    downloadLogs() {
      if (this.logs.length === 0) {
        alert('没有可下载的日志');
        return;
      }
      
      const logText = this.logs.join('\n');
      const blob = new Blob([logText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `task_${this.taskId}_logs_${new Date().toISOString().replace(/:/g, '-')}.txt`;
      document.body.appendChild(a);
      a.click();
      
      // 清理
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 100);
    },
    
    async fetchTaskStatus() {
      try {
        const response = await fetch(`/api/v1/evaluations/${this.taskId}`);
        
        if (!response.ok) {
          throw new Error(`获取任务状态失败: ${response.status} ${response.statusText}`);
        }
        
        this.taskStatus = await response.json();
        
        // 如果任务已完成或失败，停止状态轮询
        if (this.taskStatus.status === 'COMPLETED' || this.taskStatus.status === 'FAILED' || this.taskStatus.status === 'TERMINATED') {
          if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
          }
        }
      } catch (err) {
        console.error('获取任务状态错误:', err);
      }
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
    }
  }
}
</script>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f8f9fa;
  overflow: hidden;
}

.log-header {
  padding: 12px 16px;
  background-color: #f0f0f0;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.status-indicator {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 8px;
}

.status-indicator.connected {
  background-color: #e8f5e9;
  color: #388e3c;
}

.status-indicator.connecting {
  background-color: #fff8e1;
  color: #ffa000;
}

.status-indicator.disconnected,
.status-indicator.error {
  background-color: #ffebee;
  color: #d32f2f;
}

.log-controls button {
  padding: 6px 10px;
  background-color: #f0f0f0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.log-controls button.active {
  background-color: #e3f2fd;
  color: #1976d2;
  font-weight: bold;
}

.log-controls button:hover:not(:disabled) {
  background-color: #e0e0e0;
}

.log-controls button.close-btn {
  background-color: #f44336;
  color: white;
}

.log-controls button.close-btn:hover {
  background-color: #e53935;
}

.connection-status {
  padding: 8px 16px;
  font-size: 14px;
  border-bottom: 1px solid #e0e0e0;
}

.connection-status.connecting {
  background-color: #fff9c4;
  color: #fbc02d;
}

.connection-status.connected {
  background-color: #e8f5e9;
  color: #4caf50;
}

.connection-status.disconnected {
  background-color: #f5f5f5;
  color: #9e9e9e;
}

.connection-status.error {
  background-color: #ffebee;
  color: #f44336;
}

.log-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  background-color: #212121;
  color: #eee;
  font-family: monospace;
}

.log-line {
  margin: 0;
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
}

.empty-logs {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #9e9e9e;
}

.task-info {
  padding: 12px 16px;
  background-color: #fafafa;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.task-status .status {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.task-status .status.running {
  background-color: #e8f5e9;
  color: #4caf50;
}

.task-status .status.completed {
  background-color: #e8f5e9;
  color: #388e3c;
}

.task-status .status.failed {
  background-color: #ffebee;
  color: #d32f2f;
}

.task-status .status.pending {
  background-color: #e3f2fd;
  color: #1976d2;
}

.task-status .status.terminated {
  background-color: #e0e0e0;
  color: #616161;
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-progress .progress-container {
  width: 150px;
  height: 10px;
  background-color: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
}

.task-progress .progress-bar {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.3s ease;
}
</style> 