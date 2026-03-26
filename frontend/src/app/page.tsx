"use client";
import { useAuth } from "@/hooks/use-auth";
import { useOrgs } from "@/hooks/use-orgs";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Brain,
  GitPullRequest,
  BarChart3,
  Users,
  MessageSquare,
  Calendar,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const { user, isLoading } = useAuth();
  const { data: orgs, isLoading: orgsLoading } = useOrgs();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !orgsLoading && user) {
      if (Array.isArray(orgs) && orgs.length > 0) {
        router.push(`/org/${orgs[0].slug}`);
      } else {
        router.push("/me");
      }
    }
  }, [user, isLoading, orgs, orgsLoading, router]);

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (user) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <header className="border-b">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Brain className="size-6 text-primary" />
            <span className="text-lg font-bold">PM Agent</span>
          </div>
          <Button variant="outline" onClick={() => router.push("/login")}>
            Login
          </Button>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="container mx-auto px-6 py-24 text-center">
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            AI로 프로젝트를
            <br />
            <span className="text-primary">똑똑하게</span> 관리하세요
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            GitHub 연동, AI 코드 리뷰, 자동 프로젝트 분석, 팀원 전문성 파악까지.
            PM Agent가 프로젝트의 건강 상태를 분석하고 실행 가능한 제안을 제공합니다.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button size="lg" onClick={() => router.push("/login")}>
              시작하기
              <ArrowRight className="ml-2 size-4" />
            </Button>
          </div>
        </section>

        {/* Features */}
        <section className="border-t bg-muted/30 py-20">
          <div className="container mx-auto px-6">
            <h2 className="text-center text-3xl font-bold mb-12">주요 기능</h2>
            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              <FeatureCard
                icon={Brain}
                title="AI 프로젝트 분석"
                description="커밋, PR, 태스크 데이터를 종합 분석해서 프로젝트 건강도를 평가하고 실행 가능한 개선안을 제안합니다."
              />
              <FeatureCard
                icon={GitPullRequest}
                title="AI 코드 리뷰"
                description="PR 변경사항을 자동으로 분석하고 보안 취약점, 성능 이슈, 코드 품질 문제를 찾아냅니다."
              />
              <FeatureCard
                icon={BarChart3}
                title="이슈 자동 등록"
                description="AI가 발견한 문제점을 GitHub Issue로 등록하고, 적합한 팀원에게 태스크를 자동 배정합니다."
              />
              <FeatureCard
                icon={Users}
                title="팀원 전문성 추적"
                description="커밋 히스토리를 분석해서 팀원별 전문 분야를 자동으로 파악하고 태스크 배정에 활용합니다."
              />
              <FeatureCard
                icon={MessageSquare}
                title="Slack 연동"
                description="Slack에서 자연어로 프로젝트 상태를 확인하고, 중요 이벤트 알림을 자동으로 받습니다."
              />
              <FeatureCard
                icon={Calendar}
                title="캘린더 & Notion 동기화"
                description="Google Calendar, Notion과 양방향 동기화로 일정과 문서를 한 곳에서 관리합니다."
              />
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="container mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold">지금 시작하세요</h2>
          <p className="mt-4 text-muted-foreground">
            GitHub 계정만 있으면 바로 사용할 수 있습니다.
          </p>
          <Button size="lg" className="mt-8" onClick={() => router.push("/login")}>
            GitHub으로 시작하기
            <ArrowRight className="ml-2 size-4" />
          </Button>
        </section>
      </main>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        PM Agent - AI-Powered Project Management
      </footer>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <Icon className="size-8 text-primary mb-3" />
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
