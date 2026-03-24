"use client";

import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";

export function Header() {
  const { user, logout } = useAuth();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.github_username?.slice(0, 2).toUpperCase() ?? "?";

  return (
    <header className="flex h-14 items-center justify-end gap-3 border-b bg-background px-6">
      {user && (
        <div className="flex items-center gap-3">
          <Avatar size="sm">
            {user.avatar_url && (
              <AvatarImage src={user.avatar_url} alt={user.name ?? user.github_username} />
            )}
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium">
            {user.name ?? user.github_username}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="gap-1.5 text-muted-foreground"
          >
            <LogOut className="size-4" />
            Logout
          </Button>
        </div>
      )}
    </header>
  );
}
