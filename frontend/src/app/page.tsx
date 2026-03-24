"use client";
import { useAuth } from "@/hooks/use-auth";
import { useOrgs } from "@/hooks/use-orgs";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const { user, isLoading } = useAuth();
  const { data: orgs, isLoading: orgsLoading } = useOrgs();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !orgsLoading) {
      if (!user) {
        router.push("/login");
      } else if (Array.isArray(orgs) && orgs.length > 0) {
        router.push(`/org/${orgs[0].slug}`);
      } else {
        router.push("/me");
      }
    }
  }, [user, isLoading, orgs, orgsLoading, router]);

  return <div className="flex items-center justify-center h-screen">Loading...</div>;
}
