import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "고객 요청 대응 플랫폼 | VOC 아카이브",
  description: "사내 고객 VOC 검색 아카이브",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
