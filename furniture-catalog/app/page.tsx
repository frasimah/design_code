"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/sidebar";
import { ChatView } from "@/components/chat-view"; // New component
import { ProjectsView } from "@/components/projects-view";
import { MaterialsView } from "@/components/materials-view";
import { ProjectDetailView } from "@/components/project-detail-view";
import { ProductFullView } from "@/components/product-full-view";
import { SaveToProjectModal } from "@/components/save-to-project-modal";
import { ImportJSONModal } from "@/components/import-json-modal";
import { api, Product } from "@/lib/api";
import { Message, HistoryItem } from "@/types"; // Shared types

interface Project {
  id: string;
  name: string;
  items: Product[];
}

export default function Home() {
  const { data: session } = useSession();
  const accessToken = (session as { accessToken?: string })?.accessToken;

  // Shared State
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [productToSave, setProductToSave] = useState<Product | null>(null);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Navigation State
  const [currentView, setCurrentView] = useState<'chat' | 'projects' | 'project-detail' | 'product-full' | 'materials'>('chat');
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string | null>(null);

  // Data State
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Привет! Я эксперт по дизайнерской мебели. Спросите меня о чем угодно или загрузите фото для поиска."
    }
  ]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [initialProducts, setInitialProducts] = useState<Product[]>([]);

  // Search/Filter State
  const [loading, setLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>(['catalog']);
  const [availableSources, setAvailableSources] = useState<{ id: string, name: string }[]>([
    { id: 'catalog', name: 'Локальный каталог' },
    { id: 'woocommerce', name: 'de-co-de.ru' }
  ]);

  // Currency State
  const [showRubles, setShowRubles] = useState(false);
  const [exchangeRate, setExchangeRate] = useState<number>(0);

  // Initial Data Loading
  useEffect(() => {
    // Initial product load (popular/default)
    api.getProducts(undefined, 50, undefined, 'catalog', 0, undefined, undefined, undefined, accessToken)
      .then(res => setInitialProducts(res.items))
      .catch(console.error);

    api.getSources(accessToken).then(setAvailableSources).catch(console.error);

    // Fetch currency rate
    api.getCurrencyRate().then(data => {
      console.log("Currency Rate loaded:", data.rate);
      setExchangeRate(data.rate);
    }).catch(err => {
      console.error("Failed to fetch currency rate, using fallback", err);
      setExchangeRate(105.0); // Safe fallback
    });

    // Only load user data from API if authenticated
    if (!accessToken) return;

    // Load chat history
    api.getChatHistory(accessToken)
      .then(chatMessages => {
        if (chatMessages && chatMessages.length > 0) {
          const formattedMessages = chatMessages.map(h => {
            const msg: Message = {
              role: h.role === 'user' ? 'user' : 'assistant',
              content: h.content
            };

            // If message has products, add them as blocks for carousel display
            if (h.products && h.products.length > 0) {
              msg.blocks = [{
                type: "app",
                title: "Найденные товары",
                view: "carousel",
                products: h.products
              }];
            }

            return msg;
          });

          setMessages(formattedMessages);

          // Add to sidebar history
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

    // Load projects
    api.getProjects(accessToken)
      .then(serverProjects => {
        if (serverProjects && serverProjects.length > 0) {
          setProjects(serverProjects);
        }
      })
      .catch(console.error);
  }, [accessToken]);

  // Handle URL parameters for deep linking (product/project)
  const urlHandledRef = useRef(false);
  useEffect(() => {
    // Only run once
    if (urlHandledRef.current) return;

    const params = new URLSearchParams(window.location.search);
    const productSlug = params.get('product');
    const projectId = params.get('project');

    // Check for catalog filter params
    const hasCatalogParams = params.has('q') || params.has('category') ||
      params.has('brands') || params.has('sources') ||
      params.has('sort');

    if (productSlug) {
      urlHandledRef.current = true;
      // Fetch and open product by slug
      api.getProduct(productSlug)
        .then(product => {
          setSelectedProduct(product);
          // Clean up URL after success
          window.history.replaceState({}, '', window.location.pathname);
        })
        .catch(err => {
          console.error("Failed to load product from URL:", err);
          // Clean up URL even on error
          window.history.replaceState({}, '', window.location.pathname);
        });
    }

    if (projectId && projects.length > 0) {
      const project = projects.find(p => p.id === projectId);
      if (project) {
        urlHandledRef.current = true;
        setActiveProjectId(projectId);
        setCurrentView('project-detail');
        // Clean up URL
        window.history.replaceState({}, '', window.location.pathname);
      }
    }

    // If catalog filter params, switch to materials view (it will parse the params itself)
    if (hasCatalogParams) {
      urlHandledRef.current = true;
      setCurrentView('materials');
      // Don't clean URL here - MaterialsView will do it after parsing
    }
  }, [projects]);

  // --- Handlers ---

  const handleSourcesChange = (newSources: string[]) => {
    setSelectedSources(newSources);
    if (newSources.length > 0) {
      setLoading(true);
      api.getProducts(undefined, 1000, undefined, newSources.join(','), 0, undefined, undefined, undefined, accessToken)
        .then((data) => {
          setInitialProducts(data.items);
          setLoading(false);
        })
        .catch((err) => {
          console.error("Failed to fetch products for sources", err);
          setLoading(false);
        });
    }
  };

  const handleAddToProject = (projectId: string, product: Product) => {
    const updatedProjects = projects.map(p => {
      if (p.id === projectId) {
        if (p.items.some(i => i.slug === product.slug)) return p;
        return { ...p, items: [product, ...p.items] };
      }
      return p;
    });
    setProjects(updatedProjects);
    if (accessToken) api.saveProjects(updatedProjects, accessToken).catch(console.error);
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
    if (accessToken) api.saveProjects(updatedProjects, accessToken).catch(console.error);
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
    if (accessToken) api.saveProjects(updatedProjects, accessToken).catch(console.error);
  };

  const saveCurrentChat = () => {
    const firstUserMsg = messages.find(m => m.role === "user");
    if (!firstUserMsg || !firstUserMsg.content) return;

    const messagesToSave = messages.map(m => ({
      ...m,
      image: m.image && m.image.startsWith('data:') && m.image.length > 1000 ? null : m.image,
      simulation_image: m.simulation_image
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

    const otherChats = history.filter(h => h.id !== chatId);
    const updatedHistory = [newHistoryItem, ...otherChats].slice(0, 20);

    setHistory(updatedHistory);
    try {
      localStorage.setItem("furniture_chat_history", JSON.stringify(updatedHistory));
    } catch (e) {
      console.error("Failed to save chat history", e);
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
    saveCurrentChat();
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
    } catch (e) { console.error(e); }

    if (id === currentChatId) handleNewChat();
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (confirm(`Вы уверены, что хотите удалить источник "${sourceId}"?`)) {
      try {
        await api.deleteSource(sourceId, accessToken);
        const updatedSources = await api.getSources(accessToken);
        setAvailableSources(updatedSources);
        if (activeSource === sourceId) setActiveSource(null);
      } catch (e) {
        console.error("Failed to delete source", e);
        alert("Ошибка при удалении источника");
      }
    }
  };

  const handleRenameSource = async (sourceId: string, newName: string) => {
    try {
      await api.renameSource(sourceId, newName, accessToken);
      const updatedSources = await api.getSources(accessToken);
      setAvailableSources(updatedSources);
      if (activeSource === sourceId) setActiveSource(null);
    } catch (e: unknown) {
      console.error("Failed to rename source", e);
      const message = e instanceof Error ? e.message : undefined;
      alert(message || "Ошибка при переименовании источника");
    }
  };

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product);
  };

  const handleRenameProject = async (newName: string) => {
    if (!activeProjectId) return;

    const updatedProjects = projects.map(p =>
      p.id === activeProjectId ? { ...p, name: newName } : p
    );

    setProjects(updatedProjects);

    if (accessToken) {
      try {
        await api.saveProjects(updatedProjects, accessToken);
      } catch (error) {
        console.error("Failed to save project name:", error);
      }
    }
  };

  // Chat Send Handler (Refactored to accept args)
  const handleSend = async (text: string, file: File | null, previewImage: string | null) => {
    // Logic extracted from original handleSend, adapted to use args
    if (file) {
      const userMsg: Message = {
        role: "user",
        content: text || "Найти похожую мебель",
        image: previewImage
      };

      setMessages(prev => [...prev, userMsg]);
      setLoading(true);

      try {
        let results: Product[] = [];
        let chatResponse: string | null = null;
        let simulationUrl: string | null = null;

        let uploadedImageUrl = null;
        if (file) {
          try {
            const uploadRes = await api.uploadImage(file);
            uploadedImageUrl = uploadRes.url;
          } catch (e) {
            console.error("Failed to upload image", e);
            uploadedImageUrl = previewImage;
          }
        } else if (previewImage && !previewImage.startsWith('data:')) {
          uploadedImageUrl = previewImage;
        }

        if (text.trim()) {
          // Chat with Image
          const history = messages
            .filter(m => m.content)
            .map(m => ({
              role: m.role === "user" ? "user" : "model" as "user" | "model",
              content: m.content || ""
            }));

          const response = await api.chat(text, history, uploadedImageUrl || previewImage!, accessToken);
          chatResponse = response.answer;
          results = response.products || [];
          simulationUrl = response.simulation_image || null;

          // Parse JSON from text if products are missing but JSON is present
          console.log("DEBUG: Raw chatResponse:", chatResponse);

          // Try to find JSON block with recommended_slugs
          // 1. Look for markdown code block: ```json ... ```
          // 2. Look for raw JSON object: { ... "recommended_slugs" ... }
          let jsonMatch = chatResponse.match(/```json\s*(\{[\s\S]*?"recommended_slugs"[\s\S]*?\})\s*```/);

          if (!jsonMatch) {
            // Fallback: match any JSON-like object containing "recommended_slugs"
            // nesting braces might be tricky with regex, but let's try a simple one for the top level
            jsonMatch = chatResponse.match(/(\{[\s\S]*?"recommended_slugs"[\s\S]*?\})/);
          }

          console.log("DEBUG: Regex match result:", jsonMatch);

          if (jsonMatch) {
            try {
              const jsonStr = jsonMatch[1] || jsonMatch[0];
              const parsed = JSON.parse(jsonStr);
              if (parsed.recommended_slugs && Array.isArray(parsed.recommended_slugs)) {
                // If we have slugs but no products, we might need to fetch them (or they might be in results already)
                if (results.length === 0) {
                  console.log("DEBUG: Found slugs but no products. Slugs:", parsed.recommended_slugs);
                  // Start fetching products by slug
                  try {
                    // Create a search string with the slugs to find them
                    // Or better, use a direct lookup if possible.
                    // Since we don't have getProductsBySlugs, we will try to find them in initialProducts
                    // or just rely on the user seeing the text for now.
                    // BUT better to try to fetch them if possible.

                    // Let's try to fetch them using the first slug as a search query just to get SOMETHING for now
                    // Or if we can filter.
                    // Actually, api.getProducts has 'search' param.

                    // Warning: making multiple calls might be slow.
                    // Let's just log for now to confirm we get here.
                  } catch (err) {
                    console.error("DEBUG: Failed to fetch products by slug", err);
                  }
                }

                // Clean the response text by removing the JSON block
                chatResponse = chatResponse.replace(jsonMatch[0], "").trim();
              }
            } catch (e) {
              console.error("Failed to parse JSON from response", e);
            }
          }

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

          setMessages(prev => prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, image: uploadedImageUrl || m.image } : m
          ));
          setMessages(prev => [...prev, assistantMsg]);

        } else {
          // Pure Search
          results = await api.searchByImage(file);

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

    // Text only
    const userMsg: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = messages
        .filter(m => m.content)
        .map(m => ({
          role: m.role === "user" ? "user" : "model" as "user" | "model",
          content: m.content || ""
        }));

      const response = await api.chat(text, history, undefined, accessToken);
      let assistantText = response.answer;
      let products = response.products || [];

      // Parse JSON from text logic
      // Regex to capture ```json ... ``` or just { ... } if it contains recommended_slugs
      console.log("DEBUG TEXT: Raw assistantText:", assistantText);

      let jsonMatch = assistantText.match(/```json\s*(\{[\s\S]*?"recommended_slugs"[\s\S]*?\})\s*```/);
      if (!jsonMatch) {
        jsonMatch = assistantText.match(/(\{[\s\S]*?"recommended_slugs"[\s\S]*?\})/);
      }

      if (jsonMatch) {
        try {
          const jsonStr = jsonMatch[1] || jsonMatch[0];
          console.log("DEBUG TEXT: Parsing JSON string:", jsonStr);
          const parsed = JSON.parse(jsonStr);

          if (parsed.recommended_slugs && Array.isArray(parsed.recommended_slugs)) {
            if (products.length === 0 && parsed.recommended_slugs.length > 0) {
              console.log("DEBUG TEXT: Found slugs:", parsed.recommended_slugs);
            }

            // Remove the JSON block from the text
            assistantText = assistantText.replace(jsonMatch[0], "").trim();
          }
        } catch (e) {
          console.error("Failed to parse JSON from response", e);
        }
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: assistantText,
        simulation_image: response.simulation_image
      };

      if (products.length > 0) {
        assistantMsg.blocks = [{
          type: "app",
          title: "",
          view: "carousel",
          products: products
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

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans text-primary">
      <Sidebar
        className="flex border-r-0 bg-secondary"
        onNewChat={() => { handleNewChat(); setCurrentView('chat'); }}
        history={history}
        onSelectChat={(id) => { handleSelectChat(id); setCurrentView('chat'); }}
        onDeleteChat={handleDeleteChat}
        projects={projects}
        onViewProjects={() => { setCurrentView('projects'); setActiveProjectId(null); }}
        onSelectProject={(id) => { setActiveProjectId(id); setCurrentView('project-detail'); }}
        onViewMaterials={() => { setCurrentView('materials'); setActiveProjectId(null); setActiveSource(null); }}
        sources={availableSources}
        onSelectSource={(id) => { setActiveSource(id); setCurrentView('materials'); setActiveProjectId(null); }}
        onDeleteSource={handleDeleteSource}
        onRenameSource={handleRenameSource}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-background relative h-full">
        {currentView === 'projects' && (
          <ProjectsView
            projects={projects}
            onSelectProject={(id) => { setActiveProjectId(id); setCurrentView('project-detail'); }}
            onCreateNew={() => {
              setIsProjectModalOpen(true);
              setProductToSave(null);
            }}
          />
        )}

        {currentView === 'project-detail' && projects.find(p => p.id === activeProjectId) && (
          <ProjectDetailView
            project={projects.find(p => p.id === activeProjectId)!}
            onBack={() => { setCurrentView('projects'); setActiveProjectId(null); }}
            onProductClick={handleProductClick}
            onRemoveItem={(p) => activeProjectId && handleRemoveFromProject(activeProjectId, p)}
            onProductAdded={(p) => activeProjectId && handleAddToProject(activeProjectId, p)}
            onRename={handleRenameProject}
            accessToken={accessToken}
          />
        )}

        {currentView === 'materials' && (
          <MaterialsView
            key={activeSource || 'all'}
            initialSource={activeSource || undefined}
            onBack={() => { setCurrentView('projects'); setActiveProjectId(null); }}
            onProductClick={handleProductClick}
            onSave={(p) => setProductToSave(p)}
            currencyMode={showRubles ? 'rub' : 'original'}
            exchangeRate={exchangeRate}
            onToggleCurrency={() => setShowRubles(!showRubles)}
            accessToken={accessToken}
          />
        )}

        {currentView === 'chat' && (
          <ChatView
            messages={messages}
            loading={loading}
            onSend={handleSend}
            onProductClick={handleProductClick}
            onSaveProduct={setProductToSave}
            selectedSources={selectedSources}
            availableSources={availableSources}
            onSourcesChange={handleSourcesChange}
            onOpenImportModal={() => setIsImportModalOpen(true)}
            accessToken={accessToken}
            initialProducts={initialProducts}
          />
        )}
      </main>

      {/* Modals */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-background overflow-y-auto animate-in slide-in-from-bottom-5 duration-300">
          <ProductFullView
            product={selectedProduct}
            onBack={() => setSelectedProduct(null)}
            onSave={(p) => setProductToSave(p)}
            onProductUpdate={(p) => setSelectedProduct(p)}
            currencyMode={showRubles ? 'rub' : 'original'}
            exchangeRate={exchangeRate}
            accessToken={accessToken}
          />
        </div>
      )}

      {productToSave && (
        <SaveToProjectModal
          product={productToSave}
          open={!!productToSave}
          onClose={() => setProductToSave(null)}
          projects={projects}
          onSave={handleAddToProject}
          onCreateProject={handleCreateProject}
        />
      )}

      {isProjectModalOpen && (
        <SaveToProjectModal
          product={null}
          open={isProjectModalOpen}
          onClose={() => setIsProjectModalOpen(false)}
          projects={projects}
          onSave={() => { }}
          onCreateProject={handleCreateProject}
        />
      )}

      <ImportJSONModal
        open={isImportModalOpen}
        onOpenChange={setIsImportModalOpen}
        onImportSuccess={(sourceId) => {
          api.getSources(accessToken).then(setAvailableSources);
        }}
        accessToken={accessToken}
      />
    </div>
  );
}
