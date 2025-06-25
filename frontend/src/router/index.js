import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/jobs',
    name: 'Jobs',
    component: () => import('../views/Jobs.vue')
  },
  {
    path: '/job/:id',
    name: 'JobDetail',
    component: () => import('../views/JobDetail.vue')
  },
  {
    path: '/job/create',
    name: 'CreateJob',
    component: () => import('../views/JobForm.vue')
  },
    {
    path: '/history',
    name: 'JobHistory',
    component: () => import('../views/History.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
