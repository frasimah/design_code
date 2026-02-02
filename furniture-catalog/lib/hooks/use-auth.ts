"use client"

import { useSession } from "next-auth/react"

/**
 * Hook to get JWT token for API calls.
 * Returns the session access token if user is authenticated.
 */
export function useAuthToken(): string | undefined {
    const { data: session } = useSession()

    // NextAuth stores the JWT in the session
    // We need to expose it to API calls
    return (session as any)?.accessToken
}

/**
 * Get session info for display
 */
export function useAuth() {
    const { data: session, status } = useSession()

    return {
        user: session?.user,
        isLoading: status === "loading",
        isAuthenticated: status === "authenticated",
    }
}
