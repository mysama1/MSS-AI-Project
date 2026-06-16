import { useMemo } from 'react';
import type { NavItem, NavGroup } from '@/types';
import { navGroups } from '@/config/nav-config';

export function useFilteredNavItems(items: NavItem[]) {
  const user = null;
  const organization = null;

  const accessContext = useMemo(() => ({
    permissions: [],
    role: null,
    plan: 'free',
    features: [],
  }), []);

  return useMemo(() => {
    return items.filter((item) => {
      if (!item.access) return true;
      const a = item.access;
      if (a.requireOrg && !organization) return false;
      if (a.permission && !accessContext.permissions.includes(a.permission)) return false;
      if (a.role && accessContext.role !== a.role) return false;
      if (a.plan && accessContext.plan !== a.plan) return false;
      if (a.feature && !accessContext.features.includes(a.feature)) return false;
      return true;
    });
  }, [items, organization, accessContext]);
}

export function useFilteredNavGroups(groups: NavGroup[]) {
  return useFilteredNavItems(groups);
}

export function useNav() {
  const filteredGroups = useFilteredNavGroups(navGroups);
  return { navGroups: filteredGroups };
}
