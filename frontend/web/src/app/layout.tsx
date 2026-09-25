import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TrueTicket",
  description: "예매·유통·입장 전 생애주기를 커버하는 암표 방지 통합 플랫폼",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Providers>
          <header className="border-b border-zinc-200 dark:border-zinc-800">
            <nav className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4 text-sm">
              <Link href="/" className="font-semibold tracking-tight">
                TrueTicket
              </Link>
              <Link href="/events">이벤트</Link>
              <Link href="/my-tickets">마이 티켓</Link>
              <Link href="/report">신고</Link>
              <Link href="/notifications">알림</Link>
              <span className="ml-auto text-zinc-400">|</span>
              <Link href="/admin/dashboard">운영자 대시보드</Link>
            </nav>
          </header>
          <main className="flex flex-1 flex-col">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
