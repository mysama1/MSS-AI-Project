import { NavGroup } from '@/types';

export const navGroups: NavGroup[] = [
  {
    label: 'mssclaw',
    items: [
      { title: 'Dashboard', url: '/dashboard/overview', icon: 'dashboard', shortcut: ['d', 'd'], isActive: false, items: [] },
      { title: 'Chat', url: '/dashboard/chat', icon: 'chat', shortcut: ['c', 'c'], isActive: false, items: [] },
      { title: 'Users', url: '/dashboard/users', icon: 'teams', shortcut: ['u', 'u'], isActive: false, items: [] },
      { title: 'Product', url: '/dashboard/product', icon: 'product', shortcut: ['p', 'p'], isActive: false, items: [] },
      { title: 'Kanban', url: '/dashboard/kanban', icon: 'kanban', shortcut: ['k', 'k'], isActive: false, items: [] },
    ],
  },
  {
    label: 'Elements',
    items: [
      {
        title: 'Forms', url: '#', icon: 'forms', isActive: true,
        items: [
          { title: 'Basic Form', url: '/dashboard/forms/basic', icon: 'forms', shortcut: ['f', 'f'] },
          { title: 'Multi-Step', url: '/dashboard/forms/multi-step', icon: 'forms' },
        ],
      },
      { title: 'React Query', url: '/dashboard/react-query', icon: 'code', isActive: false, items: [] },
    ],
  },
  {
    label: '',
    items: [
      { title: 'Profile', url: '/dashboard/profile', icon: 'profile', shortcut: ['m', 'm'], isActive: false, items: [] },
      { title: 'Notifications', url: '/dashboard/notifications', icon: 'notification', shortcut: ['n', 'n'], isActive: false, items: [] },
    ],
  },
];
