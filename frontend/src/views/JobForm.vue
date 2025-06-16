<template>
  <div class="job-form-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>{{ isEdit ? '编辑任务' : '创建任务' }}</h2>
          <el-button @click="$router.push('/jobs')">返回列表</el-button>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="jobForm"
        :rules="rules"
        label-width="120px"
        v-loading="jobStore.loading"
      >
        <el-form-item label="任务ID" prop="JobId">
          <el-input-number
            v-model="jobForm.JobId"
            :min="100000"
            :max="999999"
            :disabled="isEdit"
          />
          <div class="form-help">6位数字ID，范围100000-9999999</div>
        </el-form-item>

        <el-form-item label="任务名称" prop="JobName">
          <el-input v-model="jobForm.JobName" />
        </el-form-item>

        <el-form-item label="任务类" prop="JobClass">
          <el-input v-model="jobForm.JobClass" />
          <div class="form-help">任务对应的类名</div>
        </el-form-item>

        <el-form-item label="包名" prop="Package">
          <el-input v-model="jobForm.Package" />
          <div class="form-help">任务所在的包名，例如：Job.MyTask</div>
        </el-form-item>

        <el-form-item label="描述" prop="Description">
          <el-input v-model="jobForm.Description" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item label="状态" prop="Disabled">
          <el-radio-group v-model="jobForm.Disabled">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分钟" prop="Minute">
          <el-input v-model="jobForm.Minute" />
          <div class="form-help">例如：*/5 表示每5分钟，0-30 表示0到30分钟，留空表示每分钟</div>
        </el-form-item>

        <el-form-item label="小时" prop="Hour">
          <el-input v-model="jobForm.Hour" />
          <div class="form-help">例如：9-17 表示上午9点到下午5点，*/2 表示每2小时</div>
        </el-form-item>

        <el-form-item label="日" prop="DayOfMonth">
          <el-input v-model="jobForm.DayOfMonth" />
          <div class="form-help">例如：1,15 表示每月1号和15号</div>
        </el-form-item>

        <el-form-item label="月" prop="MonthOfYear">
          <el-input v-model="jobForm.MonthOfYear" />
          <div class="form-help">例如：1-6 表示1月到6月</div>
        </el-form-item>

        <el-form-item label="周" prop="DayOfWeek">
          <el-input v-model="jobForm.DayOfWeek" />
          <div class="form-help">例如：1-5 表示周一到周五，6,0 表示周六和周日</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm">保存</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJobStore } from '../store/jobs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()
const formRef = ref(null)

const isEdit = computed(() => route.path.includes('/edit/'))
const jobId = computed(() => isEdit.value ? parseInt(route.params.id) : null)

// 默认的表单数据
const defaultFormData = {
  JobId: 100000,
  JobName: '',
  JobClass: '',
  Package: '',
  Description: '',
  Disabled: 0,
  Minute: '0',
  Hour: '0',
  DayOfMonth: '*',
  MonthOfYear: '*',
  DayOfWeek: '?'
}

// Form data
const jobForm = reactive({ ...defaultFormData })

// Form validation rules
const rules = reactive({
  JobId: [
    { required: true, message: '请输入任务ID', trigger: 'blur' },
    { type: 'number', min: 100000, max: 9999999, message: '任务ID必须是6位数字', trigger: 'blur' }
  ],
  JobName: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在2到50个字符', trigger: 'blur' }
  ],
  JobClass: [
    { required: true, message: '请输入任务类名', trigger: 'blur' },
    { pattern: /^[A-Za-z][A-Za-z0-9_]*$/, message: '类名只能包含字母、数字和下划线，且不能以数字开头', trigger: 'blur' }
  ],
  Package: [
    { required: true, message: '请输入包名', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*[a-z0-9_]*$/, message: '包名格式不正确', trigger: 'blur' }
  ],
  Minute: [
    { pattern: /^(\*|\?|(\*\/)?[0-5]?[0-9](-[0-5]?[0-9])?(,[0-5]?[0-9](-[0-5]?[0-9])?)*|([0-5]?[0-9]-[0-5]?[0-9])(\/[0-9]+)?(,([0-5]?[0-9]-[0-5]?[0-9])(\/[0-9]+)?)*)$/,
      message: '分钟格式不正确',
      trigger: 'blur'
    }
  ],
  Hour: [
    { pattern: /^(\*|\?|(\*\/)?([0-9]|[0-1][0-9]|2[0-3])(-([0-9]|[0-1][0-9]|2[0-3]))?(,([0-9]|[0-1][0-9]|2[0-3])(-([0-9]|[0-1][0-9]|2[0-3]))?)*|(([0-9]|[0-1][0-9]|2[0-3])-([0-9]|[0-1][0-9]|2[0-3]))(\/[0-9]+)?(,(([0-9]|[0-1][0-9]|2[0-3])-([0-9]|[0-1][0-9]|2[0-3]))(\/[0-9]+)?)*)$/,
      message: '小时格式不正确',
      trigger: 'blur'
    }
  ],
  DayOfMonth: [
    { pattern: /^(\*|\?|(\*\/)?([1-9]|[12][0-9]|3[01])(-([1-9]|[12][0-9]|3[01]))?(,([1-9]|[12][0-9]|3[01])(-([1-9]|[12][0-9]|3[01]))?)*|(([1-9]|[12][0-9]|3[01])-([1-9]|[12][0-9]|3[01]))(\/[0-9]+)?(,(([1-9]|[12][0-9]|3[01])-([1-9]|[12][0-9]|3[01]))(\/[0-9]+)?)*|L|LW|([1-9]L)|(L-[0-9]+))$/,
      message: '日期格式不正确',
      trigger: 'blur'
    }
  ],
  MonthOfYear: [
    { pattern: /^(\*|(\*\/)?([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(-([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))?(,([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(-([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))?)*|(([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))(\/[0-9]+)?(,(([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-([1-9]|1[0-2]|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))(\/[0-9]+)?)*)$/i,
      message: '月份格式不正确',
      trigger: 'blur'
    }
  ],
  DayOfWeek: [
    { pattern: /^(\*|\?|(\*\/)?([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)(-([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT))?(,([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)(-([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT))?)*|(([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)-([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT))(\/[0-9]+)?(,(([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT)-([0-6]|SUN|MON|TUE|WED|THU|FRI|SAT))(\/[0-9]+)?)*|([0-6]L)|([0-6]#[1-5])|(L-?[0-6]?))$/i,
      message: '星期格式不正确',
      trigger: 'blur'
    }
  ]
})

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    // 准备提交的数据
    const submitData = { ...jobForm }

    // 如果ID是默认值且是创建操作，则删除ID让后端自动生成
    if (!isEdit.value && submitData.JobId === defaultFormData.JobId) {
      delete submitData.JobId
    }

    // 调用API
    if (isEdit.value) {
      await jobStore.updateJob(jobId.value, submitData)
    } else {
      await jobStore.createJob(submitData)
    }

    // 显示成功消息
    ElMessage.success(isEdit.value ? '任务更新成功' : '任务创建成功')

    // 返回任务列表
    router.push('/jobs')
  } catch (error) {
    if (error && error.fields) {
      // 验证错误，已在UI中显示
      console.error('表单验证失败:', error.fields)
    } else {
      // 其他错误，显示错误消息
      const errorMsg = error.response?.data?.message || error.message || '操作失败，请重试'
      ElMessage.error(errorMsg)
    }
  }
}

// 重置表单
const resetForm = () => {
  if (!formRef.value) return

  // 重置为默认值
  Object.assign(jobForm, defaultFormData)

  // 如果是编辑模式，保留当前ID
  if (isEdit.value && jobId.value) {
    jobForm.JobId = jobId.value
  }

  // 清除验证状态
  formRef.value.clearValidate()
}

// 加载任务数据（如果是编辑模式）
onMounted(async () => {
  if (isEdit.value && jobId.value) {
    try {
      const response = await jobStore.fetchJob(jobId.value)
      if (response?.data?.data) {
        const jobData = response.data.data
        // 只更新存在的字段
        Object.keys(defaultFormData).forEach(key => {
          if (jobData[key] !== undefined) {
            jobForm[key] = jobData[key]
          }
        })
      }
    } catch (error) {
      ElMessage.error(error.message || '加载任务数据失败')
      // 加载失败后返回列表
      router.push('/jobs')
    }
  } else {
    // 创建新任务时，设置默认值
    resetForm()
  }
})
</script>

<style scoped>
.job-form-container {
  padding: 10px;
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  line-height: 1.4;
}

.el-form-item {
  margin-bottom: 18px;
}

.el-divider {
  margin: 10px 0;
}

.form-actions {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.form-actions .el-button {
  min-width: 100px;
  margin: 0 10px;
}
</style>
