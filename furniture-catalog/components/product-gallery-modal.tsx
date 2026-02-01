
import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { X, ChevronLeft, ChevronRight, BookmarkPlus, Info, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Product, api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ProductGalleryModalProps {
    product: Product | null;
    open: boolean;
    onClose: () => void;
    onSave?: (product: Product) => void;
}

export function ProductGalleryModal({ product, open, onClose, onSave }: ProductGalleryModalProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [showInfo, setShowInfo] = useState(false);
    const [showDescription, setShowDescription] = useState(false);

    // Combine all image sources
    const rawImages = [
        ...(product?.images || []),
        product?.main_image,
        ...(product?.gallery || [])
    ].filter((img): img is string => !!img);

    // Deduplicate and proxy
    const images = Array.from(new Set(rawImages)).map(img => api.getProxyImageUrl(img));

    // Reset state when product changes
    useEffect(() => {
        if (!open) return;
        const rafId = requestAnimationFrame(() => {
            setCurrentIndex(0);
            setShowInfo(false);
            setShowDescription(false);
        });
        return () => cancelAnimationFrame(rafId);
    }, [open, product]);

    const handleNext = useCallback(() => {
        if (images.length === 0) return;
        setCurrentIndex((prev) => (prev + 1) % images.length);
    }, [images.length]);

    const handlePrev = useCallback(() => {
        if (images.length === 0) return;
        setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
    }, [images.length]);

    // Handle keyboard navigation
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (!open) return;

        if (e.key === "Escape") onClose();
        if (e.key === "ArrowLeft") handlePrev();
        if (e.key === "ArrowRight") handleNext();
    }, [open, onClose, handlePrev, handleNext]);

    useEffect(() => {
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [handleKeyDown]);

    // Lock body scroll when open
    useEffect(() => {
        if (open) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "unset";
        }
        return () => {
            document.body.style.overflow = "unset";
        };
    }, [open]);

    if (!open || !product) return null;

    const handleSave = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (product && onSave) {
            onSave({
                ...product,
                main_image: images[currentIndex] // Overwrite main image with currently selected one
            });
        }
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
                <div className="relative w-full h-[65vh] flex items-center justify-center mb-6 px-12">
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

                    {/* Top Right Controls */}
                    <div className="absolute top-0 right-12 z-20 flex gap-2">
                        <Button
                            size="icon"
                            variant="secondary"
                            className={cn(
                                "bg-white/90 hover:bg-white text-[#141413] shadow-lg backdrop-blur-sm rounded-full h-10 w-10 transition-colors",
                                showDescription && "bg-[#c6613f] text-white hover:bg-[#c6613f]/90"
                            )}
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowDescription(!showDescription);
                                setShowInfo(false); // Close other popover
                            }}
                        >
                            <FileText className="h-5 w-5" />
                        </Button>

                        <Button
                            size="icon"
                            variant="secondary"
                            className={cn(
                                "bg-white/90 hover:bg-white text-[#141413] shadow-lg backdrop-blur-sm rounded-full h-10 w-10 transition-colors",
                                showInfo && "bg-[#c6613f] text-white hover:bg-[#c6613f]/90"
                            )}
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowInfo(!showInfo);
                                setShowDescription(false); // Close other popover
                            }}
                        >
                            <Info className="h-5 w-5" />
                        </Button>

                        <Button
                            size="lg"
                            variant="secondary"
                            className="bg-white/90 hover:bg-white text-[#141413] shadow-lg backdrop-blur-sm rounded-full gap-2 px-6"
                            onClick={handleSave}
                        >
                            <BookmarkPlus className="h-5 w-5" />
                            <span className="font-medium">Сохранить фото</span>
                        </Button>
                    </div>

                    {/* Details Popover/Overlay */}
                    {(showInfo || showDescription) && (
                        <div
                            className="fixed inset-0 z-25 bg-transparent"
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowInfo(false);
                                setShowDescription(false);
                            }}
                        />
                    )}

                    {showInfo && (
                        <div
                            className="absolute top-12 right-12 z-30 w-80 max-h-[60vh] overflow-y-auto overscroll-contain bg-white/95 backdrop-blur-md rounded-2xl p-6 shadow-2xl animate-in slide-in-from-top-2 duration-200 text-[#141413]"
                            onWheel={(e) => e.stopPropagation()}
                        >
                            <h3 className="font-semibold text-lg mb-4 text-[#141413] pb-2 border-b border-black/5">Характеристики</h3>
                            <div className="space-y-3 text-sm">
                                {product.brand && (
                                    <div className="grid grid-cols-2 gap-2 border-b border-black/5 pb-2">
                                        <span className="text-black/50">Бренд</span>
                                        <span className="font-medium text-right">{product.brand}</span>
                                    </div>
                                )}
                                {product.dimensions && (
                                    <div className="grid grid-cols-2 gap-2 border-b border-black/5 pb-2">
                                        <span className="text-black/50">Размеры</span>
                                        <span className="font-medium text-right">{product.dimensions}</span>
                                    </div>
                                )}
                                {product.available_formats && product.available_formats.length > 0 && !product.dimensions && (
                                    <div className="grid grid-cols-2 gap-2 border-b border-black/5 pb-2">
                                        <span className="text-black/50">Формат</span>
                                        <span className="font-medium text-right">{product.available_formats[0].dimensions}</span>
                                    </div>
                                )}
                                {product.materials && product.materials.length > 0 && (
                                    <div className="grid grid-cols-2 gap-2 border-b border-black/5 pb-2">
                                        <span className="text-black/50">Материалы</span>
                                        <span className="font-medium text-right">{product.materials.join(", ")}</span>
                                    </div>
                                )}
                                {product.article && (
                                    <div className="grid grid-cols-2 gap-2 pb-2">
                                        <span className="text-black/50">Артикул</span>
                                        <span className="font-medium text-right text-xs text-black/70">{product.article}</span>
                                    </div>
                                )}
                                {product.attributes && Object.entries(product.attributes).map(([key, value]) => (
                                    <div key={key} className="grid grid-cols-2 gap-2 border-b border-black/5 pb-2">
                                        <span className="text-black/50">{key}</span>
                                        <span className="font-medium text-right">{value}</span>
                                    </div>
                                ))}
                                {!product.brand && !product.dimensions && !product.materials?.length && !product.attributes && (
                                    <p className="text-black/50 italic text-center py-2">Нет дополнительных характеристик</p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Description Popover */}
                    {showDescription && (
                        <div
                            className="absolute top-12 right-12 z-30 w-80 max-h-[60vh] overflow-y-auto overscroll-contain bg-white/95 backdrop-blur-md rounded-2xl p-6 shadow-2xl animate-in slide-in-from-top-2 duration-200 text-[#141413]"
                            onWheel={(e) => e.stopPropagation()}
                        >
                            <h3 className="font-semibold text-lg mb-4 text-[#141413] pb-2 border-b border-black/5">Описание</h3>
                            <div className="text-sm leading-relaxed text-[#141413]/80">
                                {product.description || product.texture || (
                                    <p className="text-black/50 italic text-center py-2">Нет описания</p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Current Image */}
                    <div className="relative w-full h-full max-w-5xl">
                        {images[currentIndex] && (
                            <Image
                                src={images[currentIndex]}
                                alt={`${product.name} - view ${currentIndex + 1}`}
                                fill
                                unoptimized
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
                    {product.price && (
                        <p className="text-xl font-semibold mt-2 text-[#ff8c69] bg-black/40 px-4 py-1 rounded-full inline-block backdrop-blur-md">
                            {product.price.toLocaleString()} {product.currency || 'EUR'}
                        </p>
                    )}
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
                                    unoptimized
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
