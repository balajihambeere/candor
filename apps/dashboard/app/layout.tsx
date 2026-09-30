import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";

import { logout } from "@/lib/actions";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "Candor Dashboard",
  description: "Review queue, decision detail, and disclosure ledger for the Candor pipeline.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const store = await cookies();
  const isLoggedIn = await verifySessionToken(store.get(SESSION_COOKIE)?.value);

  return (
    <html lang="en" className="h-full">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900 antialiased">
        {isLoggedIn && (
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
              <span className="text-lg font-bold">Candor</span>
              <nav className="flex items-center gap-6 text-sm font-medium">
                <Link href="/review-queue" className="hover:text-indigo-600">
                  Review Queue
                </Link>
                <Link href="/disclosures" className="hover:text-indigo-600">
                  Disclosure Ledger
                </Link>
                <form action={logout}>
                  <button type="submit" className="text-slate-500 hover:text-slate-800">
                    Log out
                  </button>
                </form>
              </nav>
            </div>
          </header>
        )}
        <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
