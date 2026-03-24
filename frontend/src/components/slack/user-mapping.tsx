"use client";

import { useState } from "react";
import {
  useSlackUserMappings,
  useAddUserMapping,
} from "@/hooks/use-slack";
import { useOrgMembers } from "@/hooks/use-orgs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Member {
  user_id: string;
  name: string;
  github_username: string;
}

interface UserMappingProps {
  orgId: string;
}

export function UserMapping({ orgId }: UserMappingProps) {
  const { data: mappings, isLoading: mappingsLoading } =
    useSlackUserMappings(orgId);
  const { data: membersData } = useOrgMembers(orgId);
  const addMapping = useAddUserMapping(orgId);

  const members: Member[] = Array.isArray(membersData) ? membersData : [];
  const mappingList = Array.isArray(mappings) ? mappings : [];

  const [selectedUserId, setSelectedUserId] = useState("");
  const [slackUserId, setSlackUserId] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || !slackUserId.trim()) return;
    setAddError(null);
    addMapping.mutate(
      { user_id: selectedUserId, slack_user_id: slackUserId.trim() },
      {
        onSuccess: () => {
          setSelectedUserId("");
          setSlackUserId("");
        },
        onError: (err: unknown) => {
          const message =
            (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail ?? "매핑 추가에 실패했습니다.";
          setAddError(message);
        },
      }
    );
  };

  const getMemberName = (userId: string) => {
    const member = members.find((m) => m.user_id === userId);
    return member ? `${member.name} (@${member.github_username})` : userId;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Existing mappings table */}
      {mappingsLoading ? (
        <p className="text-sm text-muted-foreground">로딩 중...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">멤버</th>
                <th className="pb-2 font-medium">Slack User ID</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {mappingList.map((mapping) => (
                <tr key={mapping.id}>
                  <td className="py-2 pr-4">{getMemberName(mapping.user_id)}</td>
                  <td className="py-2 font-mono text-muted-foreground">
                    {mapping.slack_user_id}
                  </td>
                </tr>
              ))}
              {mappingList.length === 0 && (
                <tr>
                  <td
                    colSpan={2}
                    className="py-6 text-center text-muted-foreground"
                  >
                    등록된 매핑이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Add mapping form */}
      <form onSubmit={handleAdd} className="flex flex-col gap-3">
        <h4 className="text-sm font-semibold">매핑 추가</h4>
        <div className="flex flex-wrap gap-2">
          <Select
            value={selectedUserId}
            onValueChange={(v) => v && setSelectedUserId(v)}
          >
            <SelectTrigger className="flex-1 min-w-40">
              <SelectValue placeholder="멤버 선택" />
            </SelectTrigger>
            <SelectContent>
              {members.map((m) => (
                <SelectItem key={m.user_id} value={m.user_id}>
                  {m.name} (@{m.github_username})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={slackUserId}
            onChange={(e) => setSlackUserId(e.target.value)}
            placeholder="Slack User ID (예: U0123456789)"
            className="flex-1 min-w-40"
          />
          <Button
            type="submit"
            disabled={
              addMapping.isPending || !selectedUserId || !slackUserId.trim()
            }
          >
            {addMapping.isPending ? "추가 중..." : "추가"}
          </Button>
        </div>
        {addError && (
          <p className="text-sm text-destructive">{addError}</p>
        )}
      </form>
    </div>
  );
}
