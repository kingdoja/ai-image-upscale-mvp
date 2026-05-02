import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";

export const metadata: Metadata = {
  title: "AI 产品图高清放大工具",
  description: "面向电商、广告和营销素材的 AI 图片 2x/4x 高清放大与评测工具。"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
