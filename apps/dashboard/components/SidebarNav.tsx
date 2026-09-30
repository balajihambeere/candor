"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { DecisionsIcon, HomeIcon, LedgerIcon, QueueIcon } from "./icons";

const LINKS = [
  { href: "/", label: "Overview", Icon: HomeIcon },
  { href: "/decisions", label: "All Decisions", Icon: DecisionsIcon },
  { href: "/review-queue", label: "Review Queue", Icon: QueueIcon },
  { href: "/disclosures", label: "Disclosure Ledger", Icon: LedgerIcon },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1 px-3">
      {LINKS.map(({ href, label, Icon }) => {
        const active = pathname === href || pathname?.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={`group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              active
                ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            }`}
          >
            <Icon
              className={`h-4.5 w-4.5 shrink-0 ${
                active
                  ? "text-indigo-600 dark:text-indigo-400"
                  : "text-slate-400 group-hover:text-slate-500 dark:text-slate-500 dark:group-hover:text-slate-400"
              }`}
            />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
