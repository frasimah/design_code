
import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Product } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ProductGalleryModalProps {
    product: Product | null;
    open: boolean;
    onClose: () => void;
}

export function ProductGalleryModal({ product, open, onClose }: ProductGalleryModalProps) {
    const [currentIndex, setCurrentIndex] = useState(0);

    // Combine main image and gallery images into a single list
    const images = product
        ? [product.main_image, ...(product.gallery || [])].filter((img): img is string => !!img)
        : [];

    // Reset index when product changes
    useEffect(() => {
        if (open) {
            setCurrentIndex(0);
        }
    }, [open, product]);

    // Handle keyboard navigation
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (!open) return;

        if (e.key === "Escape") onClose();
        if (e.key === "ArrowLeft") handlePrev();
        if (e.key === "ArrowRight") handleNext();
    }, [open, onClose]);

    useEffect(() => {
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [handleKeyDown]);

    if (!open || !product) return null;

    const handleNext = () => {
        setCurrentIndex((prev) => (prev + 1) % images.length);
    };

    const handlePrev = () => {
        setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm animate-in fade-in duration-200">
            {/* Close Button */}
            <Button
                variant="ghost"
                size="icon"
                className="absolute top-4 right-4 text-white hover:bg-white/20 z-50"
                onClick={onClose}
            >
                <X className="h-6 w-6" />
            </Button>

            <div className="relative w-full h-full max-w-7xl mx-auto flex flex-col items-center justify-center p-4">

                {/* Main Image Container */}
                <div className="relative w-full h-[65vh] flex items-center justify-center mb-6">
                    {/* Navigation Buttons */}
                    {images.length > 1 && (
                        <>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="absolute left-0 md:left-4 z-10 text-white hover:bg-black/50 h-12 w-12 rounded-full"
                                onClick={(e) => { e.stopPropagation(); handlePrev(); }}
                            >
                                <ChevronLeft className="h-8 w-8" />
                            </Button>

                            <Button
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 md:right-4 z-10 text-white hover:bg-black/50 h-12 w-12 rounded-full"
                                onClick={(e) => { e.stopPropagation(); handleNext(); }}
                            >
                                <ChevronRight className="h-8 w-8" />
                            </Button>
                        </>
                    )}

                    {/* Current Image */}
                    <div className="relative w-full h-full max-w-5xl">
                        {images[currentIndex] && (
                            <Image
                                src={images[currentIndex]}
                                alt={`${product.name} - view ${currentIndex + 1}`}
                                fill
                                className="object-contain"
                                priority
                                quality={90}
                            />
                        )}
                    </div>
                </div>

                {/* Product Info */}
                <div className="text-center text-white mb-6">
                    <h2 className="text-2xl font-bold tracking-tight">{product.name}</h2>
                    <p className="text-white/70 text-sm mt-1">{product.description || product.texture}</p>
                </div>

                {/* Thumbnails */}
                {images.length > 1 && (
                    <div className="flex gap-2 overflow-x-auto max-w-full pb-2 px-4 scrollbar-hide">
                        {images.map((img, idx) => (
                            <button
                                key={idx}
                                onClick={() => setCurrentIndex(idx)}
                                className={cn(
                                    "relative w-20 h-14 rounded-md overflow-hidden shrink-0 border-2 transition-all",
                                    idx === currentIndex
                                        ? "border-white opacity-100"
                                        : "border-transparent opacity-50 hover:opacity-80"
                                )}
                            >
                                <Image
                                    src={img}
                                    alt={`Thumbnail ${idx + 1}`}
                                    fill
                                    className="object-cover"
                                />
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
