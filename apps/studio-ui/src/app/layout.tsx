import "./globals.css";
import type { Metadata } from "next";
import { ThemeProvider } from "@/hooks/use-theme";

export const metadata: Metadata = {
  title: "Agentic DevStudio",
  description: "Multi-agent development assistant",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
