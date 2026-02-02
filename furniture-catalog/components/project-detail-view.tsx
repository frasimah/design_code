"use client";

import { Product } from "@/lib/api";
import { ArrowLeft, MoreHorizontal, Share, ArrowDownUp, Plus } from "lucide-react";
import { Button } from "./ui/button";
import { ProductCard } from "./product-card";
import { useState } from "react";
import { UrlInputModal } from "./url-input-modal";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

interface Project {
    id: string;
    name: string;
    slug?: string;
    items: Product[];
}

interface ProjectDetailViewProps {
    project: Project;
    onBack: () => void;
    onProductClick: (product: Product) => void;
    onRemoveItem?: (product: Product) => void;
    onProductAdded?: (product: Product) => void;
    accessToken?: string;
}

export function ProjectDetailView({ project, onBack, onProductClick, onRemoveItem, onProductAdded, accessToken }: ProjectDetailViewProps) {
    const [isUrlModalOpen, setIsUrlModalOpen] = useState(false);
    const [itemToDelete, setItemToDelete] = useState<Product | null>(null);

    const handleProductAdded = (product: Product) => {
        if (onProductAdded) {
            onProductAdded(product);
        }
    };
    return (
        <div className="max-w-[calc(100%-2rem)] md:max-w-4xl mx-auto w-full py-8 pl-12 md:pl-0">
            {/* Header */}
            <div className="mb-8">
                {/* Top Action Bar */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex-1">
                        <Button
                            variant="ghost"
                            onClick={onBack}
                            className="bg-secondary/50 hover:bg-secondary text-[#565552] rounded-full h-10 w-10 p-0"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                    </div>

                    <div className="flex-1 flex flex-col items-center text-center">
                        <h1 className="text-[32px] font-bold text-[#141413] leading-tight mb-1">{project.name}</h1>
                        <div className="flex items-center gap-2 text-sm text-[#565552]">
                            <span>{project.items.length} пинов</span>
                        </div>
                    </div>

                    <div className="flex-1 flex justify-end gap-3">
                        <Button
                            className="bg-[#e9e9e9] hover:bg-[#dcdcdc] text-black font-medium border-0 rounded-full px-5 h-10 shadow-none"
                            onClick={async () => {
                                const slug = project.slug || project.id;
                                try {
                                    const headers: HeadersInit = {};
                                    if (accessToken) {
                                        headers['Authorization'] = `Bearer ${accessToken}`;
                                    }

                                    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
                                    const response = await fetch(`${apiBaseUrl}/api/print/${slug}`, { headers });

                                    if (!response.ok) {
                                        if (response.status === 401) {
                                            alert("Пожалуйста, авторизуйтесь для печати КП");
                                            return;
                                        }
                                        throw new Error("Failed to load PDF preview");
                                    }

                                    const html = await response.text();
                                    const win = window.open('', '_blank');
                                    if (win) {
                                        win.document.write(html);
                                        win.document.close();
                                    } else {
                                        alert("Разрешите всплывающие окна для просмотра КП");
                                    }
                                } catch (error) {
                                    console.error("Print error:", error);
                                    alert("Ошибка при формировании КП");
                                }
                            }}
                        >
                            Распечатать КП
                        </Button>
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:bg-black/5 text-[#141413]">
                            <MoreHorizontal className="h-5 w-5" />
                        </Button>
                    </div>
                </div>

                {/* Sub-header Controls */}
                <div className="flex items-center justify-between mt-8 mb-6">
                    <div className="flex gap-2">
                        <div className="flex -space-x-1.5 overflow-hidden">
                            <div className="w-8 h-8 rounded-full bg-[#c6613f] text-white flex items-center justify-center text-[10px] font-bold ring-2 ring-white z-10">AS</div>
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full bg-secondary/50 hover:bg-secondary text-[#565552]">
                            <Plus className="h-4 w-4" />
                        </Button>
                    </div>

                    <div className="flex gap-3">
                        <Button variant="secondary" className="bg-transparent hover:bg-black/5 text-black font-medium h-10 px-4 rounded-full">
                            <ArrowDownUp className="h-4 w-4 mr-2" />
                            Сортировка
                        </Button>
                        <Button
                            variant="secondary"
                            className="bg-transparent hover:bg-black/5 text-black font-medium h-10 px-4 rounded-full"
                            onClick={() => setIsUrlModalOpen(true)}
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Другие идеи
                        </Button>
                    </div>
                </div>
            </div>

            {/* Grid of Items */}
            {project.items.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed border-[#1f1e1d1a] rounded-xl bg-secondary/10">
                    <div className="text-muted-foreground mb-2">В этом проекте пока пусто</div>
                    <Button variant="link" onClick={onBack}>Найти что-нибудь интересное</Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                    {project.items.map((product, idx) => (
                        <div key={`${product.slug}-${idx}`} className="w-full">
                            <ProductCard
                                product={product}
                                onClick={onProductClick}
                                actionMode="delete"
                                onDelete={(p) => setItemToDelete(p)}
                                accessToken={accessToken}
                            />
                        </div>
                    ))}
                </div>
            )}

            <UrlInputModal
                open={isUrlModalOpen}
                onOpenChange={setIsUrlModalOpen}
                onProductAdded={handleProductAdded}
            />

            <Dialog open={!!itemToDelete} onOpenChange={(open) => !open && setItemToDelete(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Удаление товара</DialogTitle>
                        <DialogDescription>
                            Вы точно хотите удалить товар &quot;{itemToDelete?.title || itemToDelete?.name}&quot; из проекта?
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setItemToDelete(null)}>
                            Отмена
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={() => {
                                if (itemToDelete && onRemoveItem) {
                                    onRemoveItem(itemToDelete);
                                }
                                setItemToDelete(null);
                            }}
                        >
                            Удалить
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
