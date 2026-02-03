import { useState } from "react";
import Image from "next/image";
import { Product, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { BookmarkPlus, Trash2, Pencil, Check, X, Camera } from "lucide-react";

import { cn } from "@/lib/utils";

interface ProductCardProps {
    product: Product;
    onClick?: (product: Product) => void;
    onSave?: (product: Product) => void;
    className?: string;
    viewMode?: 'grid' | 'large' | 'list';
    visibleColumns?: {
        photo: boolean;
        name: boolean;
        dimensions: boolean;
        materials: boolean;
        price: boolean;
    };
    actionMode?: 'save' | 'delete';
    onDelete?: (product: Product) => void;
    currencyMode?: 'original' | 'rub';
    exchangeRate?: number;
    accessToken?: string;
}

export function ProductCard({
    product,
    onClick,
    onSave,
    className,
    viewMode = 'grid',
    visibleColumns = { photo: true, name: true, dimensions: true, materials: true, price: true },
    actionMode = 'save',
    onDelete,
    currencyMode = 'original',
    exchangeRate = 0,
    accessToken
}: ProductCardProps) {
    const [isEditingPrice, setIsEditingPrice] = useState(false);
    const [editPrice, setEditPrice] = useState<string>("");
    const [localPrice, setLocalPrice] = useState<{ value: number | null, currency: string }>({
        value: product.price || null,
        currency: product.currency || 'EUR'
    });

    // Image state
    const [localImage, setLocalImage] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const file = e.target.files[0];
        setIsUploading(true);

        try {
            // 1. Upload image
            const { url } = await api.uploadImage(file, accessToken);

            // 2. Update product
            await api.updateProductImage(product.slug || '', url, accessToken);

            // 3. Update local state
            setLocalImage(url);
        } catch (err) {
            console.error("Failed to update image", err);
            alert("Не удалось обновить фото");
        } finally {
            setIsUploading(false);
        }
    };

    const handleStartEdit = (e: React.MouseEvent) => {
        e.stopPropagation();
        setEditPrice(localPrice.value ? localPrice.value.toString() : "");
        setIsEditingPrice(true);
    };

    const handleSavePrice = async (e?: React.SyntheticEvent) => {
        if (e) e.stopPropagation();
        try {
            const val = parseFloat(editPrice.replace(',', '.'));
            if (isNaN(val)) {
                setIsEditingPrice(false);
                return;
            }

            await api.updateProductPrice(product.slug || '', val, localPrice.currency, accessToken);

            setLocalPrice({ ...localPrice, value: val });
            setIsEditingPrice(false);
        } catch (err) {
            console.error("Failed to update price", err);
            alert("Не удалось обновить цену");
        }
    };

    const handleCancelEdit = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsEditingPrice(false);
    };

    // Determine image source: try local state, then images array, then main_image
    const rawImageSrc = localImage || (product.images && product.images.length > 0 ? product.images[0] : product.main_image);
    const imageSrc = api.getProxyImageUrl(rawImageSrc);
    const title = product.title || product.name;
    const isList = viewMode === "list";

    // Extract parameters for list view
    const rawParams = (product as unknown as { parameters?: unknown }).parameters;
    const params: Record<string, unknown> =
        typeof rawParams === "object" && rawParams !== null
            ? (rawParams as Record<string, unknown>)
            : {};

    const readParam = (...keys: string[]) => {
        for (const key of keys) {
            const value = params[key];
            if (value === undefined || value === null) continue;
            if (typeof value === "string") return value;
            if (typeof value === "number" || typeof value === "boolean") return String(value);
            if (Array.isArray(value)) return value.map(v => (typeof v === "string" ? v : String(v))).join(", ");
            return String(value);
        }
        return "";
    };

    const dimensions = readParam("Размеры", "Dimensions");
    const materials = readParam("Материал", "Материалы", "Material", "Materials");

    // Prioritize local state
    let displayPrice: string | number = "";

    // Fallback for price value if not in localPrice but in params
    const priceRaw = readParam("Цена", "Price") || "0";
    const parsedPrice = parseFloat(priceRaw.replace(',', '.').replace(/[^\d.]/g, '')) || 0;
    const effectivePrice = localPrice.value || parsedPrice;

    if (currencyMode === 'rub' && effectivePrice > 0 && exchangeRate > 0) {
        // Convert to RUB and round to 1000
        const rubVal = effectivePrice * exchangeRate;
        const roundedRub = Math.round(rubVal / 1000) * 1000;
        displayPrice = `${roundedRub.toLocaleString('ru-RU')} ₽`;
    } else {
        displayPrice = localPrice.value
            ? `${localPrice.value.toLocaleString('de-DE')} ${localPrice.currency || 'EUR'}`
            : readParam("Цена", "Price");
    }

    const [isDeleted, setIsDeleted] = useState(false);

    const handleDeleteProduct = async (e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm(`Вы уверены, что хотите удалить товар "${title}"?`)) {
            try {
                // Call API
                await api.deleteProduct(product.slug || "", accessToken);
                setIsDeleted(true);
            } catch (err) {
                console.error("Failed to delete product", err);
                alert("Не удалось удалить товар");
            }
        }
    };

    if (isDeleted) return null;

    if (isList) {
        // Calculate grid layout based on visible columns
        // Standard spans: name (4), dimensions (3), materials (3), price (2) = 12
        const getGridTemplate = () => {
            const cols: string[] = [];
            if (visibleColumns.name) cols.push("4fr");
            if (visibleColumns.dimensions) cols.push("3fr");
            if (visibleColumns.materials) cols.push("3fr");
            if (visibleColumns.price) cols.push("2fr");
            return cols.join(" ");
        };

        return (
            <div
                className={cn(
                    "group flex flex-row items-center gap-4 w-full px-3 py-1.5 border-b border-[#1f1e1d0a] hover:bg-[#f7f6f3] transition-colors cursor-pointer",
                    className
                )}
                onClick={() => onClick?.({
                    ...product,
                    main_image: localImage || product.main_image,
                    images: localImage ? [localImage, ...(product.images || [])] : product.images,
                    price: localPrice.value || product.price,
                    currency: localPrice.currency || product.currency
                })}
            >
                {/* Thumbnail */}
                {visibleColumns.photo && (
                    <div className="relative w-10 h-10 rounded-md overflow-hidden bg-secondary/30 shrink-0">
                        {imageSrc ? (
                            <Image
                                src={imageSrc}
                                alt={title}
                                fill
                                unoptimized
                                sizes="40px"
                                className="object-cover"
                            />
                        ) : (
                            <div className="flex items-center justify-center h-full text-[8px] text-muted-foreground/40 font-medium bg-[#f0eee6]">
                                N/A
                            </div>
                        )}
                    </div>
                )}

                {/* Columns */}
                <div
                    className="flex-1 grid gap-4 items-center min-w-0"
                    style={{ gridTemplateColumns: getGridTemplate() }}
                >
                    {/* Title */}
                    {visibleColumns.name && (
                        <div className="min-w-0">
                            <h3 className="font-medium text-[14px] text-[#141413] truncate" title={title}>
                                {title}
                            </h3>
                        </div>
                    )}

                    {/* Dimensions */}
                    {visibleColumns.dimensions && (
                        <div className="min-w-0">
                            <p className="text-[13px] text-[#565552] truncate" title={dimensions}>
                                {dimensions}
                            </p>
                        </div>
                    )}

                    {/* Materials */}
                    {visibleColumns.materials && (
                        <div className="min-w-0">
                            <p className="text-[13px] text-[#565552] truncate" title={materials}>
                                {materials}
                            </p>
                        </div>
                    )}

                    {/* Price */}
                    {visibleColumns.price && (
                        <div className="text-right pr-4">
                            <span className="font-semibold text-[13px] text-[#141413] whitespace-nowrap">
                                {displayPrice}
                            </span>
                        </div>
                    )}
                </div>

                {/* Bookmark Button Overlay */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <Button
                        size="icon"
                        variant="ghost"
                        className={cn(
                            "h-7 w-7 rounded-md hover:bg-black/5",
                            actionMode === 'delete' ? "text-red-500 hover:text-red-600" : "text-[#565552] hover:text-[#141413]"
                        )}
                        onClick={(e) => {
                            e.stopPropagation();
                            if (actionMode === 'delete') {
                                onDelete?.(product);
                            } else {
                                onSave?.(product);
                            }
                        }}
                    >
                        {actionMode === 'delete' ? <Trash2 className="h-4 w-4" /> : <BookmarkPlus className="h-4 w-4" />}
                    </Button>
                </div>
            </div>
        );
    }

    // Grid / Large View
    return (
        <div
            className={cn(
                "group cursor-pointer transition-all duration-300 flex flex-col gap-2 w-full",
                className
            )}
            onClick={() => onClick?.({
                ...product,
                main_image: localImage || product.main_image,
                images: localImage ? [localImage, ...(product.images || [])] : product.images,
                price: localPrice.value || product.price,
                currency: localPrice.currency || product.currency
            })}
        >
            {/* Image Container */}
            <div className="relative rounded-2xl overflow-hidden bg-secondary/50 shrink-0 w-full aspect-[4/3]">
                {imageSrc ? (
                    <Image
                        src={imageSrc}
                        alt={title}
                        fill
                        unoptimized
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground/40 font-medium bg-[#f0eee6]">
                        Нет фото
                    </div>
                )}

                {/* Bookmark/Action Icon Overlay */}
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 flex gap-2">
                    <Button
                        size="icon"
                        variant="secondary"
                        className="h-8 w-8 rounded-full bg-white/90 hover:bg-white shadow-sm backdrop-blur-sm text-red-500 hover:text-red-600"
                        onClick={handleDeleteProduct}
                        title="Удалить товар"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>

                    <input
                        type="file"
                        id={`upload-${product.slug}`}
                        className="hidden"
                        accept="image/*"
                        onChange={handleImageUpload}
                        disabled={isUploading}
                        onClick={e => e.stopPropagation()}
                    />
                    <label htmlFor={`upload-${product.slug}`} onClick={e => e.stopPropagation()}>
                        <div className={cn(
                            "h-8 w-8 rounded-full bg-white/90 backdrop-blur-sm shadow-sm flex items-center justify-center cursor-pointer hover:bg-white text-neutral-600 hover:text-neutral-900 transition-colors",
                            isUploading && "opacity-50 cursor-wait"
                        )} title="Изменить фото">
                            <Camera className="h-4 w-4" />
                        </div>
                    </label>

                    <Button
                        size="icon"
                        variant="secondary"
                        className={cn(
                            "h-8 w-8 rounded-full bg-white/90 hover:bg-white shadow-sm backdrop-blur-sm",
                            actionMode === 'delete' ? "text-red-500 hover:text-red-600" : "text-[#141413]"
                        )}
                        onClick={(e) => {
                            e.stopPropagation();
                            if (actionMode === 'delete') {
                                onDelete?.(product);
                            } else {
                                onSave?.(product);
                            }
                        }}
                    >
                        {actionMode === 'delete' ? <Trash2 className="h-4 w-4" /> : <BookmarkPlus className="h-4 w-4" />}
                    </Button>
                </div>
            </div>

            {/* Content */}
            <div className="flex flex-col gap-0.5 mt-1 px-0.5">
                <h3 className="font-bold text-[15px] text-[#141413] leading-tight truncate" title={title}>
                    {title}
                </h3>

                {product.brand && (
                    <p className="text-[12px] text-[#868685] truncate font-medium leading-tight uppercase">
                        {product.brand}
                    </p>
                )}

                <div className="flex flex-col gap-1 h-7 justify-center">
                    {isEditingPrice ? (
                        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <input
                                type="text"
                                value={editPrice}
                                onChange={e => setEditPrice(e.target.value)}
                                className="w-20 text-[13px] border rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-ring bg-white"
                                autoFocus
                                onClick={e => e.stopPropagation()}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') handleSavePrice(e);
                                    if (e.key === 'Escape') setIsEditingPrice(false);
                                }}
                            />
                            <button onClick={handleSavePrice} className="text-green-600 hover:text-green-700 bg-white rounded-full p-0.5 shadow-sm"><Check className="h-3.5 w-3.5" /></button>
                            <button onClick={handleCancelEdit} className="text-red-500 hover:text-red-600 bg-white rounded-full p-0.5 shadow-sm"><X className="h-3.5 w-3.5" /></button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 group/price relative h-full">
                            {displayPrice ? (
                                <span className="font-semibold text-[13px] text-[#141413] whitespace-nowrap">
                                    {displayPrice}
                                </span>
                            ) : (
                                <button onClick={handleStartEdit} className="text-[11px] text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded-full">
                                    <Pencil className="h-3 w-3" /> Добавить цену
                                </button>
                            )}

                            {displayPrice && (
                                <button
                                    onClick={handleStartEdit}
                                    className="opacity-0 group-hover/price:opacity-100 transition-opacity p-1 text-muted-foreground hover:text-blue-600"
                                    title="Редактировать цену"
                                >
                                    <Pencil className="h-3 w-3" />
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Vision Confidence Badge */}
            {product.vision_confidence !== undefined && product.vision_confidence > 0 && (
                <div className="absolute top-3 left-3 bg-green-500/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm backdrop-blur-sm">
                    {(product.vision_confidence * 100).toFixed(0)}% Совпадение
                </div>
            )}
        </div>
    );
}
