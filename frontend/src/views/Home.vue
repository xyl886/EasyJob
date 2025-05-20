<template>
  <div class="home">
    <el-row :gutter="20" justify="center">
      <el-col :span="18">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <h1>EasyJob Scheduler</h1>
            </div>
          </template>
          <div class="card-content">
            <p>欢迎使用 EasyJob 任务调度平台</p>
            <p>这是一个基于 FastAPI 的任务调度系统，可以帮助您管理和执行各种定时任务。</p>
            <el-row class="action-buttons" justify="center">
              <el-button type="primary" @click="$router.push('/jobs')">查看所有任务</el-button>
              <el-button type="success" @click="$router.push('/job/create')">创建新任务</el-button>
            </el-row>
          </div>
        </el-card>
        
        <el-card class="stats-card" v-if="jobStats.total > 0">
          <template #header>
            <div class="card-header">
              <h2>任务统计</h2>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="总任务数" :value="jobStats.total">
                <template #suffix>
                  <el-icon><Calendar /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="运行中" :value="jobStats.active">
                <template #suffix>
                  <el-icon><Loading /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已禁用" :value="jobStats.disabled">
                <template #suffix>
                  <el-icon><CircleClose /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useJobStore } from '../store/jobs'
import { Calendar, Loading, CircleClose } from '@element-plus/icons-vue'

const jobStore = useJobStore()

// Job statistics
const jobStats = computed(() => {
  const total = jobStore.jobs.length
  const disabled = jobStore.jobs.filter(job => job.Disabled === 1).length
  const active = total - disabled
  
  return {
    total,
    active,
    disabled
  }
})

onMounted(async () => {
  await jobStore.fetchJobs()
})
</script>

<style scoped>
.home {
  padding: 20px;
}

.welcome-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  text-align: center;
  padding: 20px 0;
}

.action-buttons {
  margin-top: 20px;
}

.action-buttons .el-button {
  margin: 0 10px;
}

.stats-card {
  margin-top: 20px;
}
</style>
