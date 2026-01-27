
import Image from "next/image";
import { Product } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { BookmarkPlus } from "lucide-react";

import { cn } from "@/lib/utils";

interface ProductCardProps {
    product: Product;
    onClick?: (product: Product) => void;
    onSave?: (product: Product) => void;
    className?: string;
}

export function ProductCard({ product, onClick, onSave, className }: ProductCardProps) {
    return (
        <div
            className={cn("flex flex-col gap-2 w-[280px] shrink-0 group cursor-pointer", className)}
            onClick={() => onClick?.(product)}
        >
            {/* Image Container */}
            <div className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden bg-secondary/50">
                {product.main_image ? (
                    <Image
                        src={product.main_image}
                        alt={product.name}
                        fill
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground/40 font-medium bg-[#f0eee6]">
                        Нет фото
                    </div>
                )}

                {/* Bookmark/Action Icon Overlay */}
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                    <Button
                        size="icon"
                        variant="secondary"
                        className="h-8 w-8 rounded-full bg-white/90 hover:bg-white text-[#141413] shadow-sm backdrop-blur-sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            onSave?.(product);
                        }}
                    >
                        <BookmarkPlus className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Content */}
            <div className="flex flex-col gap-0.5 px-0.5">
                <h3 className="font-bold text-[15px] text-[#141413] leading-tight truncate" title={product.name}>
                    {product.name}
                </h3>
                <p className="text-[13px] text-[#565552] truncate">
                    {product.texture || 'Текстура не указана'}
                </p>

                {/* Meta Info Row */}
                <div className="flex items-center gap-1.5 text-[12px] text-[#73726c] mt-0.5 font-medium">
                    <span>Vandersanden</span>
                    <span>•</span>
                    <span>{product.article || 'N/A'}</span>
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

