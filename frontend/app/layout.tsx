import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import ErrorLogger from "@/components/ErrorLogger";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "JOB CANNON - AI Career Assistant",
  description:
    "JOB CANNON: A multi-agent AI that scrapes, verifies, matches, tailors, and tracks jobs for you. Stunning, fast, and smart.",
  metadataBase: new URL("https://job-cannon.vercel.app"),
  openGraph: {
    title: "JOB CANNON - AI Career Assistant",
    description: "Your autonomous multi-agent career copilot.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <AuthProvider>{children}</AuthProvider>
        <ErrorLogger />
      </body>
    </html>
  );
}
