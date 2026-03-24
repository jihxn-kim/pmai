"use client";

import { useProjectMembers } from "@/hooks/use-projects";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Users } from "lucide-react";

interface TeamTabProps {
  projectId: string;
}

interface Member {
  id: string;
  name: string;
  email?: string;
  avatar_url?: string;
  github_username?: string;
  role: "owner" | "admin" | "member";
  task_count?: number;
}

const roleConfig: Record<
  Member["role"],
  { label: string; className: string }
> = {
  owner: {
    label: "Owner",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  },
  admin: {
    label: "Admin",
    className: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  },
  member: {
    label: "Member",
    className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  },
};

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function TeamTab({ projectId }: TeamTabProps) {
  const { data, isLoading, isError } = useProjectMembers(projectId);

  const members: Member[] = Array.isArray(data) ? data : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Loading team members...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-destructive">
        Failed to load team members.
      </div>
    );
  }

  if (members.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-20">
        <Users className="size-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No team members found.</p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="size-4" />
          Team Members
          <span className="ml-auto text-sm font-normal text-muted-foreground">
            {members.length} member{members.length !== 1 ? "s" : ""}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-muted-foreground">
              <th className="px-4 py-2 text-left font-medium">Member</th>
              <th className="px-4 py-2 text-left font-medium">GitHub</th>
              <th className="px-4 py-2 text-left font-medium">Role</th>
              <th className="px-4 py-2 text-right font-medium">Tasks</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {members.map((member) => {
              const role =
                roleConfig[member.role] ?? roleConfig.member;
              return (
                <tr key={member.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar size="sm">
                        {member.avatar_url && (
                          <AvatarImage
                            src={member.avatar_url}
                            alt={member.name}
                          />
                        )}
                        <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
                      </Avatar>
                      <span className="font-medium">{member.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {member.github_username ? (
                      <a
                        href={`https://github.com/${member.github_username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-foreground hover:underline"
                      >
                        @{member.github_username}
                      </a>
                    ) : (
                      <span className="text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                        role.className
                      )}
                    >
                      {role.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {member.task_count ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
