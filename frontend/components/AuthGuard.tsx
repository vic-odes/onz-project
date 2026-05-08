"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

/**
 * Encapsule une page privée. Tant que la session initiale est en cours de résolution,
 * affiche un spinner. Si l'utilisateur n'est pas authentifié, redirige vers /login
 * en passant l'URL d'origine en `redirect` query param.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      const redirect = encodeURIComponent(pathname || "/");
      router.replace(`/login?redirect=${redirect}`);
    }
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div className="flex justify-center items-center py-32">
        <div className="w-10 h-10 rounded-full border-4 border-gray-200 border-t-bleu-marine animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
