import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Etsy Research Tool",
  description: "Market research tool for Etsy sellers",
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
      <body className="min-h-full bg-white">
        <nav className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center gap-8">
            <Link href="/" className="text-xl font-bold text-orange-600">
              EtsyResearch
            </Link>
            <Link href="/keywords" className="text-gray-600 hover:text-gray-900">
              Keywords
            </Link>
            <Link href="/shops" className="text-gray-600 hover:text-gray-900">
              Competitors
            </Link>
            <Link href="/seo" className="text-gray-600 hover:text-gray-900">
              SEO Audit
            </Link>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
