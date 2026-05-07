import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tracker",
  description: "Personal portfolio tracker",
};

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/positions", label: "Positions" },
  { href: "/connectors", label: "Connectors" },
  { href: "/history", label: "History" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-ink-200 bg-white">
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center gap-8">
            <span className="font-mono text-sm tracking-tight text-ink-900">tracker</span>
            <nav className="flex gap-6 text-sm">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className="text-ink-600 hover:text-ink-900">
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-6 text-xs text-ink-400">
          Values are indicative; per-source delays apply. No FX conversion.
        </footer>
      </body>
    </html>
  );
}
