"use client";

import { Sidebar } from "@/components/sidebar";
import { ProductCard } from "@/components/product-card";
import { ProductGalleryModal } from "@/components/product-gallery-modal";
import { ProductFullView } from "@/components/product-full-view";
import { HorizontalCarousel } from "@/components/horizontal-carousel";
import { SaveToProjectModal } from "@/components/save-to-project-modal";
import { useState, useEffect, useRef } from "react";
import {
  Search, Loader2, Paperclip, ArrowUp, Copy, ThumbsUp, ThumbsDown,
  RotateCcw, ChevronDown, ChevronRight, Code2, Plus, Image as ImageIcon,
  X, Check
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProjectsView } from "@/components/projects-view";
import { MaterialsView } from "@/components/materials-view";
import { ProjectDetailView } from "@/components/project-detail-view";
import { ImportJSONModal } from "@/components/import-json-modal";
import { cn } from "@/lib/utils";
import { api, Product } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content?: string;
  image?: string | null;
  simulation_image?: string | null;
  blocks?: {
    type: "app";
    title: string;
    view: "carousel";
    products: Product[];
  }[];
}

interface HistoryItem {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}

interface Project {
  id: string;
  name: string;
  items: Product[];
}



export default function Home() {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Привет! Я эксперт по дизайнерской мебели. Спросите меня о чем угодно или загрузите фото для поиска."
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialProducts, setInitialProducts] = useState<Product[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [productToSave, setProductToSave] = useState<Product | null>(null);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'chat' | 'projects' | 'project-detail' | 'product-full' | 'materials'>('chat');
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [selectedSources, setSelectedSources] = useState<string[]>(['catalog']);
  const [showSourceMenu, setShowSourceMenu] = useState(false);
  const [availableSources, setAvailableSources] = useState<{ id: string, name: string }[]>([
    { id: 'catalog', name: 'Локальный каталог' },
    { id: 'woocommerce', name: 'de-co-de.ru' }
  ]);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [activeSource, setActiveSource] = useState<string | null>(null);

  // Currency Converter State
  const [showRubles, setShowRubles] = useState(false);
  const [exchangeRate, setExchangeRate] = useState<number>(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sourceMenuRef = useRef<HTMLDivElement>(null);

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

  // Initial load
  useEffect(() => {
    api.getProducts().then(res => setInitialProducts(res.items)).catch(console.error);
    api.getSources().then(setAvailableSources).catch(console.error);

    // Fetch currency rate
    api.getCurrencyRate().then(data => {
      console.log("Currency Rate loaded:", data.rate);
      setExchangeRate(data.rate);
    }).catch(err => {
      console.error("Failed to fetch currency rate, using fallback", err);
      setExchangeRate(105.0); // Safe fallback
    });

    // Load chat history from API on mount
    api.getChatHistory()
      .then(chatMessages => {
        if (chatMessages && chatMessages.length > 0) {
          const formattedMessages = chatMessages.map(h => ({
            role: h.role === 'user' ? 'user' : 'assistant',
            content: h.content
          } as Message));

          setMessages(formattedMessages);

          // Also add to sidebar history if not already there or local is empty
          setHistory(prev => {
            if (prev.some(h => h.id === 'server_history')) return prev;
            const serverItem: HistoryItem = {
              id: 'server_history',
              title: 'История из базы',
              date: new Date().toLocaleDateString(),
              messages: formattedMessages
            };
            return [serverItem, ...prev];
          });
        }
      })
      .catch(console.error);

    const savedHistory = localStorage.getItem('furniture_chat_history');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }

    // Load projects from API
    api.getProjects()
      .then(serverProjects => {
        const savedProjectsStr = localStorage.getItem('furniture_user_projects');
        const localProjects = savedProjectsStr ? JSON.parse(savedProjectsStr) : [];

        if (serverProjects && serverProjects.length > 0) {
          setProjects(serverProjects);
        } else if (localProjects.length > 0) {
          // If server is empty but local has projects, push to server
          console.log("Syncing local projects to server...");
          setProjects(localProjects);
          api.saveProjects(localProjects).catch(console.error);
        }
      })
      .catch(err => {
        console.error("Failed to load projects from API, falling back to local storage", err);
        const savedProjects = localStorage.getItem('furniture_user_projects');
        if (savedProjects) {
          setProjects(JSON.parse(savedProjects));
        }
      });
  }, []);



  const handleAddToProject = (projectId: string, product: Product) => {
    const updatedProjects = projects.map(p => {
      if (p.id === projectId) {
        // Avoid duplicates
        if (p.items.some(i => i.slug === product.slug)) return p;
        return { ...p, items: [product, ...p.items] };
      }
      return p;
    });
    setProjects(updatedProjects);
    api.saveProjects(updatedProjects).catch(console.error);
    setProductToSave(null);
  };

  const handleCreateProject = (name: string) => {
    const newProject: Project = {
      id: Date.now().toString(),
      name,
      items: productToSave ? [productToSave] : []
    };
    const updatedProjects = [newProject, ...projects];
    setProjects(updatedProjects);
    api.saveProjects(updatedProjects).catch(console.error);
    setProductToSave(null);
  };

  const handleRemoveFromProject = (projectId: string, product: Product) => {
    const updatedProjects = projects.map(p => {
      if (p.id === projectId) {
        return { ...p, items: p.items.filter(i => i.slug !== product.slug) };
      }
      return p;
    });
    setProjects(updatedProjects);
    api.saveProjects(updatedProjects).catch(console.error);
  };



  const saveCurrentChat = () => {
    // Find the first user message for the title
    const firstUserMsg = messages.find(m => m.role === "user");

    // Don't save if no user interaction yet
    if (!firstUserMsg || !firstUserMsg.content) return;

    // Create a copy of messages without large base64 images to save space
    const messagesToSave = messages.map(m => ({
      ...m,
      // Only strip base64 images that are large, keep URLs
      image: m.image && m.image.startsWith('data:') && m.image.length > 1000 ? null : m.image,
      simulation_image: m.simulation_image // This is a URL, safe to keep
    }));

    const titleText = firstUserMsg.content;
    const cleanTitle = titleText.length > 30 ? titleText.slice(0, 30) + "..." : titleText;

    const chatId = currentChatId || Date.now().toString();
    if (!currentChatId) setCurrentChatId(chatId);

    const newHistoryItem: HistoryItem = {
      id: chatId,
      title: cleanTitle,
      date: new Date().toISOString(),
      messages: messagesToSave
    };

    // Remove existing version of this chat if it exists, then add to top
    const otherChats = history.filter(h => h.id !== chatId);
    const updatedHistory = [newHistoryItem, ...otherChats].slice(0, 20); // Limit to 20 items

    setHistory(updatedHistory);

    try {
      localStorage.setItem("furniture_chat_history", JSON.stringify(updatedHistory));
    } catch (e) {
      console.error("Failed to save chat history (likely quota exceeded)", e);
    }
  };

  const handleNewChat = () => {
    saveCurrentChat();
    setMessages([{
      role: "assistant",
      content: "Привет! Я эксперт по дизайнерской мебели. Спросите меня о чем угодно или загрузите фото для поиска."
    }]);
    setSelectedProduct(null);
    setCurrentChatId(null);
  };

  const handleSelectChat = (id: string) => {
    saveCurrentChat(); // Save current before switching
    const chat = history.find(h => h.id === id);
    if (chat) {
      setMessages(chat.messages);
      setSelectedProduct(null);
      setCurrentChatId(chat.id);
    }
  };

  const handleDeleteChat = (id: string) => {
    const updatedHistory = history.filter(h => h.id !== id);
    setHistory(updatedHistory);
    try {
      localStorage.setItem("furniture_chat_history", JSON.stringify(updatedHistory));
    } catch (e) {
      console.error("Failed to update history after deletion", e);
    }

    // If deleting current chat, reset
    if (id === currentChatId) {
      handleNewChat();
    }
  };

  const handleViewProjects = () => {
    setCurrentView('projects');
    setActiveProjectId(null);
  };

  const handleSelectProject = (projectId: string) => {
    setActiveProjectId(projectId);
    setCurrentView('project-detail');
  };

  const handleBackToChat = () => {
    setCurrentView('chat');
  };

  const handleBackToProjects = () => {
    setCurrentView('projects');
    setActiveProjectId(null);
  };

  const handleViewMaterials = () => {
    setCurrentView('materials');
    setActiveProjectId(null);
    setActiveSource(null); // Clear specific source filter when clicking main Materials link
  };

  const handleSelectSource = (sourceId: string) => {
    setActiveSource(sourceId);
    setCurrentView('materials');
    setActiveProjectId(null);
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (confirm(`Вы уверены, что хотите удалить источник "${sourceId}"?`)) {
      try {
        await api.deleteSource(sourceId);
        const updatedSources = await api.getSources();
        setAvailableSources(updatedSources);

        // If deleted source was active, reset
        if (activeSource === sourceId) {
          setActiveSource(null);
          // If in materials view, force refresh? key change handles it
        }
      } catch (e) {
        console.error("Failed to delete source", e);
        alert("Ошибка при удалении источника");
      }
    }
  };

  const handleRenameSource = async (sourceId: string, newName: string) => {
    try {
      await api.renameSource(sourceId, newName);
      const updatedSources = await api.getSources();
      setAvailableSources(updatedSources);

      // If renamed source was active, update activeSource to new ID (slugified name)
      // Ideally API returns new ID.
      // For now, simpler to just reset or keep if ID didn't change (unlikely if name changed).
      if (activeSource === sourceId) {
        // We'd need to know the new ID to keep it active correctly.
        // The API response contains source_id.
        // But here we are just refreshing list. 
        // Let's reset for safety or try to find it.
        setActiveSource(null);
      }
    } catch (e: unknown) {
      console.error("Failed to rename source", e);
      const message = e instanceof Error ? e.message : undefined;
      alert(message || "Ошибка при переименовании источника");
    }
  };

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product);
  };

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const handleSend = async () => {
    if ((!input.trim() && !pendingFile) || loading) return;

    if (pendingFile) {
      const userMsg: Message = {
        role: "user",
        content: input || "Найти похожую мебель",
        image: previewImage
      };

      setMessages(prev => [...prev, userMsg]);
      const currentInput = input;
      const currentImage = previewImage;

      setInput("");
      setPreviewImage(null);
      setPendingFile(null);
      setLoading(true);

      try {
        let results: Product[] = [];
        let chatResponse: string | null = null;
        let simulationUrl: string | null = null;

        let uploadedImageUrl = null;
        if (pendingFile) {
          try {
            const uploadRes = await api.uploadImage(pendingFile);
            uploadedImageUrl = uploadRes.url;
          } catch (e) {
            console.error("Failed to upload image", e);
            // Fallback to base64 if upload fails, though risk storage quota
            uploadedImageUrl = currentImage;
          }
        } else if (currentImage && !currentImage.startsWith('data:')) {
          uploadedImageUrl = currentImage;
        }

        // If user provided TEXT with image, use CHAT instead of pure search
        if (currentInput.trim()) {
          const history = messages
            .filter(m => m.content)
            .map(m => ({
              role: m.role === "user" ? "user" : "model" as "user" | "model",
              content: m.content || ""
            }));

          // Use the uploaded URL for the API call if possible, or base64 if fallback
          const response = await api.chat(currentInput, history, uploadedImageUrl || currentImage!);
          chatResponse = response.answer;
          results = response.products || [];
          simulationUrl = response.simulation_image || null;

          const assistantMsg: Message = {
            role: "assistant",
            content: chatResponse || "Вот что я думаю по этому поводу:",
            simulation_image: simulationUrl
          };

          if (results.length > 0) {
            assistantMsg.blocks = [{
              type: "app",
              title: "Рекомендации",
              view: "carousel",
              products: results
            }];
          }
          // Update the user message in history with the persistent URL
          setMessages(prev => prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, image: uploadedImageUrl || m.image } : m
          ));
          setMessages(prev => [...prev, assistantMsg]);
        } else {
          // Pure search
          results = await api.searchByImage(pendingFile);

          setMessages(prev => [...prev, {
            role: "assistant",
            content: `Я нашел ${results.length} похожих предметов мебели:`,
            blocks: [{
              type: "app",
              title: "Результаты поиска по фото",
              view: "carousel",
              products: results
            }]
          }]);

          // Update user message with URL
          if (uploadedImageUrl) {
            setMessages(prev => prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, image: uploadedImageUrl } : m
            ));
          }
        }
      } catch (err) {
        console.error(err);
        setMessages(prev => [...prev, { role: "assistant", content: "Произошла ошибка при обработке изображения." }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    // Text only flow
    const userMsg: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages
        .filter(m => m.content)
        .map(m => ({
          role: m.role === "user" ? "user" : "model" as "user" | "model",
          content: m.content || ""
        }));

      const response = await api.chat(input, history);

      const assistantMsg: Message = {
        role: "assistant",
        content: response.answer,
        simulation_image: response.simulation_image
      };

      if (response.products && response.products.length > 0) {
        assistantMsg.blocks = [{
          type: "app",
          title: "Рекомендованная мебель",
          view: "carousel",
          products: response.products
        }];
      }

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: "assistant", content: "Извините, произошла ошибка." }]);
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans text-primary">
      <Sidebar
        className="flex border-r-0 bg-secondary"
        onNewChat={() => { handleNewChat(); setCurrentView('chat'); }}
        history={history}
        onSelectChat={(id) => { handleSelectChat(id); setCurrentView('chat'); }}
        onDeleteChat={handleDeleteChat}
        projects={projects}
        onViewProjects={handleViewProjects}
        onSelectProject={handleSelectProject}
        onViewMaterials={handleViewMaterials}
        sources={availableSources}
        onSelectSource={handleSelectSource}
        onDeleteSource={handleDeleteSource}
        onRenameSource={handleRenameSource}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-background relative h-full">
        {currentView === 'projects' && (
          <ProjectsView
            projects={projects}
            onSelectProject={handleSelectProject}
            onCreateNew={() => {
              // Open modal in "Global / No Product" mode
              setIsProjectModalOpen(true);
              setProductToSave(null);
            }}
          />
        )}

        {currentView === 'project-detail' && projects.find(p => p.id === activeProjectId) && (
          <ProjectDetailView
            project={projects.find(p => p.id === activeProjectId)!}
            onBack={handleBackToProjects}
            onProductClick={handleProductClick}
            onRemoveItem={(p) => activeProjectId && handleRemoveFromProject(activeProjectId, p)}
            onProductAdded={(p) => activeProjectId && handleAddToProject(activeProjectId, p)}
          />
        )}

        {currentView === 'materials' && (
          <MaterialsView
            key={activeSource || 'all'}
            initialSource={activeSource || undefined}
            onBack={handleBackToProjects}
            onProductClick={handleProductClick}
            onSave={(p) => setProductToSave(p)}
            currencyMode={showRubles ? 'rub' : 'original'}
            exchangeRate={exchangeRate}
            onToggleCurrency={() => setShowRubles(!showRubles)}
          />
        )}

        {currentView === 'chat' && (
          <>
            <header className="h-[52px] flex items-center px-4 shrink-0 justify-between gap-4">
              <Button variant="ghost" size="sm" className="gap-2 text-[#3d3d3a] font-medium hover:bg-neutral-100">
                Designer Furniture Consultant <ChevronDown className="h-4 w-4 opacity-50" />
              </Button>

              <div className="flex items-center gap-2 ml-auto">
                <div className="relative" ref={sourceMenuRef}>
                  <button
                    onClick={() => {
                      const next = !showSourceMenu;
                      setShowSourceMenu(next);
                    }}
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
                            setSelectedSources(newVal);
                            // Trigger search
                            if (newVal.length > 0) {
                              setLoading(true);
                              api.getProducts(undefined, 1000, undefined, newVal.join(',')).then((data) => {
                                setInitialProducts(data.items);
                                setLoading(false);
                              });
                            }
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
                              setSelectedSources(newVal);
                              // Trigger search
                              setLoading(true);
                              api.getProducts(undefined, 1000, undefined, newVal.join(',')).then((data) => {
                                setInitialProducts(data.items);
                                setLoading(false);
                              });
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
                  onClick={() => setIsImportModalOpen(true)}
                >
                  Импорт JSON
                </Button>
              </div>
            </header>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 pb-4 scroll-smooth">
              <div className="max-w-[calc(100%-2rem)] md:max-w-4xl mx-auto w-full flex flex-col gap-6 py-4 pb-48 pl-12">

                {/* Initial Products Showcase */}


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
                          msg.role === "user" ? "font-sans font-semibold text-[15px] text-[#141413] mt-1.5" : "text-[#141413]"
                        )}>
                          {msg.content}
                        </div>
                      )}

                      {msg.blocks?.map((block, bIdx) => (
                        <div key={bIdx} className="w-full mt-2 select-none">
                          <div className="flex items-center justify-between mb-4 px-1">
                            <div className="text-[13px] font-medium text-[#141413] flex items-center gap-2 border border-[#1f1e1d1a] bg-white rounded-md px-2 py-1 shadow-sm">
                              <span className="font-bold">🧱</span>
                              {block.title}
                            </div>
                            <div className="flex gap-2 opacity-40 hover:opacity-100 transition-opacity">
                              <Code2 className="h-4 w-4 cursor-pointer" />
                            </div>
                          </div>
                          <HorizontalCarousel
                            products={block.products}
                            onProductClick={handleProductClick}
                            onSave={(p) => setProductToSave(p)}
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
                        handleSend();
                      }
                    }}
                    className="w-full bg-transparent px-12 py-4 h-[56px] outline-none text-[16px] placeholder:text-[#a1a19f]"
                    placeholder="Спросите о мебели или загрузите фото..."
                  />
                  <div className="absolute right-2 top-2 bottom-2 flex items-center gap-2">
                    <Button
                      size="icon"
                      onClick={handleSend}
                      disabled={!input.trim() || loading}
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
                      variant="ghost"
                      size="icon"
                      onClick={() => fileInputRef.current?.click()}
                      className="h-8 w-8 text-[#73726c] hover:text-[#141413] rounded-full">
                      <ImageIcon className="h-5 w-5" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      <ProductGalleryModal
        product={selectedProduct}
        open={!!selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onSave={(p) => setProductToSave(p)}
      />

      <SaveToProjectModal
        product={productToSave}
        open={!!productToSave || isProjectModalOpen}
        onClose={() => {
          setProductToSave(null);
          setIsProjectModalOpen(false);
        }}
        projects={projects}
        onSave={handleAddToProject}
        onCreateProject={handleCreateProject}
      />
      <ImportJSONModal
        open={isImportModalOpen}
        onOpenChange={setIsImportModalOpen}
        onImportSuccess={(sourceId) => {
          // Refresh sources and products
          api.getSources().then(setAvailableSources).catch(console.error);
          api.getProducts(undefined, 1000).then(res => setInitialProducts(res.items)).catch(console.error);
          setSelectedSources(prev => [...prev, sourceId]);
        }}
      />
    </div>
  );
}
