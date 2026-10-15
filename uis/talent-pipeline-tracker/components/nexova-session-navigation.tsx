"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { NEXOVA_SESSION_EXPIRED_EVENT } from "@/lib/nexova-api";

export default function NexovaSessionNavigation() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    function handleExpiredSession() {
      if (pathname !== "/login") {
        router.replace("/login");
      }
    }

    window.addEventListener(NEXOVA_SESSION_EXPIRED_EVENT, handleExpiredSession);
    return () => {
      window.removeEventListener(NEXOVA_SESSION_EXPIRED_EVENT, handleExpiredSession);
    };
  }, [pathname, router]);

  return null;
}
