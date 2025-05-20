<script setup>
import { ref } from 'vue'
import { Menu as IconMenu, Timer, Document, Setting } from '@element-plus/icons-vue'

const isCollapse = ref(false)
</script>

<template>
  <el-container class="app-container">
    <el-aside width="auto">
      <el-menu
        default-active="/"
        class="sidebar-menu"
        :collapse="isCollapse"
        :router="true"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <div class="logo-container">
          <span v-if="!isCollapse" class="logo-text">EasyJob</span>
          <el-icon v-else class="logo-icon"><Timer /></el-icon>
        </div>
        
        <el-menu-item index="/">
          <el-icon><Document /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        
        <el-menu-item index="/jobs">
          <el-icon><Timer /></el-icon>
          <template #title>任务管理</template>
        </el-menu-item>
        
        <el-menu-item index="/history">
          <el-icon> <Setting /></el-icon>
          <template #title>运行记录</template>
        </el-menu-item>
        
        <div class="collapse-btn" @click="isCollapse = !isCollapse">
          <el-icon><IconMenu /></el-icon>
        </div>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>EasyJob 任务调度平台</h2>
        </div>
      </el-header>
      
      <el-main>
        <router-view />
      </el-main>
      
      <el-footer>
        <div class="footer-content">
          <p>© {{ new Date().getFullYear() }} EasyJob 任务调度平台</p>
        </div>
      </el-footer>
    </el-container>
  </el-container>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

</style>

<style scoped>
.app-container {
  height: 100vh;
}

.el-aside {
  transition: width 0.3s;
  background-color: #304156;
}

.sidebar-menu {
  height: 100%;
  border-right: none;
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
  font-size: 20px;
  font-weight: bold;
}

.logo-text {
  margin-left: 10px;
}

.logo-icon {
  font-size: 24px;
}

.collapse-btn {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  text-align: center;
  color: #bfcbd9;
  cursor: pointer;
  padding: 10px 0;
}

.collapse-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-main {
  background-color: #f0f2f5;
  padding: 0;
  overflow-y: auto;
}

.el-footer {
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px !important;
}

.footer-content {
  color: #666;
  font-size: 14px;
}
</style>
