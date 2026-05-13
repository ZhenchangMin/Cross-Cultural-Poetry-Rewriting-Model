//定义前端页面之间的路由（如首页和翻译结果页面）
// src/router/index.js

import { createRouter, createWebHistory } from 'vue-router'
import GenerateView from '../views/GenerateView.vue'
import AboutView from '../views/AboutView.vue'
import ChangelogView from '../views/ChangelogView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: GenerateView
  },
  {
    path: '/about',
    name: 'about',
    component: AboutView
  },
  {
    path: '/changelog',
    name: 'changelog',
    component: ChangelogView
  }
]

const router = createRouter({
history: createWebHistory(),
routes
})

export default router