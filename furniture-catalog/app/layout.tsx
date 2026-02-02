
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AuthGuard } from "@/components/auth-guard";

// Fallback font since Anthropic Sans is proprietary/local
const fontSans = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-anthropic-sans",
});

export const metadata = {
  title: "Design Code Panel",
  description: "Интеллектуальный каталог мебели с AI-консультантом",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className={`${fontSans.variable} font-sans`}>
        <Providers>
          <AuthGuard>
            {children}
          </AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
