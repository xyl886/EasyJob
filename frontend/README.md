# EasyJob 前端应用

这是一个基于 Vue 3 + Vite 开发的 EasyJob 任务调度平台前端应用，用于与 FastAPI 后端进行交互，管理和监控定时任务。

## 技术栈

- Vue 3
- Vite
- Vue Router
- Pinia (状态管理)
- Element Plus (UI 组件库)
- Axios (HTTP 请求)

## 功能特性

- 任务列表展示
- 任务创建、编辑、删除
- 任务详情查看
- 任务执行历史记录
- 手动触发任务执行

## 开发环境设置

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 http://localhost:3000 上运行

### 构建生产版本

```bash
npm run build
```

## 后端接口

前端应用默认配置为通过代理连接到运行在 http://localhost:8000 的 FastAPI 后端。
如果后端运行在不同的地址，请修改 `vite.config.js` 中的代理配置。

## 项目结构

- `src/api`: API 服务调用
- `src/components`: 可复用组件
- `src/router`: 路由配置
- `src/store`: Pinia 状态管理
- `src/views`: 页面视图组件
