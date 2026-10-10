"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { ShieldCheck, Lock, AlertCircle, Loader2, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthUser, checkSession, loginWithCredentials, logoutUser } from "@/lib/auth-client";

interface AuthContextType {
  user: AuthUser | null;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  logout: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function LoginGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let mounted = true;
    checkSession()
      .then((activeUser) => {
        if (mounted) {
          setUser(activeUser);
          setIsInitializing(false);
        }
      })
      .catch(() => {
        if (mounted) setIsInitializing(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Please enter both username and password");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const loggedIn = await loginWithCredentials(username, password);
      setUser(loggedIn);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickDemoFill = () => {
    setUsername("admin");
    setPassword("admin");
    setError(null);
  };

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
  };

  if (isInitializing) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#faf9f5]">
        <div className="flex flex-col items-center gap-3 text-stone-600">
          <Loader2 className="h-8 w-8 animate-spin text-[#20808d]" />
          <p className="text-xs font-medium tracking-wide">Validating session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1f1915]/60 p-4 backdrop-blur-sm">
        <div className="w-full max-w-md rounded-2xl border border-[#e7e5e0] bg-[#faf9f5] p-6 shadow-2xl transition-all">
          {/* Header */}
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-[#20808d]/10 text-[#20808d] border border-[#20808d]/20 shadow-sm">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h1 className="font-serif text-xl font-bold tracking-tight text-[#1f1915]">
              Traffic Grid Surveillance
            </h1>
            <p className="mt-1 text-xs text-[#6b675f]">
              Restricted Operations Panel • Please sign in to continue
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#c25450]/30 bg-[#c25450]/10 p-3 text-xs text-[#a8423e]">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-semibold text-[#1f1915]">
                Username
              </label>
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                autoFocus
                disabled={isSubmitting}
                className="h-9 text-xs bg-white border-[#e7e5e0]"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-[#1f1915]">
                Password
              </label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={isSubmitting}
                className="h-9 text-xs bg-white border-[#e7e5e0]"
              />
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-9 bg-[#20808d] hover:bg-[#016a71] text-white text-xs font-medium gap-1.5 transition-colors shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Authorizing...</span>
                </>
              ) : (
                <>
                  <Lock className="h-3.5 w-3.5" />
                  <span>Authenticate Terminal</span>
                </>
              )}
            </Button>
          </form>

          {/* Quick Demo Helper */}
          <div className="mt-5 border-t border-[#e7e5e0] pt-4 text-center">
            <button
              type="button"
              onClick={handleQuickDemoFill}
              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[#20808d] hover:underline cursor-pointer"
            >
              <KeyRound className="h-3 w-3" />
              <span>Click to auto-fill demo credentials (admin / admin)</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  );
}
