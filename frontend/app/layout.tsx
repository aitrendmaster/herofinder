import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hero Finder",
  description: "B2B 인플루언서 매칭 플랫폼 — PTK",
};

const NAV = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/discovery", label: "인플루언서 탐색" },
  { href: "/brief", label: "RFP 작성" },
  { href: "/recommend", label: "AI 추천" },
  { href: "/messages", label: "메시지함" },
  { href: "/creator", label: "크리에이터" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full bg-white text-neutral-900">
        <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
            <Link href="/" className="text-lg font-bold tracking-tight">
              HERO<span className="text-neutral-400">FINDER</span>
            </Link>
            <nav className="flex items-center gap-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-black"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
