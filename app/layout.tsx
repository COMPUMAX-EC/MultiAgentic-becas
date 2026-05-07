import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "BeeScholar Match",
  description: "Simple scholarship matching from your academic profile",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
