import { useTheme } from "next-themes";
import { Moon, Sun, User, Bell, Lock } from "lucide-react";

export function SettingsTab() {
  const { theme, setTheme } = useTheme();

  return (
    <div 
      className="h-full overflow-auto"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 
          className="text-3xl font-semibold mb-8"
          style={{ color: 'var(--text-primary)' }}
        >
          Settings
        </h1>

        {/* Account Section */}
        <section className="mb-8">
          <h2 
            className="text-xl font-semibold mb-4"
            style={{ color: 'var(--text-primary)' }}
          >
            Account
          </h2>
          
          <div 
            className="p-6 rounded-2xl border space-y-4"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border)',
            }}
          >
            <div className="flex items-center gap-4">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center text-2xl"
                style={{ backgroundColor: 'var(--accent-primary)' }}
              >
                <span className="text-white">S</span>
              </div>
              <div className="flex-1">
                <div className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                  Shaurya Kumar
                </div>
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  shaurya@example.com
                </div>
              </div>
              <button
                className="px-4 py-2 rounded-xl transition-all duration-90 hover:scale-[0.98]"
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                }}
              >
                Edit Profile
              </button>
            </div>
          </div>
        </section>

        {/* Appearance Section */}
        <section className="mb-8">
          <h2 
            className="text-xl font-semibold mb-4"
            style={{ color: 'var(--text-primary)' }}
          >
            Appearance
          </h2>
          
          <div 
            className="p-6 rounded-2xl border"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border)',
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {theme === 'dark' ? (
                  <Moon className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
                ) : (
                  <Sun className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
                )}
                <div>
                  <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    Theme
                  </div>
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    Choose your preferred theme
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setTheme('light')}
                className="flex-1 p-4 rounded-xl border transition-all duration-120"
                style={{
                  backgroundColor: theme === 'light' ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                  borderColor: theme === 'light' ? 'var(--accent-primary)' : 'var(--border)',
                  color: theme === 'light' ? '#FFFFFF' : 'var(--text-primary)',
                }}
              >
                <Sun className="w-5 h-5 mx-auto mb-2" />
                <div className="text-sm font-medium">Light</div>
              </button>
              <button
                onClick={() => setTheme('dark')}
                className="flex-1 p-4 rounded-xl border transition-all duration-120"
                style={{
                  backgroundColor: theme === 'dark' ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                  borderColor: theme === 'dark' ? 'var(--accent-primary)' : 'var(--border)',
                  color: theme === 'dark' ? '#FFFFFF' : 'var(--text-primary)',
                }}
              >
                <Moon className="w-5 h-5 mx-auto mb-2" />
                <div className="text-sm font-medium">Dark</div>
              </button>
            </div>
          </div>
        </section>

        {/* Preferences Section */}
        <section className="mb-8">
          <h2 
            className="text-xl font-semibold mb-4"
            style={{ color: 'var(--text-primary)' }}
          >
            Preferences
          </h2>
          
          <div 
            className="rounded-2xl border divide-y"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border)',
            }}
          >
            <div className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
                <div>
                  <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    Notifications
                  </div>
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    Receive study reminders
                  </div>
                </div>
              </div>
              <label className="relative inline-block w-12 h-6">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div 
                  className="w-12 h-6 rounded-full peer-checked:bg-[var(--accent-primary)] transition-colors cursor-pointer"
                  style={{ backgroundColor: 'var(--bg-tertiary)' }}
                />
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-6" />
              </label>
            </div>

            <div className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <User className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
                <div>
                  <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    Study Reminders
                  </div>
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    Daily study notifications
                  </div>
                </div>
              </div>
              <label className="relative inline-block w-12 h-6">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div 
                  className="w-12 h-6 rounded-full peer-checked:bg-[var(--accent-primary)] transition-colors cursor-pointer"
                  style={{ backgroundColor: 'var(--bg-tertiary)' }}
                />
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-6" />
              </label>
            </div>
          </div>
        </section>

        {/* Security Section */}
        <section>
          <h2 
            className="text-xl font-semibold mb-4"
            style={{ color: 'var(--text-primary)' }}
          >
            Security
          </h2>
          
          <div 
            className="p-6 rounded-2xl border"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border)',
            }}
          >
            <div className="flex items-center gap-3 mb-4">
              <Lock className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
              <div>
                <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                  Change Password
                </div>
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  Update your password regularly
                </div>
              </div>
            </div>
            <button
              className="w-full px-4 py-3 rounded-xl transition-all duration-90 hover:scale-[0.99]"
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
              }}
            >
              Change Password
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
