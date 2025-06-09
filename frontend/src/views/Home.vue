<template>
  <div class="home">
    <el-row :gutter="20" justify="center">
      <el-col :span="18">
        <el-card class="welcome-card">
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
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="总任务数" :value="jobStats.total">
                <template #suffix>
                  <el-icon>
                    <Calendar/>
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="运行中" :value="jobStats.active">
                <template #suffix>
                  <el-icon>
                    <Loading/>
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="已禁用" :value="jobStats.disabled">
                <template #suffix>
                  <el-icon>
                    <CircleClose/>
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>

        <el-card class="chart-card" v-if="jobStore.statistics.length > 0">
          <div ref="chart" style="height: 400px; width: 100%;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import {onMounted, ref, computed, onUnmounted, watchEffect, nextTick} from 'vue'
import {useJobStore} from '../store/jobs'
import {Calendar, Loading, CircleClose} from '@element-plus/icons-vue'
import * as echarts from 'echarts' // 导入 ECharts

const jobStore = useJobStore()
const chart = ref(null) // 图表 DOM 引用
let chartInstance = null // ECharts 实例

// Job statistics
const jobStats = computed(() => {
  const total = jobStore.jobsTotal
  const disabled = jobStore.disabled
  const active = jobStore.running

  return {
    total,
    active,
    disabled,
  }
})
// 当统计数据变化时渲染图表
watchEffect(() => {
  if (jobStore.statistics.length > 0 && chart.value) {
    renderChart()
  }
})
// 渲染图表函数
const renderChart = () => {
  // 确保 DOM 已渲染
  nextTick(() => {
    if (!chartInstance) {
      chartInstance = echarts.init(chart.value)
    }

    // 准备图表数据
    const dates = jobStore.statistics.map(item => item.date)
    const successData = jobStore.statistics.map(item => item.success)
    const failureData = jobStore.statistics.map(item => item.failure)
    const runningData = jobStore.statistics.map(item => item.running)

    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: function (params) {
          let result = params[0].name + '<br/>'
          params.forEach(param => {
            result += `${param.marker} ${param.seriesName}: ${param.value}<br/>`
          })
          return result
        }
      },
      legend: {
        data: ['成功', '失败', '运行中'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          rotate: 45 // 如果日期太多旋转45度避免重叠
        }
      },
      yAxis: {
        type: 'value',
        name: '任务数量'
      },
      series: [
        {
          name: '成功',
          type: 'line',
          data: successData,
          smooth: true,
          lineStyle: {
            width: 3
          },
          itemStyle: {
            color: '#67C23A' // 绿色代表成功
          }
        },
        {
          name: '失败',
          type: 'line',
          data: failureData,
          smooth: true,
          lineStyle: {
            width: 3
          },
          itemStyle: {
            color: '#F56C6C' // 红色代表失败
          }
        },
        {
          name: '运行中',
          type: 'line',
          data: runningData,
          smooth: true,
          lineStyle: {
            width: 3,
            type: 'dashed' // 虚线表示运行中
          },
          itemStyle: {
            color: '#409EFF' // 蓝色代表运行中
          }
        }
      ],
    }

    chartInstance.setOption(option)

    // 响应窗口大小变化
    window.addEventListener('resize', () => {
      chartInstance.resize()
    })
  })
}
onMounted(async () => {
  await jobStore.fetchJobs()
  await jobStore.fetchStatistics()

})
// 组件卸载时销毁图表
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>

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

.chart-card {
  margin-top: 20px;
}
</style>
