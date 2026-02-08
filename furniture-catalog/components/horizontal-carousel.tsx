"use client";

import { useRef, useState, useEffect } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Product } from "@/lib/api";
import { ProductCard } from "./product-card";

interface HorizontalCarouselProps {
    products: Product[];
    onProductClick?: (product: Product) => void;
    onSave?: (product: Product) => void;
    accessToken?: string;
}

export function HorizontalCarousel({ products, onProductClick, onSave, accessToken }: HorizontalCarouselProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [showLeftArrow, setShowLeftArrow] = useState(false);
    const [showRightArrow, setShowRightArrow] = useState(false);

    const scroll = (direction: 'left' | 'right') => {
        if (scrollRef.current) {
            const scrollAmount = direction === 'left' ? -400 : 400;
            scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
        }
    };

    const updateArrows = () => {
        if (scrollRef.current) {
            const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
            setShowLeftArrow(scrollLeft > 20);
            // Show right arrow only if there's more content to scroll
            setShowRightArrow(scrollWidth > clientWidth + scrollLeft + 20);
        }
    };

    // Check arrows on mount and when products change
    useEffect(() => {
        updateArrows();
        // Also check after a small delay to ensure layout is complete
        const timer = setTimeout(updateArrows, 100);
        return () => clearTimeout(timer);
    }, [products]);

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

            {/* Right Arrow - only show if there's more content to scroll */}
            {showRightArrow && (
                <div className="absolute right-0 top-1/2 -translate-y-[80%] z-20 opacity-0 group-hover/carousel-outer:opacity-100 transition-opacity">
                    <Button
                        onClick={() => scroll('right')}
                        size="icon"
                        className="w-9 h-9 rounded-full bg-white border border-border shadow-md hover:bg-neutral-50 text-[#3d3d3a]"
                    >
                        <ChevronRight className="h-5 w-5" />
                    </Button>
                </div>
            )}

            <div
                ref={scrollRef}
                onScroll={updateArrows}
                className="flex gap-4 overflow-x-auto pb-6 scrollbar-hide snap-x pr-24 scroll-smooth"
            >
                {products.map(product => (
                    <ProductCard
                        key={product.slug}
                        product={product}
                        onClick={onProductClick}
                        onSave={onSave}
                        className="w-[220px] md:w-[260px] shrink-0"
                        accessToken={accessToken}
                    />
                ))}
            </div>
        </div>
    );
}
