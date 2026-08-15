import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Bandara Cool World Management System",
  description:
    "Bandara Cool World sales, inventory, service and accounting management system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
