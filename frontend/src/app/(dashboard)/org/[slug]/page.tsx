"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useOrgs, useOrgDashboard } from "@/hooks/use-orgs";
import { ProjectCard, type ProjectSummary } from "@/components/org/project-card";
import { ActivityFeed } from "@/components/org/activity-feed";
import { Button } from "@/components/ui/button";
import { Plus, FolderKanban } from "lucide-react";

interface OrgDashboardPageProps {
  params: Promise<{ slug: string }>;
}

export default function OrgDashboardPage({ params }: OrgDashboardPageProps) {
  const { slug } = use(params);
  const router = useRouter();

  const { data: orgs, isLoading: orgsLoading } = useOrgs();

  // Resolve slug -> org_id
  const org = Array.isArray(orgs)
    ? (orgs as Array<{ id: string; slug: string; name: string }>).find(
        (o) => o.slug === slug
      )
    : null;

  const orgId = org?.id ?? "";

  const { data: dashboard, isLoading: dashboardLoading } = useOrgDashboard(orgId);

  const isLoading = orgsLoading || (!!orgId && dashboardLoading);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading dashboard...
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

  const projects: ProjectSummary[] = Array.isArray(dashboard?.projects)
    ? dashboard.projects.map(
        (p: Omit<ProjectSummary, "org_slug">) => ({ ...p, org_slug: slug })
      )
    : [];

  // Use the first project's id for the combined activity feed (or empty string)
  const firstProjectId = projects[0]?.id ?? "";

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{org.name}</h1>
          <p className="text-sm text-muted-foreground">
            {projects.length} project{projects.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button
          onClick={() => router.push(`/org/${slug}/projects/new`)}
          className="gap-1.5"
        >
          <Plus className="size-4" />
          New Project
        </Button>
      </div>

      {projects.length === 0 ? (
        /* Empty state */
        <div className="flex flex-1 flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-20">
          <FolderKanban className="size-12 text-muted-foreground/50" />
          <div className="text-center">
            <p className="font-medium">No projects yet</p>
            <p className="text-sm text-muted-foreground">
              Create your first project to get started.
            </p>
          </div>
          <Button
            onClick={() => router.push(`/org/${slug}/projects/new`)}
            className="gap-1.5"
          >
            <Plus className="size-4" />
            Create Project
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Project grid */}
          <div className="lg:col-span-2">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Projects
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          </div>

          {/* Activity feed */}
          <div className="flex flex-col">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Recent Activity
            </h2>
            {firstProjectId ? (
              <ActivityFeed
                projectId={firstProjectId}
                className="max-h-[600px] rounded-xl border"
              />
            ) : (
              <div className="flex items-center justify-center rounded-xl border py-8 text-sm text-muted-foreground">
                No activity to show.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
