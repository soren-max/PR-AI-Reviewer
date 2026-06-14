import type { Metadata } from 'next';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { APP_NAME } from '@/lib/constants';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: APP_NAME,
    template: `%s | ${APP_NAME}`,
  },
  description: 'AI-powered Pull Request review platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <ErrorBoundary>
          {/* Header */}
          <header className="border-b border-gray-200 bg-white/80 backdrop-blur-sm">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
              <a href="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
                  PR
                </div>
                <span className="text-lg font-semibold text-gray-900">{APP_NAME}</span>
              </a>
              <nav className="flex gap-4 text-sm">
                <a
                  href="/"
                  className="text-gray-600 transition-colors hover:text-gray-900"
                >
                  提交审核
                </a>
                <a
                  href="/reviews"
                  className="text-gray-600 transition-colors hover:text-gray-900"
                >
                  历史记录
                </a>
              </nav>
            </div>
          </header>

          {/* Main content */}
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>

          {/* Footer */}
          <footer className="border-t border-gray-200 bg-white/50">
            <div className="mx-auto max-w-6xl px-4 py-4 text-center text-xs text-gray-400">
              {APP_NAME} v0.1.0 — Powered by DeepSeek V4 Pro
            </div>
          </footer>
        </ErrorBoundary>
      </body>
    </html>
  );
}
