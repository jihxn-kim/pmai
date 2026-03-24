"use client";

import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const { login, isLoading, user } = useAuth();

  if (isLoading) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (user) {
    window.location.href = "/";
    return null;
  }

  return (
    <div className="flex flex-col items-center justify-center h-screen gap-6">
      <h1 className="text-3xl font-bold">PM Agent</h1>
      <p className="text-muted-foreground">프로젝트 관리를 위한 AI 에이전트</p>
      <Button size="lg" onClick={login}>
        GitHub으로 로그인
      </Button>
    </div>
  );
}
