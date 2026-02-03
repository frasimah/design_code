"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Loader2, ArrowDownUp, Plus, Grid, LayoutGrid, List, Settings2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ProductCard } from "@/components/product-card";
import { Product, api } from "@/lib/api";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { cn } from "@/lib/utils";

export interface MaterialsViewProps {
    onBack: () => void;
    onProductClick: (product: Product) => void;
    onSave: (product: Product) => void;
    initialSource?: string;
    currencyMode?: 'original' | 'rub';
    exchangeRate?: number;
    onToggleCurrency?: () => void;
    accessToken?: string;
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

export function MaterialsView({
    onBack,
    onProductClick,
    onSave,
    initialSource,
    currencyMode = 'original',
    exchangeRate = 0,
    onToggleCurrency,
    accessToken
}: MaterialsViewProps) {
    const [query, setQuery] = useState("");
    const debouncedQuery = useDebounceValue(query, 500);
    const [availableSources, setAvailableSources] = useState<{ id: string, name: string }[]>([
        { id: 'catalog', name: 'Каталог' },
        { id: 'woocommerce', name: 'de-co-de.ru' }
    ]);
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [selectedBrands, setSelectedBrands] = useState<string[]>([]);

    // Use initialSource if provided, otherwise default to all (empty) or catalog
    // If initialSource is provided, we set selectedSources to just that source
    const [selectedSources, setSelectedSources] = useState<string[]>(initialSource ? [initialSource] : []);

    const [activeSort, setActiveSort] = useState<string>("relevance");
    const [viewMode, setViewMode] = useState<'grid' | 'large' | 'list'>('grid');
    const [visibleColumns, setVisibleColumns] = useState({
        photo: true,
        name: true,
        dimensions: true,
        materials: true,
        price: true
    });
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const [products, setProducts] = useState<Product[]>([]);
    const [totalCount, setTotalCount] = useState(0);
    const [loading, setLoading] = useState(true);

    // Infinite Scroll State
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);

    // Limit per page
    const LIMIT = 40;

    // Load available sources on mount
    useEffect(() => {
        api.getSources(accessToken).then(data => {
            setAvailableSources(data.map(s => ({ id: s.id, name: s.name })));
        }).catch(console.error);
    }, [accessToken]);

    // Reset when filters change
    useEffect(() => {
        setProducts([]);
        setPage(1);
        setHasMore(true);
        // We handle the actual fetch in the next effect which tracks page/filters
    }, [debouncedQuery, selectedCategory, selectedSources, activeSort, selectedBrands]);

    // Fetch products
    useEffect(() => {
        let active = true;

        async function fetchProducts() {
            setLoading(true);
            try {
                const offset = (page - 1) * LIMIT;
                // Pass category and brand
                // Join arrays with comma for API
                const sourceParam = selectedSources.length > 0 && !selectedSources.includes('all') ? selectedSources.join(',') : undefined;
                const brandParam = selectedBrands.length > 0 && !selectedBrands.includes('all') ? selectedBrands.join(',') : undefined;

                const response = await api.getProducts(
                    debouncedQuery,
                    LIMIT,
                    undefined,
                    sourceParam,
                    offset,
                    selectedCategory !== 'all' ? selectedCategory : undefined,
                    activeSort !== 'default' ? activeSort : undefined,
                    brandParam,
                    accessToken
                );
                const { items, total } = response;

                if (active) {
                    setTotalCount(total);
                    if (items.length < LIMIT) {
                        setHasMore(false);
                    }

                    if (page === 1) {
                        setProducts(items);
                    } else {
                        setProducts(prev => [...prev, ...items]);
                    }
                }
            } catch (error) {
                console.error("Failed to fetch products:", error);
                // Stop trying to load more if we hit an error to prevent infinite loop
                if (active) setHasMore(false);
            } finally {
                if (active) setLoading(false);
            }
        }

        if (hasMore) {
            fetchProducts();
        }

        return () => { active = false; };
        // Only trigger on filter changes or page increment, NOT on 'hasMore' alone to avoid loops
    }, [debouncedQuery, selectedCategory, selectedSources, page, activeSort, selectedBrands]);

    // Categories State
    const [categories, setCategories] = useState<{ value: string, label: string }[]>([
        { value: "all", label: "Все категории" }
    ]);

    // Fetch Categories when Source Changes
    useEffect(() => {
        async function loadCategories() {
            try {
                const sourceParam = selectedSources.length > 0 && !selectedSources.includes('all') ? selectedSources.join(',') : 'catalog';
                const data = await api.getCategories(sourceParam);
                setCategories(data.map(c => ({
                    value: c.id,
                    label: c.name
                })));
                // Reset selected category if it no longer exists
                setSelectedCategory("all");
            } catch (e) {
                console.error("Failed to load categories", e);
            }
        }
        loadCategories();
    }, [selectedSources]);

    // Brands State
    const [brands, setBrands] = useState<{ value: string, label: string }[]>([
        { value: "all", label: "Все бренды" }
    ]);

    // Fetch Brands when Source Changes
    useEffect(() => {
        async function loadBrands() {
            try {
                const sourceParam = selectedSources.length > 0 && !selectedSources.includes('all') ? selectedSources.join(',') : 'catalog';
                const data = await api.getBrands(sourceParam);
                setBrands([
                    { value: "all", label: "Все бренды" },
                    ...data.map(b => ({
                        value: b.id,
                        label: b.name
                    }))
                ]);
                setSelectedBrands(["all"]);
            } catch (e) {
                console.error("Failed to load brands", e);
            }
        }
        loadBrands();
    }, [selectedSources]);

    const [visibleCount, setVisibleCount] = useState(40);

    // Reset visible count when filters change
    useEffect(() => {
        setVisibleCount(40);
    }, [debouncedQuery, selectedCategory, selectedSources, products]);

    // Intersection Observer for Infinite Scroll
    const observerTarget = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !loading) {
                    setPage(prev => prev + 1);
                }
            },
            { threshold: 0.1 } // Trigger when 10% of the target is visible
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => {
            if (observerTarget.current) {
                observer.unobserve(observerTarget.current);
            }
        };
    }, [hasMore, loading]);

    return (
        <div className="h-full flex flex-col bg-[#faf9f5]">
            {/* Header */}
            <div className="px-8 py-8 md:py-10 max-w-[1920px] mx-auto w-full">
                {/* ... (Header content same as before) ... */}
                <div className="flex flex-col gap-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-baseline gap-3">
                            <h1 className="text-4xl font-serif text-[#141413]">Каталог</h1>
                            {!loading && (
                                <span className="text-lg text-muted-foreground font-medium">
                                    ({totalCount})
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Search and Sort Bar */}
                    <div className="flex items-center gap-3">
                        <div className="relative flex-1 max-w-xs">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Поиск..."
                                className="w-full h-10 pl-9 pr-4 rounded-full bg-white border border-[#1f1e1d0f] text-sm focus:outline-none focus:border-[#c6613f]/50 transition-colors placeholder:text-muted-foreground/60"
                            />
                        </div>

                        {/* Source Filter */}
                        <div className="relative">
                            <select
                                value={selectedSources.length > 0 ? selectedSources[0] : "all"}
                                onChange={(e) => setSelectedSources([e.target.value])}
                                className="h-10 pl-4 pr-10 rounded-full bg-white border border-[#1f1e1d0f] text-sm text-[#565552] focus:outline-none focus:border-[#c6613f]/50 appearance-none cursor-pointer hover:bg-neutral-50 transition-colors min-w-[120px]"
                            >
                                <option value="all">Все источники</option>
                                <option value="catalog">Каталог</option>
                                <option value="woocommerce">de-co-de.ru</option>
                                {availableSources.filter(s => !['catalog', 'woocommerce'].includes(s.id)).map(s => (
                                    <option key={s.id} value={s.id}>{s.name}</option>
                                ))}
                            </select>
                            <ArrowDownUp className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        </div>

                        {/* Brand Filter */}
                        <div className="relative">
                            <select
                                value={selectedBrands.length > 0 ? selectedBrands[0] : "all"}
                                onChange={(e) => setSelectedBrands([e.target.value])}
                                className="h-10 pl-4 pr-10 rounded-full bg-white border border-[#1f1e1d0f] text-sm text-[#565552] focus:outline-none focus:border-[#c6613f]/50 appearance-none cursor-pointer hover:bg-neutral-50 transition-colors min-w-[120px]"
                            >
                                {brands.map((b) => (
                                    <option key={b.value} value={b.value}>
                                        {b.label}
                                    </option>
                                ))}
                            </select>
                            <ArrowDownUp className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        </div>

                        {/* Category Filter */}
                        <div className="relative">
                            <select
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                                className="h-10 pl-4 pr-10 rounded-full bg-white border border-[#1f1e1d0f] text-sm text-[#565552] focus:outline-none focus:border-[#c6613f]/50 appearance-none cursor-pointer hover:bg-neutral-50 transition-colors min-w-[120px]"
                            >
                                {categories.map((c) => (
                                    <option key={c.value} value={c.value}>
                                        {c.label}
                                    </option>
                                ))}
                            </select>
                            <ArrowDownUp className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        </div>

                        <div className="relative">
                            <select
                                value={activeSort}
                                onChange={(e) => setActiveSort(e.target.value)}
                                className="h-10 pl-4 pr-10 rounded-full bg-white border border-[#1f1e1d0f] text-sm text-[#565552] focus:outline-none focus:border-[#c6613f]/50 appearance-none cursor-pointer hover:bg-neutral-50 transition-colors min-w-[120px]"
                            >
                                <option value="relevance">Сортировка</option>
                                <option value="price_asc">Цена ↑</option>
                                <option value="price_desc">Цена ↓</option>
                            </select>
                            <ArrowDownUp className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                        </div>

                        {/* View Mode Toggle */}
                        <div className="flex items-center gap-1 bg-white border border-[#1f1e1d0f] rounded-full p-1 h-10">
                            <button
                                onClick={() => setViewMode('list')}
                                className={cn(
                                    "p-1.5 rounded-full transition-colors",
                                    viewMode === 'list' ? "bg-[#c6613f] text-white" : "hover:bg-neutral-100 text-[#565552]"
                                )}
                                title="Список"
                            >
                                <List className="h-4 w-4" />
                            </button>
                            <button
                                onClick={() => setViewMode('large')}
                                className={cn(
                                    "p-1.5 rounded-full transition-colors",
                                    viewMode === 'large' ? "bg-[#c6613f] text-white" : "hover:bg-neutral-100 text-[#565552]"
                                )}
                                title="Крупно"
                            >
                                <Grid className="h-4 w-4" />
                            </button>
                            <button
                                onClick={() => setViewMode('grid')}
                                className={cn(
                                    "p-1.5 rounded-full transition-colors",
                                    viewMode === 'grid' ? "bg-[#c6613f] text-white" : "hover:bg-neutral-100 text-[#565552]"
                                )}
                                title="Сетка"
                            >
                                <LayoutGrid className="h-4 w-4" />
                            </button>
                        </div>

                        {/* Currency Toggle (Far Right) */}
                        {onToggleCurrency && (
                            <button
                                onClick={onToggleCurrency}
                                className={cn(
                                    "h-10 w-10 min-w-[40px] rounded-full border border-[#1f1e1d0f] flex items-center justify-center font-bold text-sm transition-colors ml-2",
                                    currencyMode === 'rub' ? "bg-[#c6613f] text-white hover:bg-[#b05535]" : "bg-white text-[#565552] hover:bg-neutral-50"
                                )}
                                title={currencyMode === 'rub' ? `Курс: ${exchangeRate} ₽` : "Показать в рублях"}
                            >
                                ₽
                            </button>
                        )}

                        {/* Column Settings Button (only in list mode) */}
                        {viewMode === 'list' && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setIsSettingsOpen(true)}
                                className="h-10 w-10 min-w-[40px] rounded-full bg-white border border-[#1f1e1d0f] text-[#565552] hover:text-[#141413] hover:bg-neutral-50 shadow-sm"
                                title="Настройка столбцов"
                            >
                                <Settings2 className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
            </div>

            {/* Grid Content */}
            <div
                className="flex-1 overflow-y-auto px-8 pb-12"
            // No onScroll needed with IntersectionObserver
            >
                <div className="max-w-[1920px] mx-auto">
                    {loading && products.length === 0 ? (
                        <div className="flex items-center justify-center h-64">
                            <Loader2 className="h-8 w-8 animate-spin text-[#c6613f]" />
                        </div>
                    ) : (
                        <>
                            {/* List View Headers */}
                            {viewMode === 'list' && products.length > 0 && (
                                <div className="flex flex-row items-center gap-4 px-3 py-2 border-b border-[#1f1e1d0f] text-[10px] font-bold text-[#565552] uppercase tracking-wider bg-neutral-50/50">
                                    {visibleColumns.photo && <div className="w-10 shrink-0 text-center">Фото</div>}
                                    <div
                                        className="flex-1 grid gap-4 items-center"
                                        style={{
                                            gridTemplateColumns: (() => {
                                                const cols: string[] = [];
                                                if (visibleColumns.name) cols.push("4fr");
                                                if (visibleColumns.dimensions) cols.push("3fr");
                                                if (visibleColumns.materials) cols.push("3fr");
                                                if (visibleColumns.price) cols.push("2fr");
                                                return cols.join(" ");
                                            })()
                                        }}
                                    >
                                        {visibleColumns.name && <div>Наименование</div>}
                                        {visibleColumns.dimensions && <div>Размеры</div>}
                                        {visibleColumns.materials && <div>Материалы</div>}
                                        {visibleColumns.price && <div className="text-right pr-4">Цена</div>}
                                    </div>
                                    <div className="w-7 shrink-0" /> {/* Spacer for bookmark button */}
                                </div>
                            )}

                            <div className={cn(
                                "grid",
                                viewMode === 'list'
                                    ? "grid-cols-1 gap-0 bg-white rounded-xl border border-[#1f1e1d0a] overflow-hidden"
                                    : viewMode === 'large'
                                        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-10"
                                        : "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-x-6 gap-y-10"
                            )}>
                                {products.map((product, index) => (
                                    <div key={`${product.slug}-${index}`} className={cn("w-full", viewMode !== 'list' && "flex justify-center")}>
                                        <ProductCard
                                            product={product}
                                            onSave={onSave}
                                            onClick={onProductClick}
                                            className="w-full"
                                            viewMode={viewMode}
                                            visibleColumns={visibleColumns}
                                            currencyMode={currencyMode}
                                            exchangeRate={exchangeRate}
                                            accessToken={accessToken}
                                        />
                                    </div>
                                ))}
                            </div>

                            {/* Loader at the bottom when loading more */}
                            {loading && products.length > 0 && (
                                <div className="flex items-center justify-center py-8 w-full">
                                    <Loader2 className="h-6 w-6 animate-spin text-[#c6613f]" />
                                </div>
                            )}

                            {/* Intersection Observer Target */}
                            {!loading && hasMore && <div ref={observerTarget} className="h-10 w-full" />}

                            {/* Manual Load More for reliability */}
                            {!loading && hasMore && products.length > 0 && (
                                <div className="flex justify-center py-8">
                                    <Button
                                        onClick={() => setPage(prev => prev + 1)}
                                        variant="outline"
                                        className="rounded-full px-8 border-[#1f1e1d0f] text-[#565552] hover:bg-neutral-50"
                                    >
                                        Загрузить еще
                                    </Button>
                                </div>
                            )}

                            {!loading && products.length === 0 && (
                                <div className="text-center py-20 text-muted-foreground">
                                    Ничего не найдено
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Column Settings Modal */}
            <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
                <DialogContent className="max-w-md bg-white p-0 overflow-hidden rounded-2xl border-0 shadow-2xl">
                    <DialogHeader className="p-6 pb-4 border-b border-[#1f1e1d0f]">
                        <DialogTitle className="text-xl font-semibold text-[#141413]">Настройка столбцов</DialogTitle>
                    </DialogHeader>
                    <div className="p-6 space-y-4">
                        {[
                            { id: 'photo', label: 'Фото' },
                            { id: 'name', label: 'Наименование' },
                            { id: 'dimensions', label: 'Размеры' },
                            { id: 'materials', label: 'Материалы' },
                            { id: 'price', label: 'Цена' }
                        ].map((col) => (
                            <div key={col.id} className="flex items-center justify-between py-2">
                                <span className="text-sm font-medium text-[#565552]">{col.label}</span>
                                <button
                                    onClick={() => setVisibleColumns(prev => ({
                                        ...prev,
                                        [col.id]: !prev[col.id as keyof typeof prev]
                                    }))}
                                    className={cn(
                                        "w-11 h-6 rounded-full transition-all duration-200 relative focus:outline-none ring-offset-2 focus:ring-2 focus:ring-[#c6613f]/20",
                                        visibleColumns[col.id as keyof typeof visibleColumns] ? "bg-[#c6613f]" : "bg-neutral-200"
                                    )}
                                >
                                    <div className={cn(
                                        "absolute top-1 w-4 h-4 rounded-full bg-white transition-all duration-200 shadow-sm",
                                        visibleColumns[col.id as keyof typeof visibleColumns] ? "left-6" : "left-1"
                                    )} />
                                </button>
                            </div>
                        ))}
                    </div>
                    <div className="p-6 pt-2 bg-neutral-50 flex justify-end">
                        <Button onClick={() => setIsSettingsOpen(false)} className="bg-[#141413] hover:bg-[#2a2a29] text-white rounded-full px-6">
                            Готово
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
