<template>
  <div class="job-detail-container">
    <el-card v-if="jobStore.currentJob" v-loading="jobStore.loading">
      <template #header>
        <div class="card-header">
          <h2>任务详情</h2>
          <div class="header-actions">
            <el-button
                type="primary"
                @click="runJob"
                :disabled="jobStore.currentJob?.Disabled === 1"
            >
              执行任务
            </el-button>
            <el-button
                type="warning"
                @click="$router.push(`/job/edit/${jobId}`)">
              编辑任务
            </el-button>
            <el-button @click="$router.push('/jobs')">返回列表</el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ jobStore.currentJob.JobId }}</el-descriptions-item>
        <el-descriptions-item label="任务名称">{{ jobStore.currentJob.JobName }}</el-descriptions-item>
        <el-descriptions-item label="任务类">{{ jobStore.currentJob.JobClass }}</el-descriptions-item>
        <el-descriptions-item label="包名">{{ jobStore.currentJob.Package }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="jobStore.currentJob.Disabled === 0 ? 'success' : 'danger'">
            {{ jobStore.currentJob.Disabled === 0 ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述">
          {{ jobStore.currentJob.Description || '无描述' }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="cron-section">
        <h3>Cron 表达式</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="分钟">{{ jobStore.currentJob.Minute || '*' }}</el-descriptions-item>
          <el-descriptions-item label="小时">{{ jobStore.currentJob.Hour || '*' }}</el-descriptions-item>
          <el-descriptions-item label="日">{{ jobStore.currentJob.DayOfMonth || '*' }}</el-descriptions-item>
          <el-descriptions-item label="月">{{ jobStore.currentJob.MonthOfYear || '*' }}</el-descriptions-item>
          <el-descriptions-item label="周">{{ jobStore.currentJob.DayOfWeek || '*' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="history-section">
        <h3>执行历史</h3>
        <el-table
            v-loading="jobStore.loading"
            :data="jobStore.jobHistory"
            style="width: 100%"
            border
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
      </div>
    </el-card>

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
import {ref, onMounted, computed} from 'vue'
import {useRoute} from 'vue-router'
import {useJobStore} from '../store/jobs'

const route = useRoute()
const jobStore = useJobStore()
const jobId = computed(() => parseInt(route.params.id))
const logDialogVisible = ref(false)
const selectedLog = ref(null)

const getStatusType = (status) => {
  switch (status) {
    case 0:
      return 'danger'
    case 1:
      return 'success'
    case 2:
      return 'warning'
    case 3:
      return 'success'
    case 4:
      return 'danger'
    default:
      return 'info'
  }
}

const runJob = async () => {
  await jobStore.runJob(jobId.value)
  // Refresh history after running the job
  setTimeout(() => {
    jobStore.fetchJobHistory(jobId.value)
  }, 1000)
}

const showLogDetails = (log) => {
  selectedLog.value = log
  logDialogVisible.value = true
}

onMounted(async () => {
  await jobStore.fetchJob(jobId.value)
  await jobStore.fetchJobHistory(jobId.value)
})
</script>

<style scoped>
.job-detail-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.cron-section, .history-section {
  margin-top: 20px;
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
