"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { api, UserProfile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader2, ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [syncStatus, setSyncStatus] = useState<any>(null);


    const [profile, setProfile] = useState<UserProfile>({
        manager_name: "",
        phone: "",
        email: "",
        company_name: ""
    });
    const accessToken = (session as any)?.accessToken;

    useEffect(() => {
        if (!accessToken) return;

        const checkStatus = async () => {
            try {
                const status = await api.getSyncStatus(accessToken);
                setSyncStatus(status);
                if (status.is_running) {
                    setSyncing(true);
                } else if (syncing && status.status !== 'running') {
                    setSyncing(false);
                }
            } catch (e) {
                console.error(e);
            }
        };

        checkStatus();
        const interval = setInterval(checkStatus, 3000);
        return () => clearInterval(interval);
    }, [accessToken]);

    useEffect(() => {
        // Safety timeout: stop loading after 2 seconds regardless of status
        const timeoutId = setTimeout(() => {
            setLoading(false);
        }, 2000);

        if (status === "loading") return;

        if (status === "unauthenticated") {
            router.push("/auth/signin");
            return;
        }

        if (status === "authenticated") {
            if (accessToken) {
                const loadProfile = async () => {
                    try {
                        const data = await api.getProfile(accessToken);
                        setProfile(data);
                    } catch (error) {
                        console.error("Failed to load profile:", error);
                    } finally {
                        setLoading(false);
                    }
                };
                loadProfile();
            } else {
                console.warn("Session authenticated but no access token found");
                setLoading(false);
            }
        }

        return () => clearTimeout(timeoutId);
    }, [status, accessToken, router]);




    const handleSync = async () => {
        if (!accessToken) return;
        if (!confirm("Это запустит полную синхронизацию каталога с сайтом de-co-de.ru. Процесс может занять несколько минут и выполняется в фоне. Вы уверены?")) return;

        setSyncing(true);
        try {
            await api.syncWoocommerceCatalog(accessToken);
            alert("Синхронизация успешно запущена в фоновом режиме. Каталог товаров обновится автоматически через несколько минут.");
        } catch (error) {
            console.error("Sync failed:", error);
            alert("Ошибка запуска синхронизации: " + (error as Error).message);
        } finally {
            setSyncing(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!accessToken) {
            alert("Ошибка авторизации. Пожалуйста, перезагрузите страницу.");
            return;
        }

        setSaving(true);
        try {
            console.log("Saving profile...", profile);
            await api.saveProfile(profile, accessToken);
            // Show success feedback (could be toast)
            alert("Настройки сохранены!");
        } catch (error) {
            console.error("Failed to save profile:", error);
            alert("Ошибка при сохранении настроек: " + (error as Error).message);
        } finally {
            setSaving(false);
        }
    };

    if (status === "loading" || loading) {
        return (
            <div className="h-screen flex items-center justify-center bg-[#faf9f5]">
                <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#faf9f5] p-8">
            <div className="max-w-2xl mx-auto">
                <div className="mb-8">
                    <Link href="/" className="inline-flex items-center text-sm text-neutral-500 hover:text-neutral-800 mb-4">
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Назад к каталогу
                    </Link>
                    <h1 className="text-3xl font-serif text-[#141413]">Настройки профиля</h1>
                    <p className="text-neutral-500 mt-2">
                        Эти данные будут использоваться при формировании коммерческих предложений.
                    </p>
                </div>

                <div className="bg-white rounded-xl border border-[#E6E2DD] p-6 shadow-sm">
                    <form onSubmit={handleSave} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-[#141413]">
                                Имя менеджера
                            </label>
                            <input
                                type="text"
                                value={profile.manager_name}
                                onChange={(e) => setProfile({ ...profile, manager_name: e.target.value })}
                                placeholder="Например: Екатерина Курчевская"
                                className="w-full px-4 py-2 rounded-lg border border-[#E6E2DD] focus:outline-none focus:ring-2 focus:ring-neutral-200"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-[#141413]">
                                    Телефон
                                </label>
                                <input
                                    type="text"
                                    value={profile.phone}
                                    onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                                    placeholder="+7 999 000 0000"
                                    className="w-full px-4 py-2 rounded-lg border border-[#E6E2DD] focus:outline-none focus:ring-2 focus:ring-neutral-200"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-[#141413]">
                                    Email для КП
                                </label>
                                <input
                                    type="email"
                                    value={profile.email}
                                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                                    placeholder="example@de-co-de.ru"
                                    className="w-full px-4 py-2 rounded-lg border border-[#E6E2DD] focus:outline-none focus:ring-2 focus:ring-neutral-200"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-[#141413]">
                                Название компании (необязательно)
                            </label>
                            <input
                                type="text"
                                value={profile.company_name}
                                onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
                                placeholder="DE-CO-DE"
                                className="w-full px-4 py-2 rounded-lg border border-[#E6E2DD] focus:outline-none focus:ring-2 focus:ring-neutral-200"
                            />
                        </div>

                        <div className="pt-4 flex justify-end">
                            <Button
                                type="submit"
                                disabled={saving}
                                className="bg-[#141413] text-white hover:bg-[#2C2C2A]"
                            >
                                {saving ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Сохранение...
                                    </>
                                ) : (
                                    "Сохранить изменения"
                                )}
                            </Button>
                        </div>
                    </form>
                </div>

                <div className="bg-white rounded-xl border border-[#E6E2DD] p-6 shadow-sm mt-8">
                    <h2 className="text-lg font-medium text-[#141413] mb-4">Управление каталогом</h2>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-[#141413]">Синхронизация с WooCommerce</p>
                            <div className="text-xs text-neutral-500 mt-1">
                                {syncStatus && syncStatus.is_running ? (
                                    <span className="text-amber-600 font-medium">
                                        {syncStatus.message}
                                        {syncStatus.total_est > 0 ? ` (${syncStatus.fetched}/${syncStatus.total_est})` : ` (${syncStatus.fetched})`}
                                    </span>
                                ) : (
                                    syncStatus?.status === 'completed' ? (
                                        <span className="text-green-600">{syncStatus.message}</span>
                                    ) : (
                                        syncStatus?.status === 'error' ? (
                                            <span className="text-red-600">{syncStatus.message}: {syncStatus.error}</span>
                                        ) : (
                                            "Загружает свежие данные с сайта de-co-de.ru. Процесс выполняется в фоне."
                                        )
                                    )
                                )}
                            </div>
                        </div>
                        <Button
                            onClick={handleSync}
                            disabled={syncing}
                            variant="outline"
                            className="border-[#E6E2DD] hover:bg-[#faf9f5] text-[#141413]"
                        >
                            <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                            {syncing ? "Запуск..." : "Обновить выгрузку"}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
