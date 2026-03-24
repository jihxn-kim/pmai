"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Trash2 } from "lucide-react";

export interface Member {
  user_id: string;
  name: string;
  github_username: string;
  avatar_url?: string | null;
  role: string;
}

interface MemberListProps {
  orgId: string;
  members: Member[];
  onRefresh: () => void;
}

const ROLES = ["owner", "admin", "member"];

const roleVariant: Record<string, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export function MemberList({ orgId, members, onRefresh }: MemberListProps) {
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  const updateRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api
        .patch(`/api/orgs/${orgId}/members/${userId}`, { role })
        .then((r) => r.data),
    onSuccess: onRefresh,
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) =>
      api.delete(`/api/orgs/${orgId}/members/${userId}`).then((r) => r.data),
    onSuccess: () => {
      setConfirmRemoveId(null);
      onRefresh();
    },
  });

  const memberToRemove = members.find((m) => m.user_id === confirmRemoveId);

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="pb-2 pr-4 font-medium">Member</th>
              <th className="pb-2 pr-4 font-medium">GitHub</th>
              <th className="pb-2 pr-4 font-medium">Role</th>
              <th className="pb-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {members.map((member) => (
              <tr key={member.user_id} className="group">
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2.5">
                    <Avatar size="sm">
                      {member.avatar_url && (
                        <AvatarImage
                          src={member.avatar_url}
                          alt={member.name}
                        />
                      )}
                      <AvatarFallback>
                        {member.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <span className="font-medium">{member.name}</span>
                  </div>
                </td>
                <td className="py-3 pr-4 text-muted-foreground">
                  @{member.github_username}
                </td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <Badge variant={roleVariant[member.role] ?? "outline"}>
                      {member.role}
                    </Badge>
                    <Select
                      value={member.role}
                      onValueChange={(role) =>
                        role && updateRole.mutate({ userId: member.user_id, role })
                      }
                    >
                      <SelectTrigger size="sm" className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((r) => (
                          <SelectItem key={r} value={r}>
                            {r}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </td>
                <td className="py-3">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setConfirmRemoveId(member.user_id)}
                    aria-label="Remove member"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </td>
              </tr>
            ))}
            {members.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="py-8 text-center text-muted-foreground"
                >
                  No members yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Confirm remove dialog */}
      <Dialog
        open={!!confirmRemoveId}
        onOpenChange={(open) => !open && setConfirmRemoveId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove{" "}
              <strong>{memberToRemove?.name ?? "this member"}</strong> from the
              organization? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmRemoveId(null)}
              disabled={removeMember.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                confirmRemoveId && removeMember.mutate(confirmRemoveId)
              }
              disabled={removeMember.isPending}
            >
              {removeMember.isPending ? "Removing..." : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
