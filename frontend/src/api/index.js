import axios from 'axios'

// Get the current hostname and port for dynamic configuration
const isDevelopment = import.meta.env.DEV
const baseURL = isDevelopment ? 'http://localhost:8000' : window.location.origin

const apiClient = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    withCredentials: true // Enable sending cookies in cross-origin requests
})

// Add response interceptor to handle common errors
apiClient.interceptors.response.use(
    response => {
        // 确保响应数据符合Result格式
        if (response.data && typeof response.data === 'object') {
            if (response.data.code === undefined) {
                response.data = {
                    code: 200,
                    message: 'success',
                    data: response.data
                }
            }
        }
        return response
    },
    error => {
        console.error('API Error:', error)
        // 处理HTTP错误
        if (error.response) {
            const {status, data} = error.response
            error.message = data?.message || `Request failed with status code ${status}`
            error.code = status
        }
        return Promise.reject(error)
    }
)

/**
 * 构建查询参数
 * @param {Object} params 参数对象
 * @returns {string} 查询参数字符串
 */
const buildQueryString = (params) => {
    if (!params) return ''
    const query = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null && value !== '')
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&')
    return query ? `?${query}` : ''
}

export default {
    getStatistics() {
        return apiClient.get('/statistics')
    },
    // Job CRUD operations
    getJobs(params = {}) {
        // 确保分页参数存在
        const defaultParams = {
            current_page: 1,
            page_size: 10,
            ...params
        }
        return apiClient.get(`/jobs/${buildQueryString(defaultParams)}`)
    },

    getJob(id) {
        return apiClient.get(`/jobs/${id}`)
    },

    createJob(job) {
        return apiClient.post('/jobs/', job)
    },

    updateJob(id, job) {
        return apiClient.put(`/jobs/${id}`, job)
    },

    deleteJob(id) {
        return apiClient.delete(`/jobs/${id}`)
    },

    // Job execution
    runJob(id) {
        return apiClient.post(`/jobs/${id}/run`)
    },

    // Job history
    getJobHistory(jobId, params = {}) {
        const defaultParams = {
            current_page: 1,
            page_size: 10,
            ...params
        }
        if (!jobId) {
            return apiClient.get(`/history${buildQueryString(defaultParams)}`)
        }
        return apiClient.get(`/jobs/${jobId}/history${buildQueryString(defaultParams)}`)
    }
}
