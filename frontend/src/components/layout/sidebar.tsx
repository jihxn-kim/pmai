"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, CheckSquare, Settings, ChevronDown, Plus, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrgs } from "@/hooks/use-orgs";
import { Button } from "@/components/ui/button";

interface SidebarProps {
  orgSlug: string;
}

export function Sidebar({ orgSlug }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: orgs } = useOrgs();

  const hasOrgs = Array.isArray(orgs) && orgs.length > 0;
  // If no slug in URL but user has orgs, use first org's slug
  const effectiveSlug = orgSlug || (hasOrgs ? (orgs[0] as { slug: string }).slug : "");
  const currentOrg = hasOrgs
    ? (orgs as Array<{ slug: string }>).find((o) => o.slug === effectiveSlug)
    : null;

  // Only show minimal sidebar if user truly has no orgs
  if (!hasOrgs) {
    return (
      <aside className="flex h-full w-60 flex-col border-r bg-muted/20">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Building2 className="size-4 text-muted-foreground" />
          <span className="text-sm font-semibold text-muted-foreground">PM Agent</span>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          <Link
            href="/me"
            className={cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
              pathname === "/me"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <CheckSquare className="size-4" />
            My Tasks
          </Link>
        </nav>
        {!hasOrgs && (
          <div className="p-3 border-t">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => router.push("/me")}
            >
              <Plus className="size-4 mr-2" /> 조직 만들기
            </Button>
          </div>
        )}
      </aside>
    );
  }

  // Has org — full navigation (only pages that exist)
  const navItems = [
    {
      href: `/org/${effectiveSlug}`,
      label: "Dashboard",
      icon: <LayoutDashboard className="size-4" />,
    },
    {
      href: "/me",
      label: "My Tasks",
      icon: <CheckSquare className="size-4" />,
    },
    {
      href: `/org/${effectiveSlug}/settings`,
      label: "Settings",
      icon: <Settings className="size-4" />,
    },
  ];

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
          const isActive = pathname === item.href || (item.href !== "/me" && pathname.startsWith(item.href + "/"));
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
