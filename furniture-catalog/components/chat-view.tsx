"use client";

import { useState, useRef, useEffect } from "react";
import { Message } from "@/types";
import { Product, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { HorizontalCarousel } from "@/components/horizontal-carousel";
import {
    Search, Loader2, Paperclip, ArrowUp, Copy, ThumbsUp, ThumbsDown,
    RotateCcw, ChevronDown, ChevronRight, Code2, Plus, Image as ImageIcon,
    X, Check
} from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ChatViewProps {
    messages: Message[];
    loading: boolean;
    onSend: (text: string, file: File | null, previewImage: string | null) => Promise<void>;
    onProductClick: (product: Product) => void;
    onSaveProduct: (product: Product) => void;

    // Source Selector Props
    selectedSources: string[];
    availableSources: { id: string; name: string }[];
    onSourcesChange: (sources: string[]) => void;

    // Import Modal
    onOpenImportModal: () => void;

    accessToken?: string;
    initialProducts?: Product[];
}

export function ChatView({
    messages,
    loading,
    onSend,
    onProductClick,
    onSaveProduct,
    selectedSources,
    availableSources,
    onSourcesChange,
    onOpenImportModal,
    accessToken,
    initialProducts = []
}: ChatViewProps) {
    const [input, setInput] = useState("");
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [pendingFile, setPendingFile] = useState<File | null>(null);
    const [showSourceMenu, setShowSourceMenu] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const sourceMenuRef = useRef<HTMLDivElement>(null);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, loading]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (sourceMenuRef.current && !sourceMenuRef.current.contains(event.target as Node)) {
                setShowSourceMenu(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onloadend = () => {
            setPreviewImage(reader.result as string);
            setPendingFile(file);
        };
        reader.readAsDataURL(file);

        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const handleSubmit = async () => {
        if ((!input.trim() && !pendingFile) || loading) return;

        // Call parent handler
        await onSend(input, pendingFile, previewImage);

        // Reset local state
        setInput("");
        setPreviewImage(null);
        setPendingFile(null);
    };

    return (
        <>
            <header className="h-[52px] flex items-center px-4 shrink-0 justify-between gap-4">
                <Button variant="ghost" size="sm" className="gap-2 text-[#3d3d3a] font-medium hover:bg-neutral-100">
                    Designer Furniture Consultant <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>

                <div className="flex items-center gap-2 ml-auto">
                    <div className="relative" ref={sourceMenuRef}>
                        <button
                            onClick={() => setShowSourceMenu(!showSourceMenu)}
                            className="flex items-center gap-2 bg-neutral-50 border border-border/60 hover:border-border rounded-md py-1.5 pl-3 pr-3 text-[13px] font-medium text-[#3d3d3a] transition-all"
                        >
                            {selectedSources.length === availableSources.length ? 'Все источники' :
                                selectedSources.length === 1 ? availableSources.find(s => s.id === selectedSources[0])?.name || 'Источник' :
                                    `${selectedSources.length} ист.`}
                            <ChevronDown className={cn("h-3.5 w-3.5 text-muted-foreground transition-transform", showSourceMenu && "rotate-180")} />
                        </button>

                        {showSourceMenu && (
                            <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-border/60 rounded-lg shadow-xl z-50 p-1.5 flex flex-col gap-0.5 animate-in fade-in zoom-in-95 duration-100">
                                {/* Option: ALL */}
                                <label className="flex items-center gap-3 px-3 py-2.5 hover:bg-neutral-50 rounded-md cursor-pointer transition-colors group">
                                    <div className={cn(
                                        "w-4 h-4 rounded border flex items-center justify-center transition-colors",
                                        selectedSources.length === availableSources.length ? "bg-[#c6613f] border-[#c6613f]" : "border-neutral-300 group-hover:border-[#c6613f]"
                                    )}>
                                        {selectedSources.length === availableSources.length && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                                    </div>
                                    <input
                                        type="checkbox"
                                        className="hidden"
                                        checked={selectedSources.length === availableSources.length}
                                        onChange={() => {
                                            const all = availableSources.map(s => s.id);
                                            const newVal = selectedSources.length === availableSources.length ? [] : all;
                                            onSourcesChange(newVal);
                                        }}
                                    />
                                    <span className="text-[13px] font-medium text-[#141413]">Все источники</span>
                                </label>

                                <div className="h-px bg-neutral-100 my-1 mx-2" />

                                {availableSources.map(source => (
                                    <label key={source.id} className="flex items-center gap-3 px-3 py-2 hover:bg-neutral-50 rounded-md cursor-pointer transition-colors group">
                                        <div className={cn(
                                            "w-4 h-4 rounded border flex items-center justify-center transition-colors",
                                            selectedSources.includes(source.id) ? "bg-[#c6613f] border-[#c6613f]" : "border-neutral-300 group-hover:border-[#c6613f]"
                                        )}>
                                            {selectedSources.includes(source.id) && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                                        </div>
                                        <input
                                            type="checkbox"
                                            className="hidden"
                                            checked={selectedSources.includes(source.id)}
                                            onChange={() => {
                                                let newVal;
                                                if (selectedSources.includes(source.id)) {
                                                    newVal = selectedSources.filter(s => s !== source.id);
                                                } else {
                                                    newVal = [...selectedSources, source.id];
                                                }
                                                onSourcesChange(newVal);
                                            }}
                                        />
                                        <div className="flex flex-col">
                                            <span className="text-[13px] text-[#3d3d3a]">{source.name}</span>
                                            {source.id === 'woocommerce' && <span className="text-[10px] text-neutral-400">de-co-de.ru</span>}
                                        </div>
                                    </label>
                                ))}
                            </div>
                        )}
                    </div>

                    <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-[13px] font-medium text-[#3d3d3a] border-border/60 hover:bg-neutral-50 shadow-sm"
                        onClick={onOpenImportModal}
                    >
                        Импорт JSON
                    </Button>
                </div>
            </header>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pb-4 scroll-smooth">
                <div className="max-w-[calc(100%-2rem)] md:max-w-4xl mx-auto w-full flex flex-col gap-6 py-4 pb-48 pl-12">

                    {/* Initial Products Showcase */}
                    {messages.length === 1 && initialProducts.length > 0 && (
                        <div className="mb-6">
                            <div className="flex items-center justify-between mb-4 px-1">
                                <div className="text-[13px] font-medium text-[#141413] flex items-center gap-2 border border-[#1f1e1d1a] bg-white rounded-md px-2 py-1 shadow-sm">
                                    <span className="font-bold">🔥</span>
                                    Популярное
                                </div>
                            </div>
                            <HorizontalCarousel
                                products={initialProducts}
                                onProductClick={onProductClick}
                                onSave={onSaveProduct}
                            />
                        </div>
                    )}

                    {/* Message Stream */}
                    {messages.map((msg, idx) => (
                        <div key={idx} className="flex gap-4 group relative">
                            {msg.role === "user" ? (
                                <div className="w-7 h-7 rounded-[4px] shrink-0 flex items-center justify-center text-[10px] font-bold tracking-wide shadow-none mt-1 select-none bg-neutral-100 text-[#565552] border border-black/5">
                                    U
                                </div>
                            ) : (
                                <div className="w-7 h-7 rounded-[4px] shrink-0 flex items-center justify-center text-[10px] font-bold tracking-wide shadow-none mt-1 select-none bg-[#c6613f] text-white border border-transparent">
                                    AI
                                </div>
                            )}

                            <div className={cn("flex-1 space-y-3 min-w-0")}>
                                {/* Image Content */}
                                {msg.image && <img src={msg.image} alt="User upload" className="max-w-md rounded-xl border border-border shadow-sm" />}

                                {/* Simulation/Try-On Result */}
                                {msg.simulation_image && (
                                    <div className="space-y-2">
                                        <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400">✨ Визуализация (Nanobanana Try-On)</div>
                                        <img src={msg.simulation_image} alt="Simulation Result" className="max-w-full rounded-2xl border-2 border-primary/20 shadow-lg" />
                                    </div>
                                )}

                                {/* Text Content */}
                                {msg.content && (
                                    <div className={cn(
                                        "font-serif text-[17px] leading-relaxed tracking-wide antialiased max-w-2xl",
                                        msg.role === "user" ? "font-sans font-semibold text-[15px] text-[#141413] mt-1.5" : "text-[#141413] prose prose-neutral prose-p:leading-relaxed prose-strong:font-semibold prose-strong:text-[#141413]"
                                    )}>
                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    </div>
                                )}

                                {msg.blocks?.map((block, bIdx) => (
                                    <div key={bIdx} className="w-full mt-2 select-none">
                                        {block.title && (
                                            <div className="flex items-center justify-between mb-4 px-1">
                                                <div className="text-[13px] font-medium text-[#141413] flex items-center gap-2 border border-[#1f1e1d1a] bg-white rounded-md px-2 py-1 shadow-sm">
                                                    <span className="font-bold">🧱</span>
                                                    {block.title}
                                                </div>
                                                <div className="flex gap-2 opacity-40 hover:opacity-100 transition-opacity">
                                                    <Code2 className="h-4 w-4 cursor-pointer" />
                                                </div>
                                            </div>
                                        )}
                                        <HorizontalCarousel
                                            products={block.products}
                                            onProductClick={onProductClick}
                                            onSave={onSaveProduct}
                                            accessToken={accessToken}
                                        />
                                    </div>
                                ))}

                                {msg.role === "assistant" && (
                                    <div className="flex gap-2 items-center">
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-[#73726c] hover:bg-transparent"><ThumbsUp className="h-4 w-4" /></Button>
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-[#73726c] hover:bg-transparent"><ThumbsDown className="h-4 w-4" /></Button>
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-[#73726c] hover:bg-transparent"><Copy className="h-4 w-4" /></Button>
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-[#73726c] hover:bg-transparent"><RotateCcw className="h-4 w-4" /></Button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex gap-4">
                            <div className="w-7 h-7 rounded-[4px] shrink-0 flex items-center justify-center bg-[#c6613f] text-white">
                                AI
                            </div>
                            <div className="flex items-center gap-2 text-neutral-400">
                                <div className="w-2 h-2 rounded-full bg-neutral-300 animate-bounce" />
                                <div className="w-2 h-2 rounded-full bg-neutral-300 animate-bounce delay-75" />
                                <div className="w-2 h-2 rounded-full bg-neutral-300 animate-bounce delay-150" />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Input Area */}
            <div className="absolute bottom-0 left-0 right-0 px-4 pb-6 pt-12 bg-gradient-to-t from-white via-white/95 to-transparent z-20">
                <div className="max-w-3xl mx-auto w-full space-y-2 relative">
                    {previewImage && (
                        <div className="absolute left-0 -top-24 w-20 h-20 rounded-lg overflow-hidden border-2 border-white shadow-lg bg-neutral-100 group animate-in fade-in slide-in-from-bottom-2">
                            <img src={previewImage} alt="Preview" className="w-full h-full object-cover" />
                            <button
                                onClick={() => { setPreviewImage(null); setPendingFile(null); }}
                                className="absolute top-1 right-1 bg-black/50 hover:bg-black/70 text-white rounded-full p-0.5 transition-colors">
                                <X size={12} />
                            </button>
                        </div>
                    )}

                    <div className="relative bg-[#ffffff] border border-[#d1d1d0] rounded-[26px] shadow-sm hover:border-[#b3b3b2] focus-within:border-[#9e9e9d] transition-all duration-200">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit();
                                }
                            }}
                            className="w-full bg-transparent px-12 py-4 h-[56px] outline-none text-[16px] placeholder:text-[#a1a19f]"
                            placeholder="Спросите о мебели или загрузите фото..."
                        />
                        <div className="absolute right-2 top-2 bottom-2 flex items-center gap-2">
                            <Button
                                size="icon"
                                onClick={handleSubmit}
                                disabled={(!input.trim() && !pendingFile) || loading}
                                className="w-8 h-8 rounded-[8px] bg-[#c6613f] hover:bg-[#b55232] text-white shadow-none transition-all disabled:opacity-50 flex items-center justify-center">
                                <ArrowUp className="h-4 w-4 stroke-[2.5]" />
                            </Button>
                        </div>
                        <div className="absolute left-2 top-2 bottom-2 flex items-center">
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="hidden"
                                accept="image/*"
                                onChange={handleFileUpload}
                            />
                            <Button
                                size="icon"
                                variant="ghost"
                                className="w-8 h-8 rounded-[8px] text-[#73726c] hover:bg-[#1f1e1d0f] hover:text-[#141413]"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <Paperclip className="h-4 w-4 stroke-[2.5]" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
