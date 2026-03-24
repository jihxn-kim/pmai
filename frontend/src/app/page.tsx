"use client";
import { useAuth } from "@/hooks/use-auth";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (user) router.push("/me");
      else router.push("/login");
    }
  }, [user, isLoading, router]);

  return <div className="flex items-center justify-center h-screen">Loading...</div>;
}
