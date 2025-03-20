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
        <el-button type="primary" @click="$router.push('/evaluation')">创建新任务</el-button>
        <el-button @click="fetchTasks">刷新列表</el-button>
      </div>
    </div>
    
    <!-- 筛选和操作区域 -->
    <div class="filter-container">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="custom-tabs">
        <el-tab-pane label="我的评测" name="my"></el-tab-pane>
        <el-tab-pane label="全部评测" name="all"></el-tab-pane>
      </el-tabs>
      
      <div class="right-controls">
        <el-input
          v-model="searchQuery"
          placeholder="搜索模型名称或数据集"
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        
        <el-button type="primary"  @click="$router.push('/evaluation')">
          <el-icon><Plus /></el-icon> 创建新任务
        </el-button>
      </div>
    </div>
    
    <!-- 表格区域 -->
    <el-table
      v-loading="loading"
      :data="tableData"
      style="width: 100%"
      :border="false"
      :header-cell-style="{ 'background-color': '#f7f7f7' }"
      header-cell-class-name="table-header-bold"
      @header-dragend="handleHeaderDragend"
    >
      <!-- 任务名称列 -->
      <el-table-column
        label="任务名称"
        min-width="180"
        fixed="left"
      >
        <template #default="scope">
          <div class="task-name-cell">
            <span v-if="!isEditing(scope.row.id)">
              {{ scope.row.name || `评测任务-${scope.row.id}` }}
              <el-button
                type="primary"
                link
                circle
                size="small"
                @click="startEditing(scope.row)"
              >
                <el-icon><Edit /></el-icon>
              </el-button>
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
        min-width="100"
        prop="model_name"
      />
      
      <!-- 评测数据集列 -->
      <el-table-column
        label="评测数据集"
        min-width="160"
      >
        <template #default="scope">
          <div class="dataset-tags">
            <template v-if="getDatasetNames(scope.row.dataset_names).length > 0">
              <!-- 只显示前两个数据集 -->
              <el-tag
                v-for="(dataset, index) in getDatasetNames(scope.row.dataset_names).slice(0, 2)"
                :key="index"
                effect="plain"
                type="info"
                size="small"
                class="dataset-tag"
              >
                {{ dataset }}
              </el-tag>
              
              <!-- 如果数据集超过2个，显示剩余数量 -->
              <el-tag
                v-if="getDatasetNames(scope.row.dataset_names).length > 2"
                effect="plain"
                type="info"
                size="small"
                class="dataset-tag more-tag"
              >
                +{{ getDatasetNames(scope.row.dataset_names).length - 2 }}
              </el-tag>
            </template>
            <span v-else>-</span>
          </div>
        </template>
      </el-table-column>
      
      <!-- 评测状态列 -->
      <el-table-column
        label="状态"
        width="100"
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
      
      <!-- 创建者列 -->
      <el-table-column
        label="创建者"
        width="150"
        align="center"
      >
        <template #default="scope">
          <div class="user-info-horizontal">
            <el-avatar 
              :size="28" 
              :src="scope.row.user_avatar || defaultAvatar"
              class="user-avatar"
            ></el-avatar>
            <span class="user-name-horizontal">{{ scope.row.user_name || '未知用户' }}</span>
          </div>
        </template>
      </el-table-column>
      
      <!-- 创建时间列 -->
      <el-table-column
        label="创建时间"
        min-width="120"
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
        width="180"
        fixed="right"
      >
        <template #default="scope">
          <div class="action-buttons">
            <el-button 
              v-if="scope.row.status === 'running'" 
              size="small" 
              type="primary"
              @click="viewLogs(scope.row.id)"
              class="action-btn"
            >
              日志
            </el-button>
            
            <el-button 
              v-if="scope.row.status === 'running'"
              size="small"
              type="warning"
              @click="terminateTask(scope.row.id)"
              class="action-btn"
            >
              停止
            </el-button>
            
            <el-button 
              v-if="scope.row.status !== 'running'"
              size="small"
              type="primary"
              @click="viewLogs(scope.row.id)"
              class="action-btn"
            >
              日志
            </el-button>
            
            <el-button 
              v-if="scope.row.status !== 'running'"
              size="small"
              type="success"
              @click="viewResults(scope.row.id)"
              class="action-btn"
            >
              结果
            </el-button>
            
            <el-button 
              size="small" 
              type="danger"
              @click="deleteTask(scope.row.id)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
      
      <!-- 空数据状态 -->
      <template #empty>
        <el-empty 
          description="暂无评测任务"
          :image-size="100"
        >
          <el-button type="primary" @click="$emit('create-task')">
            <el-icon><Plus /></el-icon> 创建新任务
          </el-button>
        </el-empty>
      </template>
    </el-table>
    
    <!-- 分页区域 -->
    <div class="pagination-container">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="sizes, prev, pager, next"
        prev-text="上一页"
        next-text="下一页"
        total-text="总共"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      >
      </el-pagination>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { Search, Edit, Plus } from '@element-plus/icons-vue';
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
    
    console.log('正在获取评测任务列表...参数:', params.toString());
    
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

// 分页处理
function handlePageChange(newPage) {
  currentPage.value = newPage;
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

// 添加数据集处理方法
const getDatasetNames = (datasetNames) => {
  if (!datasetNames) return [];
  
  if (Array.isArray(datasetNames)) {
    return datasetNames;
  }
  
  if (typeof datasetNames === 'string') {
    return datasetNames.split(',').map(name => name.trim()).filter(Boolean);
  }
  
  return [];
};

// 在方法部分添加分页大小变更处理
function handleSizeChange(newSize) {
  pageSize.value = newSize
  currentPage.value = 1  // 切换每页大小时重置到第一页
  fetchTasks()
}
</script>

<style scoped>
.task-list-container {
  width: 100%;
  padding: 16px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  overflow: hidden;
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
  align-items: center;
}

.action-buttons .el-button.action-btn {
  margin-right: 1px;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.right-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 250px;
}

.date-display {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  line-height: 1.4;
}

.time-part {
  font-size: 12px;
  color: #909399;
}

.user-info-horizontal {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name-horizontal {
  font-size: 13px;
  color: #606266;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
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
  align-items: center;
  gap: 8px;
}

.dataset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.dataset-tag {
  margin: 2px;
  background-color: #f4f4f5;
}

/* 添加剩余数量标签的样式 */
.more-tag {
  background-color: #e9e9eb;
  color: #606266;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  padding: 12px 0;
  background: #fff;
  border-top: 1px solid #ebeef5;
}

:deep(.el-pagination) {
  padding: 0;
  align-items: center;
}

:deep(.el-pagination__total) {
  margin-right: 16px;
  font-weight: normal;
  color: #606266;
}

:deep(.el-pagination__sizes) {
  margin: 0 12px;
  position: relative;
}

.size-prefix {
  position: absolute;
  left: -68px;
  top: 50%;
  transform: translateY(-50%);
  color: #606266;
  font-size: 14px;
}

:deep(.el-select) {
  width: 100px;
}

:deep(.el-select .el-input__inner) {
  padding-right: 25px;
}

:deep(.el-pagination__jump) {
  display: none !important;
}

:deep(.el-pagination__sizes .el-select .el-input .el-input__inner) {
  padding-right: 15px;
  text-align: center;
}

:deep(.el-select-dropdown__item) {
  text-align: center;
  padding: 0 10px;
}

:deep(.el-pagination.is-background .btn-prev),
:deep(.el-pagination.is-background .btn-next) {
  padding: 0 12px;
  background: transparent;
}

:deep(.el-pagination.is-background .btn-prev:hover),
:deep(.el-pagination.is-background .btn-next:hover) {
  background-color: #f4f4f5;
}

.table-header-bold .el-table__cell {
  font-weight: bold !important;
}

:deep(.table-header-bold .el-table__cell) {
  font-weight: bold !important;
}

:deep(.el-table) {
  --el-table-border-color: transparent;
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table__header) th {
  border: none !important;
}

:deep(.el-table__body) td {
  border: none !important;
}

:deep(.el-table--border)::after,
:deep(.el-table--group)::after,
:deep(.el-table::before) {
  display: none;
}

:deep(.el-table__row) {
  border-bottom: 1px solid transparent !important;
}

:deep(.el-table__row:hover) {
  background-color: #f7f7f7;
  transition: background-color 0.3s;
}

:deep(.el-table__header) {
  border-radius: 8px 8px 0 0 !important;
}

:deep(.el-table__empty-block) {
  border-radius: 0 0 8px 8px;
}

/* 新增Tab样式调整 */
.custom-tabs {
  min-width: 180px;
}

:deep(.el-tabs__nav-wrap::after) {
  /* 移除默认的底部灰线 */
  display: none !important;
}

:deep(.el-tabs__nav) {
  /* 确保导航项居中对齐 */
  display: flex;
  justify-content: center;
}

:deep(.el-tabs__item) {
  /* 调整Tab项的样式 */
  padding: 0 20px;
  height: 40px;
  line-height: 40px;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
}

:deep(.el-tabs__active-bar) {
  /* 调整活动条样式 */
  height: 2px;
  bottom: 0;
  left: 0;
  background-color: #3182ce;
}

:deep(.el-tabs__header) {
  /* 移除底部边框 */
  border-bottom: none;
  margin-bottom: 16px;
}
</style> 