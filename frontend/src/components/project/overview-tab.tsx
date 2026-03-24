"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useProjectProgress } from "@/hooks/use-projects";
import { formatDate } from "@/lib/utils";
import { CalendarDays } from "lucide-react";

interface OverviewTabProps {
  projectId: string;
  description?: string;
  startDate?: string;
  endDate?: string;
}

interface ProgressData {
  total: number;
  todo: number;
  in_progress: number;
  review: number;
  done: number;
}

export function OverviewTab({
  projectId,
  description,
  startDate,
  endDate,
}: OverviewTabProps) {
  const { data: progress, isLoading } = useProjectProgress(projectId);

  const stats: ProgressData = progress ?? {
    total: 0,
    todo: 0,
    in_progress: 0,
    review: 0,
    done: 0,
  };

  const percent =
    stats.total > 0 ? Math.round((stats.done / stats.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading...</div>
          ) : (
            <>
              <div className="flex items-end justify-center gap-2">
                <span className="text-5xl font-bold tabular-nums">{percent}</span>
                <span className="mb-1 text-2xl text-muted-foreground">%</span>
              </div>
              <div className="mx-auto max-w-sm">
                <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <p className="mt-1 text-center text-xs text-muted-foreground">
                  {stats.done} of {stats.total} tasks complete
                </p>
              </div>

              {/* Status distribution */}
              <div className="grid grid-cols-4 gap-3 pt-2">
                <StatCard label="Todo" count={stats.todo} color="text-slate-500" />
                <StatCard
                  label="In Progress"
                  count={stats.in_progress}
                  color="text-blue-500"
                />
                <StatCard
                  label="Review"
                  count={stats.review}
                  color="text-yellow-500"
                />
                <StatCard
                  label="Done"
                  count={stats.done}
                  color="text-green-500"
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Date range */}
      {(startDate || endDate) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarDays className="size-4" />
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {startDate ? formatDate(startDate) : "—"}{" "}
              <span className="mx-1">→</span>{" "}
              {endDate ? formatDate(endDate) : "—"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Description */}
      {description && (
        <Card>
          <CardHeader>
            <CardTitle>About this project</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border p-3">
      <span className={`text-2xl font-bold tabular-nums ${color}`}>{count}</span>
      <span className="text-center text-xs text-muted-foreground">{label}</span>
    </div>
  );
}
