import { createRouter, createWebHistory } from 'vue-router'
import { useStore } from 'vuex'

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

// 导航守卫
router.beforeEach((to, from, next) => {
  // 在Vue 3中，我们需要在组件内部使用useStore，但在路由守卫中需要直接引入
  const store = import.meta.hot ? useStore() : require('@/store').default
  const isLoggedIn = store.getters['auth/isLoggedIn']
  
  // 需要登录的路由
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isLoggedIn) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    } else {
      next()
    }
  } 
  // 只有未登录用户可以访问的路由（如登录页）
  else if (to.matched.some(record => record.meta.guest)) {
    if (isLoggedIn) {
      next('/')
    } else {
      next()
    }
  } 
  // 其他路由
  else {
    next()
  }
})

export default router 