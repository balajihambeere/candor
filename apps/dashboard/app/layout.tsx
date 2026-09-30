import type { Metadata } from "next";
import { cookies } from "next/headers";

import { logout } from "@/lib/actions";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";
import { LogoMark, LogoutIcon } from "@/components/icons";
import { SidebarNav } from "@/components/SidebarNav";
import { THEME_INIT_SCRIPT, ThemeToggle } from "@/components/ThemeToggle";

import "./globals.css";

export const metadata: Metadata = {
  title: "Candor Dashboard",
  description: "Review queue, decision detail, and disclosure ledger for the Candor pipeline.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await cookies();
  const isLoggedIn = await verifySessionToken(store.get(SESSION_COOKIE)?.value);

  if (!isLoggedIn) {
    return (
      <html lang="en" className="h-full" suppressHydrationWarning>
        <head>
          <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        </head>
        <body className="min-h-full bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
          {children}
        </body>
      </html>
    );
  }

  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex h-full bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2.5 px-5 py-5">
            <LogoMark className="h-8 w-8" />
            <div className="leading-tight">
              <div className="text-[15px] font-bold tracking-tight text-slate-900 dark:text-slate-100">Candor</div>
              <div className="text-[11px] font-medium text-slate-400">Decision Ops</div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto py-2">
            <div className="px-6 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Operate
            </div>
            <SidebarNav />
          </div>

          <div className="space-y-1 border-t border-slate-200 p-3 dark:border-slate-800">
            <ThemeToggle />
            <form action={logout}>
              <button
                type="submit"
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              >
                <LogoutIcon className="h-4 w-4" />
                Log out
              </button>
            </form>
          </div>
        </aside>

        <div className="flex h-full flex-1 flex-col overflow-y-auto">
          <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
