<script setup>
import { ref } from 'vue'
import {
  Menu as IconMenu,
  Timer,
  Document,
  Setting,
  Fold,
  Expand
} from '@element-plus/icons-vue'

const isCollapse = ref(false)

// 菜单配置数据
const menuItems = ref([
  { index: '/', icon: Document, title: '首页' },
  { index: '/jobs', icon: Timer, title: '任务管理' },
  { index: '/history', icon: Setting, title: '运行记录' }
])

const currentYear = new Date().getFullYear()
</script>

<template>
  <el-container class="app-container">
    <el-aside width="auto">
      <div class="sidebar-container">
        <el-menu
          default-active="/"
          class="sidebar-menu"
          :collapse="isCollapse"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <div class="logo-container" @click="isCollapse = !isCollapse">
            <el-icon v-if="isCollapse" class="logo-icon">
              <Timer />
            </el-icon>
            <span v-else class="logo-text">EasyJob</span>
          </div>

          <el-menu-item
            v-for="item in menuItems"
            :key="item.index"
            :index="item.index"
          >
            <el-icon>
              <component :is="item.icon" />
            </el-icon>
            <template #title>{{ item.title }}</template>
          </el-menu-item>
        </el-menu>
      </div>
    </el-aside>

    <el-container>
      <el-header>
        <div class="header-content">
          <div class="header-left">
            <div class="collapse-btn" @click="isCollapse = !isCollapse">
              <el-icon :class="{ 'rotate-icon': isCollapse }">
                <component :is="isCollapse ? Expand : Fold" />
              </el-icon>
            </div>
          </div>

          <div class="header-center">
            <h2>EasyJob 任务调度平台</h2>
          </div>

          <div class="header-right">
            <!-- 这里可以放置用户信息或其他操作 -->
          </div>
        </div>
      </el-header>

      <el-main>
        <router-view />
      </el-main>

      <el-footer height="40px">
        <div class="footer-content">
          <p>© {{ currentYear }} EasyJob 任务调度平台</p>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
}

.el-aside {
  background-color: #304156;
  transition: width 0.3s ease;
}

.sidebar-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.3s;
}

.logo-container:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 24px;
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  height: 60px;
}

.header-content {
  display: flex;
  align-items: center;
  width: 100%;
  height: 100%;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.collapse-btn {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #5a5e66;
  transition: all 0.3s;
  padding: 6px 10px;
  border-radius: 4px;
}

.collapse-btn:hover {
  background-color: #f5f7fa;
}

.collapse-btn .el-icon {
  margin-right: 6px;
  font-size: 18px;
  transition: transform 0.3s;
}

.collapse-btn .rotate-icon {
  transform: rotate(180deg);
}

.collapse-btn span {
  font-size: 14px;
  font-weight: 500;
}

.el-main {
  background-color: #f0f2f5;
  overflow: auto;
}

.el-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  border-top: 1px solid #eaecef;
  color: #666;
  font-size: 13px;
}
</style>