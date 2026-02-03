"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Link as LinkIcon, AlertCircle } from "lucide-react";
import { Product } from "@/lib/api";

interface UrlInputModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onProductAdded: (product: Product) => void;
}

export function UrlInputModal({ open, onOpenChange, onProductAdded }: UrlInputModalProps) {
    const [url, setUrl] = useState("");
    const [priceInstruction, setPriceInstruction] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string>("Ожидание ссылки...");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url.trim()) return;

        setLoading(true);
        setError(null);
        setStatus("Инициализация парсера...");

        try {
            const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            const response = await fetch(`${apiBaseUrl}/api/import-url/parse/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, price_instruction: priceInstruction })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to process URL");
            }

            const productData = await response.json();

            setStatus("Готово!");
            await new Promise(resolve => setTimeout(resolve, 500));

            // Map the API result to the Product interface
            onProductAdded(productData);
            onOpenChange(false);
            setUrl("");
            setPriceInstruction("");

        } catch (err) {
            console.error(err);
            setError(err instanceof Error ? err.message : "Не удалось обработать ссылку");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-xl bg-white p-0 overflow-hidden rounded-2xl border-0 shadow-2xl">
                <DialogHeader className="p-6 pb-4 border-b border-[#1f1e1d0f]">
                    <DialogTitle className="text-xl font-semibold text-[#141413] flex items-center gap-2">
                        <LinkIcon className="h-5 w-5 text-[#c6613f]" />
                        Добавить по ссылке
                    </DialogTitle>
                </DialogHeader>

                <div className="p-6">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-8 gap-4">
                            <div className="relative">
                                <div className="absolute inset-0 bg-[#c6613f]/20 rounded-full animate-ping" />
                                <div className="relative bg-white p-3 rounded-full border border-[#c6613f]/20 shadow-sm">
                                    <Loader2 className="h-8 w-8 text-[#c6613f] animate-spin" />
                                </div>
                            </div>
                            <div className="text-center space-y-1">
                                <div className="font-medium text-[#141413]">{status}</div>
                                <div className="text-sm text-muted-foreground">Это может занять до 30 секунд</div>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-[#565552]">Ссылка на товар</label>
                                <Input
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    placeholder="https://..."
                                    className="rounded-xl border-[#1f1e1d1a] focus-visible:ring-[#c6613f]"
                                    disabled={loading}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-[#565552]">
                                    Цена <span className="text-neutral-400 font-normal">(опционально)</span>
                                </label>
                                <Input
                                    value={priceInstruction}
                                    onChange={(e) => setPriceInstruction(e.target.value)}
                                    placeholder="Например: +20% или 3000 EUR"
                                    className="rounded-xl border-[#1f1e1d1a] focus-visible:ring-[#c6613f]"
                                    disabled={loading}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Можно указать формулу (напр. &quot;+20%&quot;) или фиксированную цену.
                                </p>
                            </div>
                            {error && (
                                <div className="flex items-center gap-2 text-sm text-red-500 bg-red-50 p-2 rounded-lg">
                                    <AlertCircle className="h-4 w-4 shrink-0" />
                                    <span>{error}</span>
                                </div>
                            )}

                            <div className="pt-2 flex justify-end gap-2">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => onOpenChange(false)}
                                    className="rounded-full"
                                >
                                    Отмена
                                </Button>
                                <Button
                                    type="submit"
                                    disabled={!url.trim() || loading}
                                    className="bg-[#c6613f] hover:bg-[#b05232] text-white rounded-full px-6"
                                >
                                    Обработать
                                </Button>
                            </div>
                        </form>
                    )}
                </div>
            </DialogContent>
        </Dialog >
    );
}
