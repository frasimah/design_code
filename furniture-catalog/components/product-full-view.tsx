"use client";

import { Product, api } from "@/lib/api";
import { ArrowLeft, MoreHorizontal, Share, Download, Heart, BookmarkPlus } from "lucide-react";
import { Button } from "./ui/button";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface ProductFullViewProps {
    product: Product;
    onBack: () => void;
    onSave?: (product: Product) => void;
}

export function ProductFullView({ product, onBack, onSave }: ProductFullViewProps) {
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
                            {/* Display article if available, or texture description */}
                            <span>{product.article || "Артикул не указан"}</span>
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
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:bg-black/5 text-[#141413]">
                            <Share className="h-5 w-5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-full hover:bg-black/5 text-[#141413]">
                            <MoreHorizontal className="h-5 w-5" />
                        </Button>
                    </div>
                </div>

                {/* Sub-header Controls / Description */}
                <div className="flex flex-col items-center text-center max-w-2xl mx-auto mt-4 mb-8">
                    {/* Optional: Add description snippet if available */}
                    {product.description && (
                        <p className="text-[#565552] text-sm leading-relaxed line-clamp-2">
                            {product.description}
                        </p>
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
                <div className="columns-1 sm:columns-2 md:columns-3 gap-4 space-y-4">
                    {images.map((img, idx) => (
                        <div key={idx} className="relative rounded-xl overflow-hidden group bg-secondary/20 break-inside-avoid shadow-sm hover:shadow-md transition-shadow">
                            <Image
                                src={img}
                                alt={`${product.name} ${idx + 1}`}
                                width={500}
                                height={500}
                                unoptimized
                                className="w-full h-auto object-cover transition-transform duration-500 group-hover:scale-105"
                                sizes="(max-width: 768px) 100vw, 33vw"
                            />
                            {/* Individual Save Button */}
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
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
        </div>
    );
}
