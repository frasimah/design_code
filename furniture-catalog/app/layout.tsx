
import { Inter } from "next/font/google";
import "./globals.css";
import { ChatWidget } from "@/components/chat-widget/ChatWidget";

// Fallback font since Anthropic Sans is proprietary/local
const fontSans = Inter({
  subsets: ["latin"],
  variable: "--font-anthropic-sans",
});

export const metadata = {
  title: "Furniture Consultant",
  description: "Designer Furniture Consultant",
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
        {/* <ChatWidget /> */}
      </body>
    </html>
  );
}
