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
    <!-- 顶部操作区 - 将创建按钮和搜索框放在同一行 -->
    <div class="top-controls" v-if="!hideHeader">
      <div class="left-section">
        <h3 class="section-title">评测任务列表</h3>
        <el-button type="primary" @click="createTask">创建新任务</el-button>
      </div>
      
      <!-- 搜索区域移到右侧 -->
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
    
    <!-- 筛选区域 -->
    <div class="filter-container">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的评测" name="my"></el-tab-pane>
        <el-tab-pane label="全部评测" name="all"></el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- 表格区域 - 重新排序列，加粗表头 -->
    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      border
      :header-cell-style="{ 'background-color': '#f7f7f7', 'font-weight': 'bold' }"
      @header-dragend="handleHeaderDragend"
    >
      <!-- 任务编号/名称列（放在第一列） -->
      <el-table-column
        label="任务名称"
        min-width="180"
        prop="name"
        fixed="left"
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
        width="100"
        prop="status"
        align="center"
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
      
      <!-- 用户信息列（移到第5列） -->
      <el-table-column
        label="创建者"
        width="120"
        align="center"
      >
        <template #default="scope">
          <div class="user-info-horizontal">
            <el-avatar 
              :size="24" 
              :src="scope.row.user_avatar || defaultAvatar"
              class="user-avatar"
            ></el-avatar>
            <span class="user-name">{{ scope.row.user_name || '未知用户' }}</span>
          </div>
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
      
      <!-- 操作列 - 调整按钮间距 -->
      <el-table-column
        label="操作"
        width="200"
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
      <div class="page-size-selector">
        <span class="page-size-label">每页显示：</span>
        <el-select 
          v-model="pageSize" 
          @change="handlePageSizeChange" 
          size="small"
          style="width: 80px"
        >
          <el-option :value="10" label="10条" />
          <el-option :value="20" label="20条" />
          <el-option :value="50" label="50条" />
          <el-option :value="100" label="100条" />
        </el-select>
      </div>
      
      <div class="pagination-controls">
        <el-button 
          size="small" 
          :disabled="currentPage <= 1" 
          @click="handlePrevPage"
        >上一页</el-button>
        
        <span class="page-info">第 {{ currentPage }} 页，共 {{ totalPages }} 页</span>
        
        <el-button 
          size="small" 
          :disabled="currentPage >= totalPages" 
          @click="handleNextPage"
        >下一页</el-button>
      </div>
    </div>
    
    <!-- 无数据提示 -->
    <el-empty
      v-if="tableData.length === 0 && !loading"
      description="暂无评测任务，请创建新任务"
    >
      <el-button type="primary" @click="createTask">创建新任务</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Search, Edit, MoreFilled } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
// 导入API客户端
import api from '@/utils/api';

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

// 计算总页数
const totalPages = computed(() => {
  return Math.ceil(total.value / pageSize.value) || 1;
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
    
    console.log('正在获取评测任务列表...');
    
    // 使用导入的api而不是this.$api
    const response = await api.get(`/api/v1/evaluations?${params.toString()}`);
    
    console.log('评测任务列表API响应:', response.status);
    
    // 不需要再次await response.data，axios已经提供data属性
    const data = response.data;
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
      
      // 使用导入的api
      const response = await api.post(`/api/v1/evaluations/${taskId}/terminate`);
      
      if (response.status === 200) {
        const result = response.data;
        ElMessage.success(result.message || '任务终止操作已执行');
        fetchTasks();
      } else {
        throw new Error(`终止任务失败: ${response.status} ${response.statusText}`);
      }
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
      
      // 使用导入的api
      const response = await api.delete(`/api/v1/evaluations/${taskId}`);
      
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
    // 使用导入的api
    const response = await api.patch(`/api/v1/evaluations/${taskId}/name`, {
      name: editingName.value.trim()
    });
    
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

// 处理每页显示数量变化
function handlePageSizeChange() {
  currentPage.value = 1;
  fetchTasks();
}

// 上一页按钮处理
function handlePrevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    fetchTasks();
  }
}

// 下一页按钮处理
function handleNextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
    fetchTasks();
  }
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

function createTask() {
  console.log('点击了创建新任务按钮');
  emit('create-task');
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

.left-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.search-area {
  width: 300px;
}

.filter-container {
  margin-bottom: 16px;
}

/* 水平布局的用户信息 */
.user-info-horizontal {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

.user-avatar {
  margin: 0;
}

.user-name {
  font-size: 14px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 调整操作按钮样式，使其更紧凑 */
.action-column {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-column .el-button {
  padding: 6px 10px;
  min-width: 40px;
}

/* 分页控件样式 */
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  white-space: nowrap;
  min-width: 180px;
}

.page-size-selector .el-select {
  width: 80px;
  min-width: 80px;
}

.page-size-label {
  display: inline-block;
  line-height: 32px; /* 与el-select的高度保持一致 */
  vertical-align: middle;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-info {
  color: #606266;
  font-size: 14px;
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

/* 其他已有样式保持不变 */
</style> 