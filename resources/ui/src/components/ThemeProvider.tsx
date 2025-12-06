import type { ReactNode } from 'react';
import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_PREFERENCE_KEY = 'omni_theme';

// Helper to get session ID (same logic as api.ts)
function getSessionId(): string {
  let sessionId = sessionStorage.getItem('omni_session_id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem('omni_session_id', sessionId);
  }
  return sessionId;
}

// Helper to get theme from preferences API
async function getThemeFromPreferences(): Promise<Theme | null> {
  try {
    const sessionId = getSessionId();
    const response = await fetch(`/api/v1/preferences/${THEME_PREFERENCE_KEY}`, {
      headers: { 'x-session-id': sessionId },
    });

    if (response.ok) {
      const data = await response.json();
      return data.value as Theme;
    }
  } catch (error) {
    console.debug('[ThemeProvider] Failed to load theme from preferences:', error);
  }
  return null;
}

// Helper to save theme to preferences API
async function saveThemeToPreferences(theme: Theme): Promise<void> {
  try {
    const sessionId = getSessionId();
    await fetch('/api/v1/preferences', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id': sessionId,
      },
      body: JSON.stringify({
        key: THEME_PREFERENCE_KEY,
        value: theme,
      }),
    });
  } catch (error) {
    console.debug('[ThemeProvider] Failed to save theme to preferences:', error);
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light');
  const [isLoading, setIsLoading] = useState(true);

  // Load theme from preferences API on mount
  useEffect(() => {
    const loadTheme = async () => {
      const savedTheme = await getThemeFromPreferences();
      if (savedTheme) {
        setTheme(savedTheme);
      }
      setIsLoading(false);
    };

    loadTheme();
  }, []);

  // Apply theme to DOM and save to preferences
  useEffect(() => {
    if (isLoading) return; // Don't save during initial load

    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);

    // Save to preferences API (async, fire-and-forget)
    saveThemeToPreferences(theme);
  }, [theme, isLoading]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
