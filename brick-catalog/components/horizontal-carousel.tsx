"use client";

import { useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Product } from "@/lib/api";
import { ProductCard } from "./product-card";

interface HorizontalCarouselProps {
    products: Product[];
    onProductClick?: (product: Product) => void;
    onSave?: (product: Product) => void;
}

export function HorizontalCarousel({ products, onProductClick, onSave }: HorizontalCarouselProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [showLeftArrow, setShowLeftArrow] = useState(false);

    const scroll = (direction: 'left' | 'right') => {
        if (scrollRef.current) {
            const scrollAmount = direction === 'left' ? -400 : 400;
            scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
        }
    };

    const onScroll = () => {
        if (scrollRef.current) {
            setShowLeftArrow(scrollRef.current.scrollLeft > 20);
        }
    };

    return (
        <div className="relative group/carousel-outer">
            {/* Left Arrow */}
            {showLeftArrow && (
                <div className="absolute left-[-20px] top-1/2 -translate-y-[80%] z-20 transition-opacity">
                    <Button
                        onClick={() => scroll('left')}
                        size="icon"
                        className="w-9 h-9 rounded-full bg-white border border-border shadow-md hover:bg-neutral-50 text-[#3d3d3a]"
                    >
                        <ChevronDown className="h-5 w-5 rotate-90" />
                    </Button>
                </div>
            )}

            {/* Right Arrow */}
            <div className="absolute right-0 top-1/2 -translate-y-[80%] z-20 opacity-0 group-hover/carousel-outer:opacity-100 transition-opacity">
                <Button
                    onClick={() => scroll('right')}
                    size="icon"
                    className="w-9 h-9 rounded-full bg-white border border-border shadow-md hover:bg-neutral-50 text-[#3d3d3a]"
                >
                    <ChevronRight className="h-5 w-5" />
                </Button>
            </div>

            <div
                ref={scrollRef}
                onScroll={onScroll}
                className="flex gap-4 overflow-x-auto pb-6 scrollbar-hide snap-x pr-24 scroll-smooth"
            >
                {products.map(product => (
                    <ProductCard
                        key={product.slug}
                        product={product}
                        onClick={onProductClick}
                        onSave={onSave}
                    />
                ))}
            </div>
        </div>
    );
}
