
import { Inter } from "next/font/google";
import "./globals.css";

// Fallback font since Anthropic Sans is proprietary/local
const fontSans = Inter({
  subsets: ["latin"],
  variable: "--font-anthropic-sans",
});

export const metadata = {
  title: "Brick Catalog",
  description: "Vandersanden Brick Catalog",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${fontSans.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
