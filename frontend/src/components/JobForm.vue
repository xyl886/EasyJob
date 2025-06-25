<template>
  <el-form
    ref="formRef"
    :model="jobForm"
    :rules="rules"
    label-width="120px"
    v-loading="loading"
  >
    <el-form-item label="任务ID" prop="JobId">
      <el-input-number 
        v-model="jobForm.JobId"
        :disabled="isEdit"
      />
      <div class="form-help">6位数字ID，范围100000-999999</div>
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
    
    <el-divider>Cron 表达式设置</el-divider>
    
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
      <el-button @click="cancel">取消</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, reactive, onMounted, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  jobData: {
    type: Object,
    required: true
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit', 'cancel'])
const formRef = ref(null)
const loading = ref(false)

// Form data
const jobForm = reactive({
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
})

// Form validation rules
const rules = reactive({
  JobId: [
    { required: true, message: '请输入任务ID', trigger: 'blur' },
    { type: 'number', min: 100000, max: 9999999, message: '任务ID必须是6-7位数字', trigger: 'blur' }
  ],
  JobName: [
    { required: true, message: '请输入任务名称', trigger: 'blur' }
  ],
  JobClass: [
    { required: true, message: '请输入任务类名', trigger: 'blur' }
  ],
  Package: [
    { required: true, message: '请输入包名', trigger: 'blur' }
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

// Submit form
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true
        emit('submit', { ...jobForm })
      } catch (error) {
        ElMessage.error('提交表单时发生错误')
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.error('表单验证失败，请检查输入')
    }
  })
}

// Cancel form
const cancel = () => {
  emit('cancel')
}

// Initialize form data
onMounted(() => {
  if (props.jobData) {
    // console.log('props.jobData', props.jobData)
    Object.assign(jobForm, props.jobData)
  }
})
</script>

<style scoped>
.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
