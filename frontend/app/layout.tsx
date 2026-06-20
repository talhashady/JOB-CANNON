import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Career Assistant - Land your next role",
  description:
    "A multi-agent AI that scrapes, verifies, matches, tailors, and tracks jobs for you. Stunning, fast, and smart.",
  metadataBase: new URL("https://ai-career-assistant.vercel.app"),
  openGraph: {
    title: "AI Career Assistant",
    description: "Your autonomous multi-agent career copilot.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
