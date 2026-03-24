"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function CallbackHandler() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token") || searchParams.get("access_token");
    if (token) {
      sessionStorage.setItem("access_token", token);
      window.location.href = "/";
    } else {
      window.location.href = "/login";
    }
  }, [searchParams]);

  return <div className="flex items-center justify-center h-screen">로그인 중...</div>;
}

export default function CallbackPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
      <CallbackHandler />
    </Suspense>
  );
}
