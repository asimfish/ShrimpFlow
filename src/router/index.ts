import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      component: () => import('@/pages/dashboard/dashboard_page.vue'),
    },
    {
      path: '/openclaw',
      component: () => import('@/pages/openclaw/openclaw_page.vue'),
    },
    {
      path: '/timeline',
      component: () => import('@/pages/timeline/timeline_page.vue'),
    },
    {
      path: '/digest',
      component: () => import('@/pages/digest/digest_page.vue'),
    },
    {
      path: '/skills',
      component: () => import('@/pages/skills/skill_tree_page.vue'),
    },
    {
      path: '/patterns',
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
      path: '/community',
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
      component: () => import('@/pages/profile/profile_page.vue'),
    },
    {
      path: '/architecture',
      component: () => import('@/pages/architecture/architecture_page.vue'),
    },
    {
      path: '/security',
      component: () => import('@/pages/security/security_page.vue'),
    },
  ],
})
