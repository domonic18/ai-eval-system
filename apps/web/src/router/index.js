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

// 优化全局前置守卫
router.beforeEach((to, from, next) => {
  // 获取目标路由是否需要认证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isGuestOnly = to.matched.some(record => record.meta.guest)
  
  // 统一使用isAuthenticated
  const isAuthenticated = store.getters['auth/isAuthenticated']
  
  // 为调试添加详细日志
  console.log('路由导航:', { 
    从: from.path,
    到: to.path, 
    需要认证: requiresAuth,
    仅游客: isGuestOnly,
    已认证: isAuthenticated,
    token: store.state.auth.token?.substring(0, 10) + '...'
  })

  // 路由逻辑处理
  if (requiresAuth && !isAuthenticated) {
    // 需要认证但未登录
    console.log('拦截访问，重定向到登录页');
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else if (isGuestOnly && isAuthenticated) {
    // 已登录用户访问仅限游客页面(如登录页)
    console.log('已登录用户试图访问登录页，重定向到首页');
    next('/')
  } else {
    // 其他情况正常通过
    console.log('允许路由导航');
    next()
  }
})

export default router 