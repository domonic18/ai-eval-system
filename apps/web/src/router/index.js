import { createRouter, createWebHistory } from 'vue-router'
import store from '@/store'

// 路由定义
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/evaluation-results',
    name: 'evaluation-results',
    component: () => import('@/views/EvaluationResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/guide',
    name: 'guide',
    component: () => import('@/views/GuideView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/evaluation',
    name: 'evaluation',
    component: () => import('../views/EvaluationView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/evaluation/records',
    name: 'evaluationRecords',
    component: () => import('../views/EvaluationView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/evaluation/history',
    redirect: '/evaluation/records'
  },
  {
    path: '/evaluation/datasets',
    redirect: '/evaluation'
  },
  {
    path: '/evaluation/datasets/upload',
    redirect: '/evaluation'
  },
  {
    path: '/arena',
    name: 'arena',
    component: () => import('@/views/ArenaView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true }
  },
  // 捕获所有未匹配的路由并重定向到首页
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { x: 0, y: 0 }
  }
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 获取目标路由是否需要认证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  
  // 判断当前是否已登录
  const isAuthenticated = store.getters['auth/isAuthenticated']
  
  console.log('路由守卫检查:', { 
    路径: to.path, 
    需要认证: requiresAuth, 
    已认证: isAuthenticated,
    token存在: !!localStorage.getItem('token')
  })

  // 需要认证但未登录，重定向到登录页
  if (requiresAuth && !isAuthenticated) {
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } 
  // 已登录但访问登录/注册页，重定向到首页
  else if (isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    next('/')
  }
  // 其他情况正常通过
  else {
    next()
  }
})

export default router 