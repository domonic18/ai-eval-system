<!--
  TaskList.vue - 任务列表组件 (优化版)
  
  功能：
  1. 我的评测/全部评测Tab切换
  2. 搜索过滤功能
  3. Element Plus美化表格
  4. 翻页功能
  5. 可调整列宽与用户信息显示
-->
<template>
  <div class="task-list-container">
    <!-- 顶部操作区 -->
    <div class="top-controls" v-if="!hideHeader">
      <h3 class="section-title">评测任务列表</h3>
      <div class="action-buttons">
        <el-button type="primary" @click="$emit('create-task')">创建新任务</el-button>
        <el-button @click="fetchTasks">刷新列表</el-button>
      </div>
    </div>
    
    <!-- 筛选区域 -->
    <div class="filter-container">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的评测" name="my"></el-tab-pane>
        <el-tab-pane label="全部评测" name="all"></el-tab-pane>
      </el-tabs>
      
      <div class="search-area">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模型名称或数据集"
          prefix-icon="el-icon-search"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>
    
    <!-- 表格区域 -->
    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      border
      :header-cell-style="{ 'background-color': '#f7f7f7' }"
      @header-dragend="handleHeaderDragend"
    >
      <!-- 用户信息列 -->
      <el-table-column
        label="创建者"
        width="120"
        align="center"
        fixed="left"
      >
        <template #default="scope">
          <div class="user-info">
            <el-avatar 
              :size="30" 
              :src="scope.row.user_avatar || defaultAvatar"
              class="user-avatar"
            ></el-avatar>
            <span class="user-name">{{ scope.row.user_name || '未知用户' }}</span>
          </div>
        </template>
      </el-table-column>
      
      <!-- 任务名称列 -->
      <el-table-column
        label="任务名称"
        min-width="180"
        prop="name"
      >
        <template #default="scope">
          <div class="task-name-cell">
            <span v-if="!isEditing(scope.row.id)">
              {{ scope.row.name || `评测任务-${scope.row.id}` }}
              <el-button
                type="primary"
                link
                icon="Edit"
                @click="startEditing(scope.row)"
              />
            </span>
            <div v-else class="name-editor">
              <el-input
                v-model="editingName"
                size="small"
                @keyup.enter="saveTaskName(scope.row.id)"
                ref="nameInput"
              />
              <div class="edit-actions">
                <el-button
                  type="primary"
                  size="small"
                  @click="saveTaskName(scope.row.id)"
                >保存</el-button>
                <el-button
                  size="small"
                  @click="cancelEditing"
                >取消</el-button>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>
      
      <!-- 评测模型列 -->
      <el-table-column
        label="评测模型"
        min-width="160"
        prop="model_name"
      />
      
      <!-- 评测数据集列 -->
      <el-table-column
        label="评测数据集"
        min-width="160"
        prop="dataset_names"
      />
      
      <!-- 评测状态列 -->
      <el-table-column
        label="状态"
        width="120"
        prop="status"
      >
        <template #default="scope">
          <el-tag
            :type="getStatusTagType(scope.row.status)"
            effect="plain"
            size="small"
          >
            {{ formatStatus(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- 创建时间列 -->
      <el-table-column
        label="创建时间"
        min-width="160"
        sortable
        :sort-method="sortByDate"
      >
        <template #default="scope">
          <div class="date-display">
            <div>{{ formatDatePart(scope.row.created_at) }}</div>
            <div class="time-part">{{ formatTimePart(scope.row.created_at) }}</div>
          </div>
        </template>
      </el-table-column>
      
      <!-- 操作列 -->
      <el-table-column
        label="操作"
        width="220"
        fixed="right"
      >
        <template #default="scope">
          <div class="action-column">
            <el-button
              type="primary"
              size="small"
              @click="viewLogs(scope.row.id)"
            >日志</el-button>
            
            <el-button
              v-if="getTaskStatusType(scope.row.status) === 'completed'"
              type="success"
              size="small"
              @click="viewResults(scope.row.id)"
            >结果</el-button>
            
            <el-button
              v-if="getTaskStatusType(scope.row.status) === 'running'"
              type="warning"
              size="small"
              @click="terminateTask(scope.row.id)"
            >停止</el-button>
            
            <el-button
              type="danger"
              size="small"
              @click="deleteTask(scope.row.id)"
            >删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页区域 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="handlePageChange"
      />
    </div>
    
    <!-- 无数据提示 -->
    <el-empty
      v-if="tableData.length === 0 && !loading"
      description="暂无评测任务，请创建新任务"
    >
      <el-button type="primary" @click="$emit('create-task')">创建新任务</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Search, Edit, MoreFilled } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';

// 接收属性
const props = defineProps({
  hideHeader: {
    type: Boolean,
    default: false
  }
});

// 定义事件
const emit = defineEmits(['create-task', 'view-logs', 'view-results']);

// 状态变量
const tasks = ref([]);
const loading = ref(false);
const error = ref(null);
const activeTab = ref('my');  // 默认显示我的评测
const searchQuery = ref('');
const currentPage = ref(1);
const pageSize = ref(10);
const total = ref(0);
const sortOrder = ref('descending');
const refreshInterval = ref(null);
const activeTasks = ref(new Set());
const editingTaskId = ref(null);
const editingName = ref('');
const nameInput = ref(null);
const defaultAvatar = '/default-avatar.png';  // 默认头像

// 计算属性
const tableData = computed(() => {
  return tasks.value;
});

// 排序方法
const sortByDate = (a, b) => {
  const dateA = new Date(a.created_at);
  const dateB = new Date(b.created_at);
  return sortOrder.value === 'ascending' ? dateA - dateB : dateB - dateA;
};

// 生命周期钩子
onMounted(() => {
  fetchTasks();
  refreshInterval.value = setInterval(fetchTasks, 10000);
});

onBeforeUnmount(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
});

// 方法
// 获取任务列表
async function fetchTasks() {
  if (loading.value && tasks.value.length > 0) return;
  
  const isFirstLoad = tasks.value.length === 0;
  if (isFirstLoad) loading.value = true;
  error.value = null;
  
  try {
    // 构建查询参数
    const params = new URLSearchParams();
    params.append('limit', pageSize.value);
    params.append('offset', (currentPage.value - 1) * pageSize.value);
    
    // 根据Tab添加用户筛选
    if (activeTab.value === 'my') {
      params.append('current_user_only', 'true');
    }
    
    // 添加搜索条件
    if (searchQuery.value) {
      params.append('search', searchQuery.value);
    }
    
    const response = await fetch(`/api/v1/evaluations?${params.toString()}`);
    
    if (!response.ok) {
      throw new Error(`获取任务列表失败: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    tasks.value = data.items || [];
    total.value = data.total || 0;
    
    // 更新活动任务集合
    activeTasks.value.clear();
    tasks.value.forEach(task => {
      if (task.status === 'RUNNING' || task.status === 'PENDING') {
        activeTasks.value.add(task.id);
      }
    });
    
    // 根据活动任务数量调整刷新间隔
    adjustRefreshInterval();
    
  } catch (err) {
    console.error('获取任务列表错误:', err);
    error.value = `获取任务列表失败: ${err.message}`;
    ElMessage.error(error.value);
  } finally {
    loading.value = false;
  }
}

// 调整刷新间隔
function adjustRefreshInterval() {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
  
  const interval = activeTasks.value.size > 0 ? 5000 : 30000;
  refreshInterval.value = setInterval(fetchTasks, interval);
}

// 查看日志
function viewLogs(taskId) {
  emit('view-logs', taskId);
}

// 查看结果
function viewResults(taskId) {
  emit('view-results', taskId);
}

// 终止任务
async function terminateTask(taskId) {
  try {
    const result = await ElMessageBox.confirm(
      '确定要终止此任务吗？终止后无法恢复。',
      '终止任务',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    if (result === 'confirm') {
      loading.value = true;
      
      const response = await fetch(`/api/v1/evaluations/${taskId}/terminate`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`终止任务失败: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      ElMessage.success(result.message || '任务终止操作已执行');
      fetchTasks();
    }
  } catch (err) {
    if (err !== 'cancel') {
      console.error('终止任务错误:', err);
      ElMessage.error(`终止任务失败: ${err.message}`);
    }
  } finally {
    loading.value = false;
  }
}

// 删除任务
async function deleteTask(taskId) {
  try {
    const result = await ElMessageBox.confirm(
      '确定要删除此任务吗？此操作不可恢复。',
      '删除任务',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'danger',
      }
    );
    
    if (result === 'confirm') {
      loading.value = true;
      
      const response = await fetch(`/api/v1/evaluations/${taskId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`删除任务失败: ${response.status} ${response.statusText}`);
      }
      
      ElMessage.success('任务已成功删除');
      fetchTasks();
    }
  } catch (err) {
    if (err !== 'cancel') {
      console.error('删除任务错误:', err);
      ElMessage.error(`删除任务失败: ${err.message}`);
    }
  } finally {
    loading.value = false;
  }
}

// 名称编辑相关方法
function isEditing(taskId) {
  return editingTaskId.value === taskId;
}

function startEditing(task) {
  editingTaskId.value = task.id;
  editingName.value = task.name || `评测任务-${task.id}`;
  
  nextTick(() => {
    if (nameInput.value) {
      nameInput.value.focus();
    }
  });
}

function cancelEditing() {
  editingTaskId.value = null;
  editingName.value = '';
}

async function saveTaskName(taskId) {
  if (!editingName.value.trim()) {
    ElMessage.warning('任务名称不能为空');
    return;
  }
  
  try {
    const response = await fetch(`/api/v1/evaluations/${taskId}/name`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name: editingName.value.trim() })
    });
    
    if (!response.ok) {
      throw new Error(`更新任务名称失败: ${response.status} ${response.statusText}`);
    }
    
    // 更新本地任务名称
    const taskIndex = tasks.value.findIndex(t => t.id === taskId);
    if (taskIndex !== -1) {
      tasks.value[taskIndex].name = editingName.value.trim();
    }
    
    ElMessage.success('任务名称已更新');
    cancelEditing();
  } catch (err) {
    console.error('更新任务名称错误:', err);
    ElMessage.error(`更新任务名称失败: ${err.message}`);
  }
}

// Tab变更处理
function handleTabChange() {
  currentPage.value = 1;
  fetchTasks();
}

// 搜索处理
function handleSearch() {
  currentPage.value = 1;
  fetchTasks();
}

// 分页处理
function handlePageChange() {
  fetchTasks();
}

// 列宽调整处理
function handleHeaderDragend(newWidth, oldWidth, column) {
  console.log('列宽已调整:', column, newWidth);
}

// 状态处理方法
function getTaskStatusType(status) {
  if (!status) return 'unknown';
  
  const normalizedStatus = String(status).toLowerCase();
  
  if (normalizedStatus.includes('pending') || normalizedStatus.includes('waiting')) return 'pending';
  if (normalizedStatus.includes('running')) return 'running';
  if (normalizedStatus.includes('completed') || normalizedStatus.includes('success')) return 'completed';
  if (normalizedStatus.includes('failed') || normalizedStatus.includes('error')) return 'failed';
  if (normalizedStatus.includes('terminated') || normalizedStatus.includes('stopped')) return 'terminated';
  
  return 'unknown';
}

function getStatusTagType(status) {
  const statusType = getTaskStatusType(status);
  const typeMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'terminated': 'info',
    'unknown': ''
  };
  return typeMap[statusType] || '';
}

function formatStatus(status) {
  if (!status) return '未知状态';
  
  // 处理内部枚举格式，如 EVALUATIONSTATUS.RUNNING
  if (status.includes('EVALUATIONSTATUS.')) {
    const pureName = status.replace('EVALUATIONSTATUS.', '');
    return getStatusText(pureName);
  }
  
  // 正常状态码处理
  return getStatusText(status);
}

function getStatusText(status) {
  const statusMap = {
    'PENDING': '等待中',
    'pending': '等待中',
    'RUNNING': '运行中',
    'running': '运行中',
    'COMPLETED': '已完成',
    'completed': '已完成',
    'FAILED': '失败',
    'failed': '失败',
    'TERMINATED': '已终止',
    'terminated': '已终止'
  };
  return statusMap[status] || status;
}

// 日期格式化
function formatDatePart(dateStr) {
  if (!dateStr) return '';
  
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date);
}

function formatTimePart(dateStr) {
  if (!dateStr) return '';
  
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date);
}
</script>

<style scoped>
.task-list-container {
  width: 100%;
  padding: 16px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.top-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.search-area {
  width: 300px;
}

.date-display {
  display: flex;
  flex-direction: column;
}

.time-part {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.user-avatar {
  margin-bottom: 5px;
}

.user-name {
  font-size: 12px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-name-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.name-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.action-column {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style> 