"use client";

import { useState } from "react";
import { Product, api } from "@/lib/api";
import { ArrowLeft, MoreHorizontal, Share, Download, Heart, BookmarkPlus, Trash2, GripVertical, FileText } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface ProductFullViewProps {
    product: Product;
    onBack: () => void;
    onSave?: (product: Product) => void;
}

export function ProductFullView({ product, onBack, onSave }: ProductFullViewProps) {
    const [isDetailsOpen, setIsDetailsOpen] = useState(false);
    const [isDescriptionOpen, setIsDescriptionOpen] = useState(false);

    // Combine main image and gallery
    // Combine all image sources
    const rawImages = [
        ...(product.images || []),
        product.main_image,
        ...(product.gallery || [])
    ].filter((img): img is string => !!img);

    // Deduplicate and proxy
    const images = Array.from(new Set(rawImages)).map(img => api.getProxyImageUrl(img));

    return (
        <div className="max-w-[calc(100%-2rem)] md:max-w-4xl mx-auto w-full py-8 pl-12 md:pl-0">
            {/* Header */}
            <div className="mb-8">
                {/* Top Action Bar */}
                <div className="flex items-center justify-between mb-6">
                    {/* Back Button */}
                    <div className="flex-1">
                        <Button
                            variant="ghost"
                            onClick={onBack}
                            className="bg-secondary/50 hover:bg-secondary text-[#565552] rounded-full h-10 w-10 p-0"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                    </div>

                    {/* Centered Title & Meta */}
                    <div className="flex-1 flex flex-col items-center text-center">
                        <h1 className="text-[32px] font-bold text-[#141413] leading-tight mb-1">{product.name}</h1>
                        <div className="flex items-center gap-2 text-sm text-[#565552]">
                            {/* Display price if available, with fallback to parameters */}
                            {(() => {
                                let price = product.price;
                                let currency = product.currency || 'EUR';

                                if (!price) {
                                    // Fallback to parameters
                                    const params = product.parameters || {};
                                    const priceParam = params['Цена'] || params['Price'];
                                    if (priceParam) {
                                        const parsed = parseFloat(String(priceParam).replace(',', '.').replace(/[^\d.]/g, ''));
                                        if (!isNaN(parsed) && parsed > 0) {
                                            price = parsed;
                                        } else {
                                            // If parse fails, return raw string if it looks like price?
                                            // simpler to prioritize parsed.
                                        }
                                    }
                                }

                                return (
                                    <span>{price ? `${price.toLocaleString()} ${currency}` : "Цена не указана"}</span>
                                );
                            })()}
                        </div>
                    </div>

                    {/* Right Actions */}
                    <div className="flex-1 flex justify-end gap-3">
                        <Button
                            variant="secondary"
                            className="bg-[#e9e9e9] hover:bg-[#dcdcdc] text-black font-medium border-0 rounded-full px-5 h-10 shadow-none gap-2"
                            onClick={() => onSave?.(product)}
                        >
                            <Heart className="h-4 w-4" />
                            <span>Сохранить</span>
                        </Button>
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:bg-black/5 text-[#141413]" onClick={() => setIsDescriptionOpen(true)} title="Полное описание">
                            <FileText className="h-5 w-5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:bg-black/5 text-[#141413]" onClick={() => setIsDetailsOpen(true)}>
                            <MoreHorizontal className="h-5 w-5" />
                        </Button>
                    </div>
                </div>

                {/* Sub-header Controls / Description */}
                <div className="flex flex-col items-center text-center max-w-2xl mx-auto mt-4 mb-8">
                    {/* Optional: Add description snippet if available */}
                    {/* Optional: Add description snippet if available */}
                    {product.description && (
                        <div
                            className="text-[#565552] text-sm leading-relaxed line-clamp-2 prose prose-sm max-w-none [&>p]:m-0 [&>p]:inline"
                            dangerouslySetInnerHTML={{ __html: product.description }}
                        />
                    )}

                    <div className="flex items-center gap-4 mt-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {product.color?.base_color && (
                            <span className="px-3 py-1 bg-secondary/30 rounded-full">
                                {product.color.base_color}
                            </span>
                        )}
                        {product.texture && (
                            <span className="px-3 py-1 bg-secondary/30 rounded-full">
                                {product.texture}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Grid of Images */}
            {images.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed border-[#1f1e1d1a] rounded-xl bg-secondary/10">
                    <div className="text-muted-foreground">Нет изображений</div>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    {images.map((img, idx) => (
                        <div
                            key={idx}
                            className="relative rounded-xl overflow-hidden group bg-secondary/20 shadow-sm hover:shadow-md transition-all"
                        >
                            <Image
                                src={img}
                                alt={`${product.name} ${idx + 1}`}
                                width={500}
                                height={500}
                                unoptimized
                                className="w-full h-auto object-cover transition-transform duration-500 group-hover:scale-105"
                                sizes="(max-width: 768px) 100vw, 33vw"
                            />
                            {/* Reorder Button - Left side */}
                            <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                <Button
                                    size="icon"
                                    variant="secondary"
                                    className="h-8 w-8 rounded-full bg-white/90 hover:bg-white text-[#141413] shadow-sm backdrop-blur-sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        if (onSave && images.length > 1) {
                                            const newImages = [...images];
                                            // Move image one position to the left (earlier in array)
                                            // If first, wrap to end
                                            if (idx === 0) {
                                                // Move first to end
                                                const [first] = newImages.splice(0, 1);
                                                newImages.push(first);
                                            } else {
                                                // Swap with previous
                                                [newImages[idx - 1], newImages[idx]] = [newImages[idx], newImages[idx - 1]];
                                            }
                                            onSave({
                                                ...product,
                                                images: newImages,
                                                main_image: newImages[0]
                                            });
                                        }
                                    }}
                                >
                                    <GripVertical className="h-4 w-4" />
                                </Button>
                            </div>
                            {/* Action Buttons - Right side */}
                            <div className="absolute top-2 right-2 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                {/* Delete Photo */}
                                <Button
                                    size="icon"
                                    variant="secondary"
                                    className="h-8 w-8 rounded-full bg-white/90 hover:bg-red-50 text-[#141413] hover:text-red-600 shadow-sm backdrop-blur-sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        // Remove this image from the product
                                        if (onSave) {
                                            const updatedImages = images.filter((_, i) => i !== idx);
                                            onSave({
                                                ...product,
                                                images: updatedImages,
                                                main_image: updatedImages[0] || undefined
                                            });
                                        }
                                    }}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                                {/* Save as Main */}
                                <Button
                                    size="icon"
                                    variant="secondary"
                                    className="h-8 w-8 rounded-full bg-white/90 hover:bg-white text-[#141413] shadow-sm backdrop-blur-sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onSave?.({
                                            ...product,
                                            main_image: img
                                        });
                                    }}
                                >
                                    <BookmarkPlus className="h-4 w-4" />
                                </Button>
                            </div>
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors duration-300 pointer-events-none" />
                        </div>
                    ))}
                </div>
            )}

            {/* Product Details Modal */}
            <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
                <DialogContent
                    className="bg-[#faf9f5] border-[#1f1e1d0f] rounded-xl shadow-2xl overflow-hidden p-0 gap-0"
                    style={{ width: '90vw', maxWidth: '1200px' }}
                >
                    <DialogHeader className="px-6 py-4 border-b border-[#1f1e1d0f] flex flex-row items-center justify-between bg-white backdrop-blur-md">
                        <DialogTitle className="text-lg font-bold text-[#141413]">
                            Характеристики
                        </DialogTitle>
                    </DialogHeader>

                    <div className="p-6 overflow-y-auto max-h-[70vh] scrollbar-thin">
                        <div className="space-y-3">
                            {/* Article - always show first */}
                            <div className="flex justify-between items-baseline gap-4 text-[14px]">
                                <span className="text-[#888886] shrink-0">Артикул</span>
                                <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                <span className="text-[#141413] font-medium text-right shrink-0 max-w-[60%]">{product.article || "—"}</span>
                            </div>

                            {/* Brand */}
                            {product.brand && (
                                <div className="flex justify-between items-baseline gap-4 text-[14px]">
                                    <span className="text-[#888886] shrink-0">Бренд</span>
                                    <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                    <span className="text-[#141413] font-medium text-right shrink-0">{product.brand}</span>
                                </div>
                            )}

                            {/* Parameters (technical specs) - filtered to avoid duplicates */}
                            {product.parameters && Object.entries(product.parameters)
                                .filter(([key]) => {
                                    const lowerKey = key.toLowerCase();
                                    // Skip keys that are already displayed explicitly
                                    const skipKeys = ['артикул', 'article', 'цена', 'price', 'бренд', 'brand', 'источник', 'source'];
                                    return !skipKeys.includes(lowerKey);
                                })
                                .map(([key, value]) => (
                                    <div key={`param-${key}`} className="flex justify-between items-baseline gap-4 text-[14px]">
                                        <span className="text-[#888886] shrink-0">{key}</span>
                                        <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                        <span className="text-[#141413] font-medium text-right shrink-0 max-w-[60%]">{String(value)}</span>
                                    </div>
                                ))}

                            {/* Attributes (WooCommerce/dynamic) - filtered to avoid duplicates with parameters */}
                            {product.attributes && Object.entries(product.attributes)
                                .filter(([key]) => {
                                    const lowerKey = key.toLowerCase();
                                    // Skip keys that are already displayed explicitly
                                    const skipKeys = ['артикул', 'article', 'цена', 'price', 'бренд', 'brand', 'источник', 'source'];
                                    if (skipKeys.includes(lowerKey)) return false;
                                    // Also skip if already in parameters
                                    if (product.parameters && Object.keys(product.parameters).some(pKey => pKey.toLowerCase() === lowerKey)) return false;
                                    return true;
                                })
                                .map(([key, value]) => (
                                    <div key={`attr-${key}`} className="flex justify-between items-baseline gap-4 text-[14px]">
                                        <span className="text-[#888886] shrink-0">{key}</span>
                                        <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                        <span className="text-[#141413] font-medium text-right shrink-0 max-w-[60%]">{String(value)}</span>
                                    </div>
                                ))}

                            {/* Source */}
                            {product.source && (
                                <div className="flex justify-between items-baseline gap-4 text-[14px]">
                                    <span className="text-[#888886] shrink-0">Источник</span>
                                    <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                    <span className="text-[#141413] font-medium text-right shrink-0">{product.source}</span>
                                </div>
                            )}

                            {/* Price - always show last */}
                            {product.price && (
                                <div className="flex justify-between items-baseline gap-4 text-[14px]">
                                    <span className="text-[#888886] shrink-0">Цена</span>
                                    <div className="h-[1px] flex-1 bg-[#1f1e1d1a] translate-y-[-4px]" />
                                    <span className="text-[#141413] font-medium text-right shrink-0">
                                        {product.price.toLocaleString()} {product.currency || 'RUB'}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <Dialog open={isDescriptionOpen} onOpenChange={setIsDescriptionOpen}>
                <DialogContent className="bg-white p-6 max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl">
                    <DialogHeader>
                        <DialogTitle className="text-xl font-bold mb-4">Описание</DialogTitle>
                    </DialogHeader>
                    <div
                        className="prose prose-sm max-w-none text-[#565552] leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: product.description || "Описание отсутствует" }}
                    />
                </DialogContent>
            </Dialog>
        </div>
    );
}
