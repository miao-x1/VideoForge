import { useCallback, useEffect, useState } from 'react';
import { authApi, type TokenResponse, type UserOut } from '../api/client';

const TOKEN_KEY = 'vf_token';
const USER_KEY = 'vf_user';

function persistAuth(resp: TokenResponse) {
  localStorage.setItem(TOKEN_KEY, resp.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
}

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
        .catch((err: { response?: { status?: number } }) => {
          if (err?.response?.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
            setUser(null);
          }
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const applyAuth = useCallback((resp: TokenResponse) => {
    persistAuth(resp);
    setUser(resp.user);
    return resp;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
    window.location.href = '/login';
  }, []);

  return { user, loading, applyAuth, logout };
}
