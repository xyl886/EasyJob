<template>
  <div class="jobs-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>任务列表</h2>
          <el-button type="primary" @click="openJobDialog()">创建任务</el-button>
        </div>
      </template>

      <!-- 搜索和过滤区域 -->
      <el-form :model="searchForm" :inline="true" class="search-form">
        <el-form-item label="任务名称">
          <el-input v-model="searchForm.job_name" placeholder="输入任务名称" clearable @clear="handleSearch"/>
        </el-form-item>
        <el-form-item label="状态" >
          <el-select style="width: 120px" v-model="searchForm.status" placeholder="全部状态" clearable @change="handleSearch">
            <el-option label="启用" :value="0"/>
            <el-option label="禁用" :value="1"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table
          v-loading="jobStore.loading"
          :data="jobStore.jobs"
          style="width: 100%"
          border
          stripe
      >
        <el-table-column prop="JobId" label="任务ID" width="100"/>
        <el-table-column prop="JobName" label="任务名称"/>
        <el-table-column prop="JobClass" label="任务类"/>
        <el-table-column prop="Package" label="包名"/>
        <el-table-column label="Cron表达式" width="200">
          <template #default="{ row }">
            {{ formatCronExpression(row) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.Disabled === 0 ? 'success' : 'danger'">
              {{ row.Disabled === 0 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320">
          <template #default="{ row }">
            <el-button
                size="small"
                type="primary"
                @click="runJob(row.JobId)"
                :disabled="row.Disabled === 1"
            >
              执行
            </el-button>
            <el-button
                size="small"
                @click="viewJobDetail(row.JobId)"
            >
              详情
            </el-button>
            <el-button
                size="small"
                type="warning"
                @click="openJobDialog(row)"
            >
              编辑
            </el-button>
<!--            <el-button-->
<!--                size="small"-->
<!--                type="info"-->
<!--                @click="viewRunRecords(row)"-->
<!--            >-->
<!--              记录-->
<!--            </el-button>-->
            <el-button
                size="small"
                type="danger"
                @click="confirmDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
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

    <!-- 任务表单对话框 -->
    <el-dialog
        v-model="jobDialogVisible"
        :title="isEdit ? '编辑任务' : '创建任务'"
        width="60%"
        destroy-on-close
    >
      <job-form
          :job-data="currentJob"
          :is-edit="isEdit"
          @submit="handleJobSubmit"
          @cancel="jobDialogVisible = false"
      />
    </el-dialog>

    <!-- 运行记录对话框 -->
    <el-dialog
        v-model="recordsDialogVisible"
        title="任务运行记录"
        width="70%"
    >
      <div v-if="selectedJob" class="job-info">
        <h3>{{ selectedJob.JobName }} <small>(ID: {{ selectedJob.JobId }})</small></h3>
      </div>

      <el-table
          v-loading="jobStore.loading"
          :data="jobStore.jobHistory.items || jobStore.jobHistory"
          style="width: 100%; margin-top: 15px"
          border
          v-if="recordsDialogVisible"
      >
        <el-table-column prop="RunId" label="运行ID" width="100"/>
        <el-table-column prop="StartTime" label="开始时间"/>
        <el-table-column prop="EndTime" label="结束时间"/>
        <el-table-column prop="Status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.Status)">{{ row.Status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
                size="small"
                type="primary"
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
            v-model:current-page="historyPagination.current_page"
            v-model:page-size="historyPagination.page_size"
            :page-sizes="[10, 20, 50, 100]"
            background
            layout="sizes, prev, pager, next, jumper"
            :total="historyPagination.total"
            @size-change="handleHistorySizeChange"
            @current-change="handleHistoryPageChange"
        />
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="recordsDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

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
import {ref, reactive, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {useJobStore} from '../store/jobs'
import {ElMessage, ElMessageBox} from 'element-plus'
import JobForm from '../components/JobForm.vue'

const router = useRouter()
const jobStore = useJobStore()

// 分页
const pagination = reactive({
  current_page: 1,
  page_size: 10,
  total: 0
})

// 搜索表单
const searchForm = reactive({
  job_name: '',
  status: null
})

// Dialog visibility states
const jobDialogVisible = ref(false)
const recordsDialogVisible = ref(false)
const logDialogVisible = ref(false)

// Current data for dialogs
const currentJob = ref(null)
const isEdit = ref(false)
const selectedJob = ref(null)
const selectedLog = ref(null)

// Format cron expression for display
const formatCronExpression = (job) => {
  const parts = []
  if (job.Minute) parts.push(`分钟: ${job.Minute}`)
  if (job.Hour) parts.push(`小时: ${job.Hour}`)
  if (job.DayOfMonth) parts.push(`日: ${job.DayOfMonth}`)
  if (job.MonthOfYear) parts.push(`月: ${job.MonthOfYear}`)
  if (job.DayOfWeek) parts.push(`周: ${job.DayOfWeek}`)

  return parts.length > 0 ? parts.join(', ') : '无调度'
}

// 处理分页大小变化
const handleSizeChange = (val) => {
  pagination.page_size = val
  fetchJobs()
}

// 处理当前页变化
const handleCurrentChange = (val) => {
  pagination.current_page = val
  fetchJobs()
}

// 处理搜索
const handleSearch = () => {
  pagination.current_page = 1 // 重置为第一页
  fetchJobs()
}

// 重置搜索
const resetSearch = () => {
  searchForm.job_name = ''
  searchForm.status = null
  handleSearch()
}

// 获取任务列表
const fetchJobs = async () => {
  try {
    const params = {
      current_page: pagination.current_page,
      page_size: pagination.page_size,
      job_name: searchForm.job_name || undefined,
      status: searchForm.status
    }
    console.log('fetchJobs params', params)
    
    const response = await jobStore.fetchJobs(params)
    console.log('fetchJobs response:', response)
    
    // 处理后端返回的数据
    if (response?.data) {
      // 如果后端返回了分页信息，则使用后端的数据
      if (response.data.data && typeof response.data.data === 'object' && 'total' in response.data.data) {
        pagination.total = response.data.data.total || 0
      } else {
        // 如果后端没有返回分页信息，则根据返回的数组长度来判断
        const items = Array.isArray(response.data.data) ? response.data.data : []
        if (items.length > 0) {
          // 如果有数据且是第一页，假设还有更多数据
          if (pagination.current_page === 1) {
            pagination.total = items.length < pagination.page_size ? items.length : items.length + 1
          } else {
            // 如果不是第一页，假设还有更多数据
            pagination.total = (pagination.current_page - 1) * pagination.page_size + items.length + 1
          }
        } else {
          // 如果没有数据，重置为0
          pagination.total = 0
        }
      }
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error(error.message || '获取任务列表失败')
  }
}

// Run a job
const runJob = async (jobId) => {
  try {
    const success = await jobStore.runJob(jobId)
    if (success) {
      ElMessage.success('任务已触发执行')
    }
  } catch (error) {
    ElMessage.error(error.message || '触发任务执行失败')
  }
}
// Open job form dialog
const openJobDialog = (job = null) => {
  if (job) {
    currentJob.value = {...job}
    isEdit.value = true
  } else {
    currentJob.value = {
      JobId: 100000,
      JobName: '',
      JobClass: '',
      Package: '',
      Description: '',
      Disabled: 0,
      Minute: '',
      Hour: '',
      DayOfMonth: '',
      MonthOfYear: '',
      DayOfWeek: '',
      Status: 1
    }
    isEdit.value = false
  }
  jobDialogVisible.value = true
}

// Handle job form submission
const handleJobSubmit = async (formData) => {
  try {
    if (isEdit.value) {
      await jobStore.updateJob(formData.JobId, formData)
    } else {
      await jobStore.createJob(formData)
    }
    jobDialogVisible.value = false
    await jobStore.fetchJobs()
  } catch (error) {
    // Error is already handled in the store
  }
}

// View job details
const viewJobDetail = (jobId) => {
  router.push(`/job/${jobId}`)
}

// 分页参数
const historyPagination = reactive({
  current_page: 1,
  page_size: 10,
  total: 0
})

// 重置分页参数
const resetHistoryPagination = () => {
  historyPagination.current_page = 1
  historyPagination.page_size = 10
  historyPagination.total = 0
}

// 处理分页大小变化
const handleHistorySizeChange = (val) => {
  historyPagination.page_size = val
  viewRunRecords(selectedJob.value)
}

// 处理当前页变化
const handleHistoryPageChange = (val) => {
  historyPagination.current_page = val
  viewRunRecords(selectedJob.value)
}

// View run records
const viewRunRecords = async (job) => {
  try {
    selectedJob.value = job
    resetHistoryPagination()
    await jobStore.fetchJobHistory(job.JobId, {
      current_page: historyPagination.current_page,
      page_size: historyPagination.page_size
    })
    // 更新分页总数
    if (jobStore.jobHistory && jobStore.jobHistory.total !== undefined) {
      historyPagination.total = jobStore.jobHistory.total
    }
    recordsDialogVisible.value = true
  } catch (error) {
    console.error('Failed to fetch job history:', error)
    ElMessage.error('获取任务记录失败：' + (error.message || '未知错误'))
  }
}

// Show log details
const showLogDetails = (log) => {
  selectedLog.value = log
  logDialogVisible.value = true
}

// Get status type for tag color
const getStatusType = (status) => {
  switch (status?.toLowerCase()) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'running':
      return 'warning'
    default:
      return 'info'
  }
}

// Delete a job with confirmation
const confirmDelete = (job) => {
  ElMessageBox.confirm(
      `确定要删除任务 "${job.JobName}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
  )
      .then(async () => {
        await jobStore.deleteJob(job.JobId)
      })
      .catch(() => {
        // User canceled deletion
      })
}

onMounted(() => {
  fetchJobs()
})

</script>

<style scoped>
.search-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.job-actions button {
  margin-right: 8px;
  margin-bottom: 5px;
}

.jobs-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.job-info {
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 15px;
  margin-bottom: 15px;
}

.log-output {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: monospace;
  max-height: 400px;
  overflow-y: auto;
}
</style>
