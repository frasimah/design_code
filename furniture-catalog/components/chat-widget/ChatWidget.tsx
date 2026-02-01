'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, X, MessageCircle, Sparkles, Loader2, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils'; // Assuming standard shadcn/ui utils
import { sendMessage, ChatMessage, Product } from './api';
import Image from 'next/image';

// --- Types ---
interface ChatWidgetProps {
    className?: string;
}

// --- Components ---

export function ChatWidget({ className }: ChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([
        { role: 'assistant', content: 'Здравствуйте! Я ваш консультант по кирпичу. Чем я могу помочь?' }
    ]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const toggleOpen = () => setIsOpen(!isOpen);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg: ChatMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            // Prepare history for API (exclude initial greeting if generic)
            const history = messages.slice(1);
            const response = await sendMessage(userMsg.content, history);

            const aiMsg: ChatMessage = {
                role: 'assistant',
                content: response.answer,
                products: response.products,
                image: response.simulation_image
            };
            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Прошу прощения, произошла ошибка. Пожалуйста, попробуйте еще раз.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className={cn("fixed bottom-6 right-6 z-50 flex flex-col items-end", className)}>

            {/* Chat Window */}
            {isOpen && (
                <div className="mb-4 w-[380px] max-w-[calc(100vw-32px)] h-[600px] max-h-[80vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-neutral-200 animate-in slide-in-from-bottom-10 fade-in duration-200">

                    {/* Header */}
                    <div className="bg-[#121212] p-4 flex justify-between items-center text-white shrink-0">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#1B2F81] to-[#54519E] flex items-center justify-center">
                                <Sparkles size={16} className="text-white" />
                            </div>
                            <div>
                                <h3 className="font-medium text-sm">DesignCode Consultant</h3>
                                <p className="text-xs text-neutral-400">Онлайн</p>
                            </div>
                        </div>
                        <button onClick={toggleOpen} className="p-1 hover:bg-white/10 rounded-full transition-colors">
                            <X size={20} />
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F8F9FA]">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={cn("flex flex-col max-w-[85%]", msg.role === 'user' ? "self-end items-end" : "self-start items-start")}>
                                <div
                                    className={cn(
                                        "p-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap",
                                        msg.role === 'user'
                                            ? "bg-[#121212] text-white rounded-br-none"
                                            : "bg-white text-[#464646] shadow-sm border border-black/5 rounded-bl-none"
                                    )}
                                >
                                    {msg.content}
                                </div>

                                {/* Product Recommendations */}
                                {msg.products && msg.products.length > 0 && (
                                    <div className="mt-3 w-full -ml-2">
                                        <p className="text-[10px] uppercase text-[#B0B0B0] font-medium tracking-wider mb-2 pl-2">Рекомендуемые товары</p>
                                        <div className="flex gap-2 overflow-x-auto pb-2 px-2 snap-x hide-scrollbar">
                                            {msg.products.map((product) => (
                                                <div key={product.slug} className="snap-center shrink-0 w-32 bg-white rounded-lg border border-black/5 overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
                                                    <div className="aspect-[4/3] relative bg-neutral-100">
                                                        {typeof product.main_image === "string" && product.main_image ? (
                                                            <img src={product.main_image} alt={product.name} className="object-cover w-full h-full" />
                                                        ) : (
                                                            <div className="w-full h-full flex items-center justify-center text-neutral-300"><ImageIcon size={16} /></div>
                                                        )}
                                                    </div>
                                                    <div className="p-2">
                                                        <h4 className="text-xs font-medium text-[#121212] truncate group-hover:text-[#52529D] transition-colors">{product.name}</h4>
                                                        <p className="text-[10px] text-[#B0B0B0]">{product.article}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Simulation Image */}
                                {msg.image && (
                                    <div className="mt-3 w-full rounded-lg overflow-hidden border border-black/5 shadow-sm">
                                        <img src={msg.image} alt="Simulation" className="w-full h-auto" />
                                    </div>
                                )}
                            </div>
                        ))}
                        {isLoading && (
                            <div className="self-start bg-white p-3 rounded-2xl rounded-bl-none shadow-sm border border-black/5 flex items-center gap-2">
                                <Loader2 size={16} className="animate-spin text-[#B0B0B0]" />
                                <span className="text-xs text-[#B0B0B0]">Печатает...</span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="p-3 bg-white border-t border-neutral-100 shrink-0">
                        <div className="relative flex items-end gap-2 bg-[#F8F9FA] p-2 rounded-xl border border-transparent focus-within:border-[#1B2F81] focus-within:ring-1 focus-within:ring-[#1B2F81]/10 transition-all">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder="Задайте вопрос о кирпиче..."
                                className="w-full max-h-32 bg-transparent text-sm resize-none focus:outline-none p-2 text-[#121212] placeholder:text-[#B0B0B0]"
                                rows={1}
                                style={{ minHeight: '40px' }}
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className="mb-1 p-2 rounded-full bg-[#121212] text-white hover:bg-[#2a2a2a] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <Send size={16} />
                            </button>
                        </div>
                        <div className="text-center mt-2">
                            <p className="text-[10px] text-[#B0B0B0]">AI может ошибаться. Проверяйте информацию.</p>
                        </div>
                    </div>

                </div>
            )}

            {/* Floating Button */}
            <button
                onClick={toggleOpen}
                className={cn(
                    "h-14 w-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 hover:scale-105 active:scale-95 group",
                    isOpen ? "bg-white text-[#121212]" : "bg-gradient-to-br from-[#1B2F81] via-[#0B2498] to-[#54519E] text-white"
                )}
            >
                {isOpen ? <X size={24} /> : <MessageCircle size={28} className="group-hover:animate-pulse" />}
                {!isOpen && (
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white"></span>
                )}
            </button>
        </div>
    );
}
