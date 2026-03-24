"use client";

import { use, useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useOrgs, useOrgMembers } from "@/hooks/use-orgs";
import api from "@/lib/api";
import { MemberList, type Member } from "@/components/org/member-list";
import { SlackConnect } from "@/components/slack/slack-connect";
import { UserMapping } from "@/components/slack/user-mapping";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CheckCircle2, AlertCircle, UserPlus } from "lucide-react";

interface OrgSettingsPageProps {
  params: Promise<{ slug: string }>;
}

const ROLES = ["owner", "admin", "member"];

export default function OrgSettingsPage({ params }: OrgSettingsPageProps) {
  const { slug } = use(params);

  const { data: orgs, isLoading: orgsLoading, refetch: refetchOrgs } = useOrgs();

  const org = Array.isArray(orgs)
    ? (orgs as Array<{ id: string; slug: string; name: string }>).find(
        (o) => o.slug === slug
      )
    : null;

  const orgId = org?.id ?? "";

  // -- Org info form --
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle");

  useEffect(() => {
    if (org) {
      setOrgName(org.name);
      setOrgSlug(org.slug);
    }
  }, [org]);

  const updateOrg = useMutation({
    mutationFn: (data: { name: string; slug: string }) =>
      api.patch(`/api/orgs/${orgId}`, data).then((r) => r.data),
    onSuccess: () => {
      setSaveStatus("success");
      refetchOrgs();
      setTimeout(() => setSaveStatus("idle"), 3000);
    },
    onError: () => {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    },
  });

  const handleSaveOrg = (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId) return;
    updateOrg.mutate({ name: orgName, slug: orgSlug });
  };

  // -- Members --
  const {
    data: membersData,
    isLoading: membersLoading,
    refetch: refetchMembers,
  } = useOrgMembers(orgId);

  const members: Member[] = Array.isArray(membersData) ? membersData : [];

  // -- Add member form --
  const [newUsername, setNewUsername] = useState("");
  const [newRole, setNewRole] = useState("member");
  const [addError, setAddError] = useState<string | null>(null);

  const addMember = useMutation({
    mutationFn: (data: { github_username: string; role: string }) =>
      api.post(`/api/orgs/${orgId}/members`, data).then((r) => r.data),
    onSuccess: () => {
      setNewUsername("");
      setNewRole("member");
      setAddError(null);
      refetchMembers();
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to add member.";
      setAddError(message);
    },
  });

  const handleAddMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !orgId) return;
    setAddError(null);
    addMember.mutate({ github_username: newUsername.trim(), role: newRole });
  };

  if (orgsLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading settings...
      </div>
    );
  }

  if (!org) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-destructive">
        Organization not found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Organization Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage settings and members for <strong>{org.name}</strong>.
        </p>
      </div>

      {/* ── Organization Info ── */}
      <Card>
        <CardHeader>
          <CardTitle>Organization Info</CardTitle>
          <CardDescription>Update your organization name and slug.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveOrg} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-name">Name</Label>
              <Input
                id="org-name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="My Organization"
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-slug">Slug</Label>
              <Input
                id="org-slug"
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                placeholder="my-org"
                required
              />
              <p className="text-xs text-muted-foreground">
                Used in URLs. Only lowercase letters, numbers, and hyphens.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Button
                type="submit"
                disabled={updateOrg.isPending}
              >
                {updateOrg.isPending ? "Saving..." : "Save Changes"}
              </Button>

              {saveStatus === "success" && (
                <span className="flex items-center gap-1.5 text-sm text-green-600">
                  <CheckCircle2 className="size-4" />
                  Saved successfully
                </span>
              )}
              {saveStatus === "error" && (
                <span className="flex items-center gap-1.5 text-sm text-destructive">
                  <AlertCircle className="size-4" />
                  Failed to save
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* ── Member Management ── */}
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>
            Manage who has access to this organization.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {/* Add member form */}
          <form onSubmit={handleAddMember} className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold">Add Member</h3>
            <div className="flex flex-wrap gap-2">
              <Input
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder="GitHub username"
                className="flex-1 min-w-40"
                required
              />
              <Select value={newRole} onValueChange={(v) => v && setNewRole(v)}>
                <SelectTrigger className="w-32">
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
              <Button
                type="submit"
                disabled={addMember.isPending || !newUsername.trim()}
                className="gap-1.5"
              >
                <UserPlus className="size-4" />
                {addMember.isPending ? "Adding..." : "Add"}
              </Button>
            </div>
            {addError && (
              <p className="flex items-center gap-1.5 text-sm text-destructive">
                <AlertCircle className="size-4" />
                {addError}
              </p>
            )}
          </form>

          <Separator />

          {/* Member list */}
          {membersLoading ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Loading members...
            </div>
          ) : (
            <MemberList
              orgId={orgId}
              members={members}
              onRefresh={refetchMembers}
            />
          )}
        </CardContent>
      </Card>

      {/* ── Slack 연동 ── */}
      <Separator />
      <div>
        <h2 className="text-xl font-semibold">Slack 연동</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Slack 워크스페이스를 연결하고 알림 채널을 설정합니다.
        </p>
      </div>

      {orgId && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Slack 연결</CardTitle>
              <CardDescription>
                Slack 워크스페이스를 연결하고 조직 기본 채널을 설정합니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SlackConnect orgId={orgId} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>사용자 매핑</CardTitle>
              <CardDescription>
                조직 멤버와 Slack 사용자를 연결합니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <UserMapping orgId={orgId} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
