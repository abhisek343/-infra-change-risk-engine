import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Infra Change Risk Engine",
  description: "Pre-deploy infrastructure risk analysis, approvals, and report export for Terraform and Kubernetes changes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[#020817] text-slate-100">
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.08),transparent_35%)]">
          <div className="mx-auto grid min-h-screen w-full max-w-[1600px] lg:grid-cols-[260px_1fr]">
            <aside className="border-b border-white/10 bg-slate-950/70 px-6 py-8 backdrop-blur lg:border-r lg:border-b-0">
              <Link href="/" className="block">
                <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Infra Change</p>
                <h1 className="mt-2 text-2xl font-semibold text-white">Risk Engine</h1>
              </Link>
              <p className="mt-3 text-sm leading-6 text-white/55">
                Portfolio-grade change analysis for Terraform and Kubernetes rollouts.
              </p>
              <nav className="mt-8 flex flex-col gap-3 text-sm">
                <Link
                  href="/"
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/80 transition hover:border-cyan-400/40 hover:text-white"
                >
                  Dashboard
                </Link>
                <Link
                  href="/new"
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/80 transition hover:border-cyan-400/40 hover:text-white"
                >
                  New analysis
                </Link>
              </nav>
            </aside>
            <main className="px-6 py-8 lg:px-10">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
