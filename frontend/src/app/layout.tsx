import type { Metadata } from "next";
import { Noto_Sans_KR } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

const notoSansKr = Noto_Sans_KR({
  display: "swap",
  preload: false,
  variable: "--font-noto-sans-kr",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "고객 요청 대응 플랫폼 | VOC 아카이브",
  description: "사내 고객 VOC 검색 아카이브",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="ko" className={notoSansKr.variable}><body>{children}</body></html>;
}
