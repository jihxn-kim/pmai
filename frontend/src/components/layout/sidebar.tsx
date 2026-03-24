"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FolderKanban, CheckSquare, Settings, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrgs } from "@/hooks/use-orgs";

interface SidebarProps {
  orgSlug: string;
}

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export function Sidebar({ orgSlug }: SidebarProps) {
  const pathname = usePathname();
  const { data: orgs } = useOrgs();

  const navItems: NavItem[] = [
    {
      href: `/org/${orgSlug}`,
      label: "Dashboard",
      icon: <LayoutDashboard className="size-4" />,
    },
    {
      href: `/org/${orgSlug}/projects`,
      label: "Projects",
      icon: <FolderKanban className="size-4" />,
    },
    {
      href: `/org/${orgSlug}/tasks`,
      label: "My Tasks",
      icon: <CheckSquare className="size-4" />,
    },
    {
      href: `/org/${orgSlug}/settings`,
      label: "Settings",
      icon: <Settings className="size-4" />,
    },
  ];

  const currentOrg = Array.isArray(orgs)
    ? orgs.find((o: { slug: string }) => o.slug === orgSlug)
    : null;

  return (
    <aside className="flex h-full w-60 flex-col border-r bg-muted/20">
      {/* Org header */}
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-semibold">
            {currentOrg?.name ?? orgSlug}
          </span>
          {Array.isArray(orgs) && orgs.length > 1 && (
            <span className="text-xs text-muted-foreground">Switch org</span>
          )}
        </div>
        {Array.isArray(orgs) && orgs.length > 1 && (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
