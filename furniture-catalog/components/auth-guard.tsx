"use client"

import { useSession } from "next-auth/react"
import { useRouter, usePathname } from "next/navigation"
import { useEffect } from "react"

// Pages that don't require authentication
const PUBLIC_PATHS = ["/auth/signin", "/auth/error"]

interface AuthGuardProps {
    children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
    const { data: session, status } = useSession()
    const router = useRouter()
    const pathname = usePathname()

    const isPublicPath = PUBLIC_PATHS.some(path => pathname?.startsWith(path))

    useEffect(() => {
        // Don't redirect if on public path or still loading
        if (isPublicPath || status === "loading") return

        // Redirect to signin if not authenticated
        if (status === "unauthenticated") {
            router.push("/auth/signin")
        }
    }, [status, isPublicPath, router])

    // Show loading state while checking auth
    if (status === "loading") {
        return (
            <div className="min-h-screen bg-[#FAF9F7] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-[#3D3929] border-t-transparent rounded-full animate-spin" />
                    <p className="text-[#595853] text-sm">Загрузка...</p>
                </div>
            </div>
        )
    }

    // Show nothing while redirecting to signin
    if (!isPublicPath && status === "unauthenticated") {
        return (
            <div className="min-h-screen bg-[#FAF9F7] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-[#3D3929] border-t-transparent rounded-full animate-spin" />
                    <p className="text-[#595853] text-sm">Перенаправление...</p>
                </div>
            </div>
        )
    }

    // Render children for authenticated users or public paths
    return <>{children}</>
}
