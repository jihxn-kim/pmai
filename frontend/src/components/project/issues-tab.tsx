"use client";

import { useProjectIssues } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, Clock, GitPullRequest, UserX } from "lucide-react";

interface IssuesTabProps {
  projectId: string;
}

interface IssueItem {
  id: string;
  title: string;
  detail?: string;
}

interface IssuesData {
  overdue_tasks?: IssueItem[];
  stale_prs?: IssueItem[];
  pending_reviews?: IssueItem[];
  unassigned_tasks?: IssueItem[];
}

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  items: IssueItem[];
  emptyText: string;
}

function IssueSection({ title, icon, items, emptyText }: SectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          {icon}
          {title}
          <span className="ml-auto inline-flex size-5 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
            {items.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground">{emptyText}</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-2 rounded-md border p-2"
              >
                <span className="text-sm">{item.title}</span>
                {item.detail && (
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {item.detail}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function IssuesTab({ projectId }: IssuesTabProps) {
  const { data, isLoading, isError } = useProjectIssues(projectId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Loading issues...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-destructive">
        Failed to load issues.
      </div>
    );
  }

  const issues: IssuesData = data ?? {};
  const overdueTasks: IssueItem[] = Array.isArray(issues.overdue_tasks)
    ? issues.overdue_tasks
    : [];
  const stalePrs: IssueItem[] = Array.isArray(issues.stale_prs)
    ? issues.stale_prs
    : [];
  const pendingReviews: IssueItem[] = Array.isArray(issues.pending_reviews)
    ? issues.pending_reviews
    : [];
  const unassignedTasks: IssueItem[] = Array.isArray(issues.unassigned_tasks)
    ? issues.unassigned_tasks
    : [];

  const totalIssues =
    overdueTasks.length +
    stalePrs.length +
    pendingReviews.length +
    unassignedTasks.length;

  return (
    <div className="space-y-4">
      {totalIssues === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16">
          <AlertTriangle className="size-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No issues detected.</p>
        </div>
      )}

      <IssueSection
        title="Overdue Tasks"
        icon={<Clock className="size-4 text-red-500" />}
        items={overdueTasks}
        emptyText="No overdue tasks."
      />
      <IssueSection
        title="Stale PRs"
        icon={<GitPullRequest className="size-4 text-orange-500" />}
        items={stalePrs}
        emptyText="No stale pull requests."
      />
      <IssueSection
        title="Pending Reviews"
        icon={<AlertTriangle className="size-4 text-yellow-500" />}
        items={pendingReviews}
        emptyText="No pull requests awaiting review."
      />
      <IssueSection
        title="Unassigned Tasks"
        icon={<UserX className="size-4 text-slate-500" />}
        items={unassignedTasks}
        emptyText="All tasks are assigned."
      />
    </div>
  );
}
