import { useCallback, useEffect, useState } from 'react';
import { authApi, type UserOut } from '../api/client';

const TOKEN_KEY = 'vf_token';
const USER_KEY = 'vf_user';

export function useAuth() {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const stored = localStorage.getItem(USER_KEY);
    if (stored && token) {
      try {
        setUser(JSON.parse(stored));
      } catch { /* ignore */ }
    }
    if (token) {
      authApi.me()
        .then((u) => { setUser(u); localStorage.setItem(USER_KEY, JSON.stringify(u)); })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const resp = await authApi.login(email, password);
    localStorage.setItem(TOKEN_KEY, resp.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
    setUser(resp.user);
    return resp;
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    const resp = await authApi.register(email, password, displayName);
    localStorage.setItem(TOKEN_KEY, resp.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
    setUser(resp.user);
    return resp;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
    window.location.href = '/login';
  }, []);

  return { user, loading, login, register, logout };
}
