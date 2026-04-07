import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      meta: { keepAlive: true },
      component: () => import('@/pages/dashboard/dashboard_page.vue'),
    },
    {
      path: '/openclaw',
      name: 'openclaw',
      meta: { keepAlive: true },
      component: () => import('@/pages/openclaw/openclaw_page.vue'),
    },
    {
      path: '/timeline',
      name: 'timeline',
      meta: { keepAlive: true },
      component: () => import('@/pages/timeline/timeline_page.vue'),
    },
    {
      path: '/digest',
      name: 'digest',
      meta: { keepAlive: true },
      component: () => import('@/pages/digest/digest_page.vue'),
    },
    {
      path: '/skills',
      name: 'skills',
      meta: { keepAlive: true },
      component: () => import('@/pages/skills/skill_tree_page.vue'),
    },
    {
      path: '/patterns',
      name: 'patterns',
      meta: { keepAlive: true },
      component: () => import('@/pages/patterns/patterns_page.vue'),
    },
    {
      path: '/patterns/:id',
      component: () => import('@/pages/patterns/pattern_detail_page.vue'),
    },
    {
      path: '/workflows/:id',
      component: () => import('@/pages/patterns/workflow_detail_page.vue'),
    },
    {
      path: '/memory',
      name: 'memory',
      meta: { keepAlive: true },
      component: () => import('@/pages/memory/memory_page.vue'),
    },
    {
      path: '/twin',
      name: 'twin',
      meta: { keepAlive: true },
      component: () => import('@/pages/twin/twin_page.vue'),
    },
    {
      path: '/community',
      name: 'community',
      meta: { keepAlive: true },
      component: () => import('@/pages/community/community_page.vue'),
    },
    {
      path: '/layer/shadow',
      component: () => import('@/pages/layers/shadow_page.vue'),
    },
    {
      path: '/layer/mirror',
      component: () => import('@/pages/layers/mirror_page.vue'),
    },
    {
      path: '/layer/brain',
      component: () => import('@/pages/layers/brain_page.vue'),
    },
    {
      path: '/layer/autopilot',
      component: () => import('@/pages/layers/autopilot_page.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      meta: { keepAlive: true },
      component: () => import('@/pages/profile/profile_page.vue'),
    },
    {
      path: '/workprint',
      name: 'workprint',
      meta: { keepAlive: true },
      component: () => import('@/pages/workprint/workprint_page.vue'),
    },
    {
      path: '/architecture',
      component: () => import('@/pages/architecture/architecture_page.vue'),
    },
    {
      path: '/security',
      component: () => import('@/pages/security/security_page.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard',
    },
  ],
})
