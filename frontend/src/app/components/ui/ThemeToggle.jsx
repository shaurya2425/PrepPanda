import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="relative w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
      style={{
        backgroundColor: 'var(--bg-tertiary)',
        border: '1px solid var(--border)',
      }}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      <Sun
        className="w-[18px] h-[18px] transition-all duration-300"
        style={{
          color: 'var(--accent-warning)',
          opacity: theme === 'dark' ? 0 : 1,
          transform: theme === 'dark' ? 'rotate(-90deg) scale(0)' : 'rotate(0) scale(1)',
          position: 'absolute',
        }}
      />
      <Moon
        className="w-[18px] h-[18px] transition-all duration-300"
        style={{
          color: 'var(--accent-secondary)',
          opacity: theme === 'dark' ? 1 : 0,
          transform: theme === 'dark' ? 'rotate(0) scale(1)' : 'rotate(90deg) scale(0)',
          position: 'absolute',
        }}
      />
    </button>
  );
}
