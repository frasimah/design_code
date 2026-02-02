"use client"

import { signIn, signOut, useSession } from "next-auth/react"
import { User, LogOut, LogIn } from "lucide-react"

export function AuthButton() {
    const { data: session, status } = useSession()

    if (status === "loading") {
        return (
            <div className="w-8 h-8 rounded-full bg-[#E6E2DD] animate-pulse" />
        )
    }

    if (session?.user) {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#E6E2DD]/50">
                    {session.user.image ? (
                        <img
                            src={session.user.image}
                            alt=""
                            className="w-6 h-6 rounded-full"
                        />
                    ) : (
                        <User className="w-4 h-4 text-[#3D3929]" />
                    )}
                    <span className="text-sm text-[#3D3929] max-w-[100px] truncate">
                        {session.user.name || session.user.email}
                    </span>
                </div>
                <button
                    onClick={() => signOut()}
                    className="p-2 rounded-lg hover:bg-[#E6E2DD]/50 transition-colors"
                    title="Выйти"
                >
                    <LogOut className="w-4 h-4 text-[#3D3929]" />
                </button>
            </div>
        )
    }

    return (
        <button
            onClick={() => signIn()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#3D3929] text-white hover:bg-[#3D3929]/90 transition-colors"
        >
            <LogIn className="w-4 h-4" />
            <span className="text-sm font-medium">Войти</span>
        </button>
    )
}
