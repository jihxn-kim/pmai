"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";

interface ProjectBriefing {
  project_id: string;
  project_name: string;
  progress?: number;
  completed_tasks?: string[];
  delayed_items?: string[];
  risks?: string[];
  recommendations?: string[];
  workload?: string;
}

interface Briefing {
  id: string;
  week_label?: string;
  week_start?: string;
  org_summary?: string;
  projects?: ProjectBriefing[];
  created_at: string;
}

interface BriefingCardProps {
  briefing: Briefing;
}

function ProjectSection({ project }: { project: ProjectBriefing }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border">
      <button
        className="flex w-full items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
          <span>{project.project_name}</span>
        </div>
        {project.progress != null && (
          <span className="text-xs text-muted-foreground">
            {project.progress}%
          </span>
        )}
      </button>

      {expanded && (
        <div className="border-t px-4 pb-3 pt-2 flex flex-col gap-3">
          {/* Progress bar */}
          {project.progress != null && (
            <div>
              <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>Progress</span>
                <span>{project.progress}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${project.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Workload */}
          {project.workload && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Workload
              </span>
              <p className="mt-0.5 text-sm">{project.workload}</p>
            </div>
          )}

          {/* Completed tasks */}
          {project.completed_tasks && project.completed_tasks.length > 0 && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Completed
              </span>
              <ul className="mt-1 space-y-0.5">
                {project.completed_tasks.map((t, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-sm">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-green-500" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Delayed items */}
          {project.delayed_items && project.delayed_items.length > 0 && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Delayed
              </span>
              <ul className="mt-1 space-y-0.5">
                {project.delayed_items.map((t, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-sm">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-yellow-500" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risks */}
          {project.risks && project.risks.length > 0 && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Risks
              </span>
              <ul className="mt-1 space-y-0.5">
                {project.risks.map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-sm">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-red-500" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {project.recommendations && project.recommendations.length > 0 && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Recommendations
              </span>
              <ul className="mt-1 space-y-0.5">
                {project.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-sm">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-blue-500" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function BriefingCard({ briefing }: BriefingCardProps) {
  const projects: ProjectBriefing[] = Array.isArray(briefing.projects)
    ? briefing.projects
    : [];

  const weekLabel =
    briefing.week_label ??
    (briefing.week_start
      ? `Week of ${new Date(briefing.week_start).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}`
      : "Weekly Briefing");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{weekLabel}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {/* Org summary */}
        {briefing.org_summary && (
          <p className="text-sm text-muted-foreground">{briefing.org_summary}</p>
        )}

        {/* Project sections */}
        {projects.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Projects
            </h3>
            {projects.map((p) => (
              <ProjectSection key={p.project_id} project={p} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export type { Briefing };
