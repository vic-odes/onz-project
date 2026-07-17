"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

type Mode = "login" | "register";

interface AuthFormProps {
  mode: Mode;
}

export default function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLogin = mode === "login";
  const redirectParam = searchParams.get("redirect");
  const redirectTo = redirectParam || "/mes-projets";
  // Préserve le param redirect= en navigant entre /login et /register
  const redirectQuery = redirectParam ? `?redirect=${encodeURIComponent(redirectParam)}` : "";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Email et mot de passe sont requis.");
      return;
    }
    if (!isLogin && password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }

    setSubmitting(true);
    try {
      if (isLogin) {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password, fullName.trim() || undefined);
      }
      router.replace(redirectTo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-6 py-12">
      <div className="card w-full max-w-md">
        <h1 className="font-playfair text-3xl font-bold text-bleu-marine mb-2">
          {isLogin ? "Connexion" : "Créer un compte"}
        </h1>
        <p className="font-source text-sm text-gray-500 mb-6">
          {isLogin
            ? "Connectez-vous pour accéder à vos projets."
            : "Démarrez en quelques secondes — gratuit pour commencer."}
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!isLogin && (
            <div>
              <label className="label">Nom complet (optionnel)</label>
              <input
                type="text"
                className="input-field"
                placeholder="Ex. : Marie Diallo"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={submitting}
                maxLength={120}
              />
            </div>
          )}

          <div>
            <label className="label">Email *</label>
            <input
              type="email"
              className="input-field"
              placeholder="vous@exemple.org"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div>
            <label className="label">
              Mot de passe *
              {!isLogin && (
                <span className="ml-1 font-normal text-gray-400">(8 caractères minimum)</span>
              )}
            </label>
            <input
              type="password"
              className="input-field"
              placeholder="••••••••"
              autoComplete={isLogin ? "current-password" : "new-password"}
              required
              minLength={isLogin ? 1 : 8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg font-source text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting
              ? isLogin
                ? "Connexion…"
                : "Création…"
              : isLogin
                ? "Se connecter"
                : "Créer mon compte"}
          </button>
        </form>

        <p className="font-source text-sm text-center mt-6 text-gray-600">
          {isLogin ? (
            <>
              Pas encore de compte ?{" "}
              <Link href={`/register${redirectQuery}`} className="text-vert-sauge font-semibold hover:underline">
                Créer un compte
              </Link>
            </>
          ) : (
            <>
              Déjà inscrit ?{" "}
              <Link href={`/login${redirectQuery}`} className="text-vert-sauge font-semibold hover:underline">
                Se connecter
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
