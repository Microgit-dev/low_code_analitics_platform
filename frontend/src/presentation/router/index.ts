import { createRouter, createWebHistory } from 'vue-router'
import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import PublicFormView from '../views/PublicFormView.vue'
import PublicDashboardView from '../views/PublicDashboardView.vue'
import ReportDetailView from '../views/ReportDetailView.vue'
import TableReportDetailView from '../views/TableReportDetailView.vue'
import TableReportView from '../views/TableReportView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: RegisterView, meta: { guestOnly: true } },
    { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
    {
      path: '/workspaces/:workspaceId/reports/create',
      name: 'report-create',
      component: ReportDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/workspaces/:workspaceId/reports/:reportId',
      name: 'report-detail',
      component: ReportDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/workspaces/:workspaceId/table-reports/create',
      name: 'table-report-create',
      component: TableReportDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/workspaces/:workspaceId/table-reports/:reportId',
      name: 'table-report-detail',
      component: TableReportDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/workspaces/:workspaceId/table-reports/:reportId/view',
      name: 'table-report-view',
      component: TableReportView,
      meta: { requiresAuth: true }
    },
    { path: '/form/:formId', name: 'public-form', component: PublicFormView },
    { path: '/report/:reportId', name: 'public-dashboard', component: PublicDashboardView }
  ]
})

router.beforeEach((to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const token = localStorage.getItem('low_code_token')

  if (to.meta.requiresAuth && !token) {
    next({ name: 'login' })
    return
  }

  if (to.meta.guestOnly && token) {
    next({ name: 'dashboard' })
    return
  }

  next()
})
