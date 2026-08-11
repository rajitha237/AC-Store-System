"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getAccessToken } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const token = getAccessToken();

    router.replace(
      token
        ? "/dashboard"
        : "/login",
    );
  }, [router]);

  return (
    <main className="page-center">
      <div className="loading-spinner" />
    </main>
  );
}
