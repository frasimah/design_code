import NextAuth from "next-auth"
import YandexProvider from "next-auth/providers/yandex"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"
import type { NextAuthOptions } from "next-auth"
import { encode } from "next-auth/jwt"

export const authOptions: NextAuthOptions = {
    providers: [
        // Yandex OAuth (primary for Russian users)
        YandexProvider({
            clientId: process.env.YANDEX_CLIENT_ID || "",
            clientSecret: process.env.YANDEX_CLIENT_SECRET || "",
        }),
        // Google OAuth (secondary)
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
        }),
        // Demo credentials for development
        CredentialsProvider({
            name: "Demo",
            credentials: {
                email: { label: "Email", type: "email", placeholder: "demo@example.com" },
            },
            async authorize(credentials) {
                // Only for development - allows login without OAuth setup
                if (credentials?.email) {
                    return {
                        id: `demo-${credentials.email}`,
                        email: credentials.email,
                        name: credentials.email.split("@")[0],
                    }
                }
                return null
            },
        }),
    ],
    pages: {
        signIn: "/auth/signin",
    },
    callbacks: {
        async jwt({ token, account, user }) {
            // Pass user ID, provider, and access token to JWT token
            if (account && user) {
                token.userId = user.id
                token.provider = account.provider
                // For OAuth providers, store the access token
                if (account.access_token) {
                    token.accessToken = account.access_token
                }
            }
            return token
        },
        async session({ session, token }) {
            // Include user ID and access token in session for API calls
            if (session.user) {
                (session.user as { id?: string }).id = token.userId as string
                (session.user as { provider?: string }).provider = token.provider as string
            }
            // Encode the full token as JWT for API authorization
            const encodedToken = await encode({
                token,
                secret: process.env.NEXTAUTH_SECRET || "development-secret-please-change-in-production",
            })
                ; (session as { accessToken?: string }).accessToken = encodedToken
            return session
        },
    },
    session: {
        strategy: "jwt",
    },
    secret: process.env.NEXTAUTH_SECRET,
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }

