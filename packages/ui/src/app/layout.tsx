import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Nav } from "@/components/nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "MitoRAG",
  description: "Cited, KG-grounded mitochondrial research assistant"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
