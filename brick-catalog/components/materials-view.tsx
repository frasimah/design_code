"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Loader2, ArrowDownUp, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProductCard } from "@/components/product-card";
import { Product, api } from "@/lib/api";
import { useDebounce } from "@/lib/hooks/use-debounce";

export interface MaterialsViewProps {
    onBack?: () => void;
    onProductClick?: (product: Product) => void;
    onSave?: (product: Product) => void;
}

function useDebounceValue<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
}

export function MaterialsView({ onBack, onProductClick, onSave }: MaterialsViewProps) {
    const [query, setQuery] = useState("");
    const debouncedQuery = useDebounceValue(query, 500);
    const [selectedColor, setSelectedColor] = useState<string>("all");
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(false);

    // Fetch products when query or color changes
    useEffect(() => {
        let active = true;

        async function fetchProducts() {
            setLoading(true);
            try {
                // Pass selectedColor to API
                const data = await api.getProducts(debouncedQuery, 1000, selectedColor);
                if (active) {
                    setProducts(data);
                }
            } catch (error) {
                console.error("Failed to fetch products:", error);
            } finally {
                if (active) setLoading(false);
            }
        }

        fetchProducts();

        return () => { active = false; };
    }, [debouncedQuery, selectedColor]);

    const colors = [
        { value: "all", label: "Все цвета" },
        { value: "бежевый", label: "Бежевый" },
        { value: "белый", label: "Белый" },
        { value: "жёлтый", label: "Жёлтый" },
        { value: "зеленый", label: "Зеленый" },
        { value: "коричневый", label: "Коричневый" },
        { value: "красный", label: "Красный" },
        { value: "оранжевый", label: "Оранжевый" },
        { value: "пурпурный", label: "Пурпурный" },
        { value: "розовый", label: "Розовый" },
        { value: "серый", label: "Серый" },
        { value: "чёрный", label: "Чёрный" },
    ];

    return (
        <div className="h-full flex flex-col bg-[#faf9f5]">
            {/* Header */}
            <div className="px-8 py-8 md:py-10 max-w-[1920px] mx-auto w-full">
                <div className="flex flex-col gap-6">
                    <div className="flex items-center justify-between">
                        <h1 className="text-4xl font-serif text-[#141413]">Материалы</h1>
                    </div>

                    {/* Search and Sort Bar */}
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-xl">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Поиск по названию или артикулу..."
                                className="w-full h-10 pl-9 pr-4 rounded-full bg-white border border-[#1f1e1d0f] text-sm focus:outline-none focus:border-[#c6613f]/50 transition-colors placeholder:text-muted-foreground/60"
                            />
                        </div>

                        {/* Color Filter */}
                        <div className="relative">
                            <select
                                value={selectedColor}
                                onChange={(e) => setSelectedColor(e.target.value)}
                                className="h-10 pl-4 pr-10 rounded-full bg-white border border-[#1f1e1d0f] text-sm text-[#565552] focus:outline-none focus:border-[#c6613f]/50 appearance-none cursor-pointer hover:bg-neutral-50 transition-colors min-w-[140px]"
                            >
                                {colors.map((c) => (
                                    <option key={c.value} value={c.value}>
                                        {c.label}
                                    </option>
                                ))}
                            </select>
                            <ArrowDownUp className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        </div>

                        <Button variant="outline" className="gap-2 rounded-full h-10 px-5 border-[#1f1e1d0f] bg-white hover:bg-neutral-50 text-[#565552]">
                            <ArrowDownUp className="h-4 w-4" />
                            <span>Сортировка</span>
                        </Button>
                    </div>
                </div>
            </div>

            {/* Grid Content */}
            <div className="flex-1 overflow-y-auto px-8 pb-12">
                <div className="max-w-[1920px] mx-auto">
                    {loading && products.length === 0 ? (
                        <div className="flex items-center justify-center h-64">
                            <Loader2 className="h-8 w-8 animate-spin text-[#c6613f]" />
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-x-6 gap-y-10">
                            {products.map((product) => (
                                <div key={product.slug} className="w-full flex justify-center">
                                    <ProductCard
                                        product={product}
                                        onSave={onSave}
                                        onClick={onProductClick}
                                        className="w-full"
                                    />
                                </div>
                            ))}
                        </div>
                    )}

                    {!loading && products.length === 0 && (
                        <div className="text-center py-20 text-muted-foreground">
                            Ничего не найдено
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
