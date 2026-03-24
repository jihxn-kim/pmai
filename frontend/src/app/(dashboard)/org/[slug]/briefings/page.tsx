"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useOrgs } from "@/hooks/use-orgs";
import {
  useBriefings,
  useLatestBriefing,
  useGenerateBriefing,
} from "@/hooks/use-ai";
import { BriefingCard } from "@/components/ai/briefing-card";
import type { Briefing } from "@/components/ai/briefing-card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, Newspaper } from "lucide-react";

interface BriefingsPageProps {
  params: Promise<{ slug: string }>;
}

export default function BriefingsPage({ params }: BriefingsPageProps) {
  const { slug } = use(params);
  const router = useRouter();

  const { data: orgs } = useOrgs();
  const org = Array.isArray(orgs)
    ? (orgs as Array<{ id: string; slug: string; name: string }>).find(
        (o) => o.slug === slug
      )
    : null;
  const orgId = org?.id ?? "";

  const { data: latestData, isLoading: latestLoading } =
    useLatestBriefing(orgId);
  const { data: allData, isLoading: allLoading } = useBriefings(orgId);
  const generate = useGenerateBriefing(orgId);

  const latestBriefing: Briefing | null = latestData ?? null;
  const allBriefings: Briefing[] = Array.isArray(allData) ? allData : [];

  // Archive: all briefings except the latest
  const archiveBriefings = latestBriefing
    ? allBriefings.filter((b) => b.id !== latestBriefing.id)
    : allBriefings;

  const isLoading = latestLoading || allLoading;

  const handleGenerate = async () => {
    await generate.mutateAsync();
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-1"
            onClick={() => router.push(`/org/${slug}`)}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Weekly Briefings</h1>
            {org && (
              <p className="text-sm text-muted-foreground">{org.name}</p>
            )}
          </div>
        </div>

        <Button
          onClick={handleGenerate}
          disabled={generate.isPending || !orgId}
          className="gap-1.5"
        >
          {generate.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Newspaper className="size-4" />
          )}
          Generate Briefing
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
          Loading briefings...
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Latest briefing */}
          <section>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Latest
            </h2>
            {latestBriefing ? (
              <BriefingCard briefing={latestBriefing} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed py-16">
                <Newspaper className="size-10 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">
                  No briefing generated yet. Click &ldquo;Generate Briefing&rdquo; to
                  create one.
                </p>
              </div>
            )}
          </section>

          {/* Archive */}
          {archiveBriefings.length > 0 && (
            <section>
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Archive
              </h2>
              <div className="flex flex-col gap-4">
                {archiveBriefings.map((b) => (
                  <BriefingCard key={b.id} briefing={b} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
