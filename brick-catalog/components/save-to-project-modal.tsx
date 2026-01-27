"use client";

import { useState } from "react";
import { FolderPlus, Check, Plus, X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Product } from "@/lib/api";

interface Project {
    id: string;
    name: string;
    items: Product[];
}

interface SaveToProjectModalProps {
    product: Product | null;
    open: boolean;
    onClose: () => void;
    projects: Project[];
    onSave: (projectId: string, product: Product) => void;
    onCreateProject: (name: string) => void;
}

export function SaveToProjectModal({ product, open, onClose, projects, onSave, onCreateProject }: SaveToProjectModalProps) {
    const [newProjectName, setNewProjectName] = useState("");
    const [isCreating, setIsCreating] = useState(false);

    // If no product, we are just managing/creating projects.
    // The "Save" action might not be applicable, or we just want to create.

    const handleCreate = () => {
        if (newProjectName.trim()) {
            onCreateProject(newProjectName.trim());
            setNewProjectName("");
            setIsCreating(false);
            if (!product) {
                // If we are just creating, close after creation
                onClose();
            }
        }
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md bg-[#faf9f5] border-[#1f1e1d0f] rounded-xl shadow-2xl p-0 gap-0 overflow-hidden">
                <DialogHeader className="p-6 pb-2">
                    <DialogTitle className="text-xl font-serif text-[#141413]">
                        {product ? "Сохранить в проект" : "Ваши проекты"}
                    </DialogTitle>
                    {product && (
                        <div className="flex items-center gap-4 mt-4 bg-white p-2 rounded-lg border border-[#1f1e1d0f]">
                            <img
                                src={product.main_image}
                                alt={product.name}
                                className="w-12 h-12 object-cover rounded-md"
                            />
                            <div>
                                <div className="text-sm font-semibold text-[#141413]">{product.name}</div>
                                <div className="text-xs text-muted-foreground">{product.article}</div>
                            </div>
                        </div>
                    )}
                </DialogHeader>

                <div className="p-6 pt-2 space-y-4">
                    <div className="space-y-2">
                        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">Ваши проекты</div>

                        <div className="max-h-[200px] overflow-y-auto space-y-2 pr-2 scrollbar-thin">
                            {projects.length === 0 && (
                                <div className="text-sm text-center py-8 text-muted-foreground/50 border-2 border-dashed border-[#1f1e1d0f] rounded-lg">
                                    Нет проектов
                                </div>
                            )}

                            {projects.map((project) => {
                                const isAlreadySaved = product ? project.items.some(i => i.slug === product.slug) : false;
                                return (
                                    <button
                                        key={project.id}
                                        onClick={() => product && onSave(project.id, product)}
                                        disabled={isAlreadySaved || !product}
                                        className="w-full flex items-center justify-between p-3 rounded-lg bg-white border border-[#1f1e1d0f] hover:border-[#c6613f]/30 hover:shadow-sm transition-all text-left disabled:opacity-60 disabled:cursor-not-allowed group"
                                    >
                                        <span className="font-medium text-[#3d3d3a]">{project.name}</span>
                                        {isAlreadySaved ? (
                                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full flex items-center gap-1">
                                                <Check className="h-3 w-3" /> Сохранено
                                            </span>
                                        ) : (
                                            <div className="text-xs text-muted-foreground group-hover:text-[#c6613f]">
                                                {project.items.length} фото
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {isCreating ? (
                        <div className="flex gap-2 animate-in fade-in slide-in-from-top-2">
                            <Input
                                value={newProjectName}
                                onChange={(e) => setNewProjectName(e.target.value)}
                                placeholder="Название проекта..."
                                className="bg-white"
                                autoFocus
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') handleCreate();
                                    if (e.key === 'Escape') setIsCreating(false);
                                }}
                            />
                            <Button onClick={handleCreate} disabled={!newProjectName.trim()} className="shrink-0 bg-[#c6613f] hover:bg-[#b55232] text-white">
                                Создать
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => setIsCreating(false)} className="shrink-0">
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ) : (
                        <Button
                            variant="outline"
                            onClick={() => setIsCreating(true)}
                            className="w-full border-dashed border-[#1f1e1d26] text-muted-foreground hover:text-[#c6613f] hover:border-[#c6613f] hover:bg-transparent"
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Новый проект
                        </Button>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
