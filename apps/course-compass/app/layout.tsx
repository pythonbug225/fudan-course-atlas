import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "课途 · 复旦选课与成长规划",
  description: "公共与专业学分审计，多轮选课智能体与双方案比较。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
