import { defineStore } from 'pinia'
import api from '../api'
import { ElMessage } from 'element-plus'

export const useJobStore = defineStore('jobs', {
  state: () => ({
    jobs: [],
    currentJob: null,
    jobHistory: [],
    loading: false,
    error: null
  }),
  
  getters: {
    getJobById: (state) => (id) => {
      return state.jobs.find(job => job.JobId === parseInt(id))
    }
  },
  
  actions: {
    async fetchJobs(params = {}) {
      this.loading = true
      try {
        const response = await api.getJobs(params)
        if (response.data.code === 200) {
          // 如果后端返回的是分页数据对象
          if (response.data.data && typeof response.data.data === 'object' && 'items' in response.data.data) {
            this.jobs = response.data.data.items || []
          } else if (Array.isArray(response.data.data)) {
            // 如果后端直接返回数组
            this.jobs = response.data.data
          } else {
            // 其他情况，确保jobs是数组
            this.jobs = []
          }
          return response
        } else {
          throw new Error(response.data.message || 'Failed to fetch jobs')
        }
      } catch (error) {
        this.error = error.message || 'Failed to fetch jobs'
        ElMessage.error(this.error)
        throw error // 重新抛出错误，让调用者可以处理
      } finally {
        this.loading = false
      }
    },
    
    async fetchJob(id) {
      this.loading = true
      try {
        const response = await api.getJob(id)
        if (response.data.code === 200) {
          this.currentJob = response.data.data
        } else {
          throw new Error(response.data.message || 'Failed to fetch job')
        }
      } catch (error) {
        this.error = error.message || 'Failed to fetch job'
        ElMessage.error(this.error)
      } finally {
        this.loading = false
      }
    },
    
    async createJob(job) {
      this.loading = true
      try {
        const response = await api.createJob(job)
        if (response.data.code === 200) {
          ElMessage.success('Job created successfully')
          return response.data.data
        } else {
          throw new Error(response.data.message || 'Failed to create job')
        }
      } catch (error) {
        this.error = error.message || 'Failed to create job'
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateJob(id, job) {
      this.loading = true
      try {
        const response = await api.updateJob(id, job)
        if (response.data.code === 200) {
          ElMessage.success('Job updated successfully')
          return response.data.data
        } else {
          throw new Error(response.data.message || 'Failed to update job')
        }
      } catch (error) {
        this.error = error.message || 'Failed to update job'
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async deleteJob(id) {
      this.loading = true
      try {
        const response = await api.deleteJob(id)
        if (response.data.code === 200) {
          this.jobs = this.jobs.filter(job => job.JobId !== parseInt(id))
          ElMessage.success('Job deleted successfully')
          return true
        } else {
          throw new Error(response.data.message || 'Failed to delete job')
        }
      } catch (error) {
        this.error = error.message || 'Failed to delete job'
        ElMessage.error(this.error)
        return false
      } finally {
        this.loading = false
      }
    },
    
    async runJob(id) {
      this.loading = true
      try {
        const response = await api.runJob(id)
        if (response.data.code === 200) {
          ElMessage.success('Job triggered successfully')
          return true
        } else {
          throw new Error(response.data.message || 'Failed to run job')
        }
      } catch (error) {
        this.error = error.message || 'Failed to run job'
        ElMessage.error(this.error)
        return false
      } finally {
        this.loading = false
      }
    },
    
    async fetchJobHistory(jobId, params = {}) {
      this.loading = true
      try {
        const response = await api.getJobHistory(jobId, params)
        if (response.data.code === 200) {
          // 如果后端返回的是分页数据对象
          if (response.data.data && typeof response.data.data === 'object' && 'items' in response.data.data) {
            this.jobHistory = response.data.data.items || []
          } else if (Array.isArray(response.data.data)) {
            // 如果后端直接返回数组
            this.jobHistory = response.data.data
          } else {
            // 其他情况，确保jobHistory是数组
            this.jobHistory = []
          }
          return response.data.data
        } else {
          throw new Error(response.data.message || 'Failed to fetch job history')
        }
      } catch (error) {
        this.error = error.message || 'Failed to fetch job history'
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
