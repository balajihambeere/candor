export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect width="32" height="32" rx="8" fill="url(#candor-logo-gradient)" />
      <path
        d="M11 16.5L14.5 20L21.5 12.5"
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <defs>
        <linearGradient id="candor-logo-gradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366F1" />
          <stop offset="1" stopColor="#4338CA" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function QueueIcon({ className = "h-4.5 w-4.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <path
        d="M6 5h9M6 10h9M6 15h5M3 5h.01M3 10h.01M3 15h.01"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LedgerIcon({ className = "h-4.5 w-4.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <path
        d="M5 3.5h7.5L16 7v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M12 3.5V7h3.5" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7 10.5h6M7 13.5h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function LogoutIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <path
        d="M13 14.5v.75A1.75 1.75 0 0 1 11.25 17h-5.5A1.75 1.75 0 0 1 4 15.25v-10.5A1.75 1.75 0 0 1 5.75 3h5.5A1.75 1.75 0 0 1 13 4.75v.75"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16.5 10H8.25M16.5 10 13.75 7.25M16.5 10l-2.75 2.75"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function InboxZeroIcon({ className = "h-12 w-12" }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="6" y="14" width="36" height="26" rx="4" stroke="currentColor" strokeWidth="2" />
      <path d="M6 24h10l3 5h10l3-5h10" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M24 6v12m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function LedgerEmptyIcon({ className = "h-12 w-12" }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="6" width="28" height="36" rx="3" stroke="currentColor" strokeWidth="2" />
      <path d="M16 16h16M16 23h16M16 30h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function ArrowRightIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <path
        d="M3.5 8h9M8.5 4l4 4-4 4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
