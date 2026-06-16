// mssclaw WebUI — Root Layout
// 吸收模式: Dashboard Starter (sidebar) + LobeChat (theme toggle)
// 吸收来源: github.com/Kiranism/next-shadcn-dashboard-starter

import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarNav } from "@/components/sidebar-nav";
import { CommandPalette } from "@/components/command-palette";
import { Toaster } from "@/components/ui/toaster";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "mssclaw — AI Agent Framework",
  description: "MSS-AI agent management dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark">
          <div className="flex h-screen overflow-hidden">
            <SidebarNav />
            <main className="flex-1 overflow-y-auto bg-background">
              <div className="container mx-auto p-6">{children}</div>
            </main>
          </div>
          <CommandPalette />
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
