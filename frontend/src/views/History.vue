<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>运行记录</h2>
        </div>
      </template>

      <!-- 搜索和过滤区域 -->
      <el-form :model="searchForm" :inline="true" class="search-form">
        <el-form-item label="任务ID">
          <el-input
            v-model="searchForm.job_id" 
            :controls="false"
            placeholder="输入任务ID" 
            clearable
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select style="width: 120px" v-model="searchForm.status" placeholder="全部状态" clearable @change="handleSearch">
            <el-option label="成功" :value="3"/>
            <el-option label="失败" :value="4"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table
          v-loading="loading"
          :data="historyList"
          style="width: 100%"
          border
          stripe
      >
        <el-table-column prop="JobId" label="任务ID" width="100"/>
        <el-table-column prop="JobName" label="任务名称"/>
        <el-table-column prop="RunId" label="运行ID" width="120"/>
        <el-table-column prop="StartTime" label="开始时间" width="180"/>
        <el-table-column prop="EndTime" label="结束时间" width="180"/>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.Status)">
              {{ getStatusText(row.Status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
                size="small"
                type="primary"
                link
                @click="showLogDetails(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container" style="margin-top: 15px">
        <el-pagination
            v-model:current-page="pagination.current_page"
            v-model:page-size="pagination.page_size"
            :page-sizes="[10, 20, 50, 100]"
            background
            layout="sizes, prev, pager, next, jumper"
            :total="pagination.total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
        />
      </div>
    </el-card>


    <!-- 日志详情对话框 -->
    <el-dialog
        v-model="logDialogVisible"
        title="执行日志详情"
        width="70%"
    >
      <pre v-if="selectedLog" class="log-output">{{ selectedLog.Output || '无日志输出' }}</pre>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="logDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const loading = ref(false)
const historyList = ref([])
const selectedLog = ref(null)
const logDialogVisible = ref(false)

// 分页
const pagination = reactive({
  current_page: 1,
  page_size: 10,
  total: 0
})

// 搜索表单
const searchForm = reactive({
  job_id: null,
  status: null
})

// 获取运行记录
const fetchHistory = async () => {
  loading.value = true
  try {
    const params = {
      current_page: pagination.current_page,
      page_size: pagination.page_size,
      job_id: searchForm.job_id || undefined,
      status: searchForm.status
    }
    
    const response = await api.getJobHistory(params.job_id || null, params)
    if (response.data?.code === 200) {
      historyList.value = response.data.data?.items || []
      pagination.total = response.data.data?.total || 0
    } else {
      throw new Error(response.data?.message || '获取运行记录失败')
    }
  } catch (error) {
    console.error('Failed to fetch history:', error)
    ElMessage.error(error.message || '获取运行记录失败')
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  pagination.current_page = 1
  fetchHistory()
}

// 重置搜索
const resetSearch = () => {
  searchForm.job_id = null
  searchForm.status = null
  handleSearch()
}

// 处理分页大小变化
const handleSizeChange = (val) => {
  pagination.page_size = val
  fetchHistory()
}

// 处理当前页变化
const handleCurrentChange = (val) => {
  pagination.current_page = val
  fetchHistory()
}

// 显示日志详情
const showLogDetails = (log) => {
  selectedLog.value = log
  logDialogVisible.value = true
}

// 获取状态类型
const getStatusType = (status) => {
  return status === 3 ? 'success' : 'danger'
}

// 获取状态文本
const getStatusText = (status) => {
  return status === 3 ? '成功' : '失败'
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-container {
  padding: 20px;
}

.search-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

.log-output {
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 60vh;
  overflow-y: auto;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-family: monospace;
  line-height: 1.5;
}
</style>