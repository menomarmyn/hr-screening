import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, setUnauthorizedHandler, tokenStore } from "../api";
import type { Role, User } from "../types";

interface AuthState {
  user: User | null;
  ready: boolean;
  signIn: (token: string, user: User) => void;
  signOut: () => void;
}

const Ctx = createContext<AuthState>({ user: null, ready: false, signIn: () => {}, signOut: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => {
    tokenStore.set(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(signOut)
      .finally(() => setReady(true));
  }, [signOut]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      signIn: (token, u) => {
        tokenStore.set(token);
        setUser(u);
      },
      signOut,
    }),
    [user, ready, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

/** Пускает только нужную роль; остальных — на вход, сохранив, куда шли. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return null;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (user.role !== role) return <Navigate to={user.role === "hr" ? "/hr" : "/me"} replace />;
  return <>{children}</>;
}
