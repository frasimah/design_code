
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { MessageSquare, Folder, Boxes, Plus, PanelLeftClose, PanelLeftOpen, FolderOpen, ChevronRight, Trash2, Globe, Pencil, Check, X, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuthButton } from "@/components/auth-button";
import Link from "next/link";

type Project = { id: string; name: string; items: unknown[] };

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    onNewChat?: () => void;
    history?: { id: string; title: string; date: string }[];
    onSelectChat?: (id: string) => void;
    onDeleteChat?: (id: string) => void;
    projects?: Project[];
    onViewProjects?: () => void;
    onSelectProject?: (id: string) => void;
    onViewMaterials?: () => void;
    sources?: { id: string; name: string }[];
    onSelectSource?: (id: string) => void;
    onDeleteSource?: (id: string) => void;
    onRenameSource?: (id: string, newName: string) => void;
}

export function Sidebar({ className, onNewChat, history, onSelectChat, onDeleteChat, projects, onViewProjects, onSelectProject, onViewMaterials, sources, onSelectSource, onDeleteSource, onRenameSource, ...props }: SidebarProps) {
    const [collapsed, setCollapsed] = React.useState(false);

    // Default to collapsed on mobile
    React.useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 768) {
                setCollapsed(true);
            }
        };

        // Check on mount
        handleResize();

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    return (
        <div
            className={cn(
                "flex flex-col border-r border-[#1f1e1d0f] bg-[#faf9f5] h-screen transition-all duration-300",
                collapsed ? "w-[60px]" : "w-[240px]",
                className
            )}
            {...props}
        >
            <div className="flex items-center justify-between p-3 h-[80px] mt-1 pl-4">
                {!collapsed && <img src="/logo.svg" alt="Vandersanden" className="h-[34px]" />}
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground/60 hover:text-foreground ml-auto"
                    onClick={() => setCollapsed(!collapsed)}
                >
                    {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
                </Button>
            </div>

            <div className="flex-1 py-2 px-3 flex flex-col gap-1 overflow-y-auto">
                <Button
                    onClick={(e) => {
                        e.preventDefault();
                        onNewChat?.();
                    }}
                    className={cn(
                        "w-full justify-start gap-2 h-9 mb-4 rounded-lg bg-white border border-[#1f1e1d0f] text-[#3d3d3a] hover:bg-white hover:border-[#1f1e1d26] shadow-sm transition-all active:scale-[0.98]",
                        collapsed && "px-0 justify-center"
                    )}
                >
                    <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />
                    {!collapsed && <span className="text-sm font-medium">Новый чат</span>}
                </Button>

                <div className="space-y-0.5">
                    <NavItem icon={<MessageSquare className="h-4 w-4" />} label="Чаты" collapsed={collapsed} />

                    {/* Chat History List */}
                    {!collapsed && history && history.length > 0 && (
                        <div className="pl-2 pr-1 py-2 space-y-1 animate-in fade-in slide-in-from-left-2 overflow-y-auto max-h-[250px] scrollbar-hide">
                            <div className="text-[11px] font-semibold text-muted-foreground/50 px-2 uppercase tracking-wider mb-2">История</div>
                            {history.map((chat) => (
                                <SwipeableHistoryItem
                                    key={chat.id}
                                    chat={chat}
                                    onSelect={() => onSelectChat?.(chat.id)}
                                    onDelete={() => onDeleteChat?.(chat.id)}
                                />
                            ))}
                        </div>
                    )}

                    <CollapsibleProjects
                        collapsed={collapsed}
                        projects={projects}
                        onViewProjects={onViewProjects}
                        onSelectProject={onSelectProject}
                    />

                    <CollapsibleMaterials
                        collapsed={collapsed}
                        sources={sources}
                        onViewMaterials={onViewMaterials}
                        onSelectSource={onSelectSource}
                        onDeleteSource={onDeleteSource}
                        onRenameSource={onRenameSource}
                    />
                </div>
            </div>

            <div className="p-3 mt-auto border-t border-[#1f1e1d0f] space-y-1">
                <Button
                    asChild
                    variant="ghost"
                    className={cn(
                        "w-full justify-start gap-3 h-9 px-2 text-[#565552] hover:bg-[#1f1e1d0f] transition-colors",
                        collapsed && "justify-center px-0"
                    )}
                >
                    <Link href="/settings">
                        <Settings className="h-4 w-4 shrink-0" />
                        {!collapsed && <span className="truncate text-sm font-medium">Настройки</span>}
                    </Link>
                </Button>
                {collapsed ? (
                    <AuthButton />
                ) : (
                    <AuthButton />
                )}
            </div>
        </div >
    );
}

function NavItem({ icon, label, collapsed, active, isUser }: { icon: React.ReactNode; label: string; collapsed: boolean; active?: boolean; isUser?: boolean }) {
    return (
        <Button
            variant={"ghost"}
            className={cn(
                "w-full justify-start gap-3 h-9 px-2 text-[#565552] hover:bg-[#1f1e1d0f] transition-colors",
                collapsed && "justify-center px-0",
                active && "bg-[#1f1e1d0f]"
            )}
        >
            <span className={cn("shrink-0", !isUser && "text-muted-foreground/70")}>{icon}</span>
            {!collapsed && <span className="truncate text-sm font-medium">{label}</span>}
        </Button>
    );
}



function SwipeableHistoryItem({ chat, onSelect, onDelete }: { chat: { id: string; title: string }; onSelect: () => void; onDelete: () => void }) {
    return (
        <div className="relative group rounded-md hover:bg-[#1f1e1d0f] transition-colors">
            <button
                onClick={onSelect}
                className="w-full text-left px-2 py-1.5 text-[13px] text-[#565552] truncate pr-8"
                title={chat.title}
            >
                {chat.title}
            </button>

            {/* Delete Action (Visible on Hover) */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onDelete();
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/40 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                title="Удалить чат"
            >
                <Trash2 className="h-3.5 w-3.5" />
            </button>
        </div>
    );
}

function CollapsibleProjects({ collapsed, projects, onViewProjects, onSelectProject }: { collapsed: boolean; projects?: Project[]; onViewProjects?: () => void; onSelectProject?: (id: string) => void }) {
    const [isExpanded, setIsExpanded] = React.useState(true);

    if (!projects || projects.length === 0) {
        return (
            <div className="mt-4" onClick={onViewProjects}>
                <NavItem icon={<Folder className="h-4 w-4" />} label="Проекты" collapsed={collapsed} />
            </div>
        );
    }

    return (
        <div className="mt-4 animate-in fade-in slide-in-from-left-2">
            <div className="flex items-center group">
                <div className="flex-1" onClick={onViewProjects}>
                    <NavItem icon={<Folder className="h-4 w-4" />} label="Проекты" collapsed={collapsed} />
                </div>
                {!collapsed && (
                    <button
                        onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                        className="mr-2 p-1 text-muted-foreground/50 hover:text-foreground transition-colors"
                    >
                        <ChevronRight className={cn("h-3 w-3 transition-transform", isExpanded && "rotate-90")} />
                    </button>
                )}
            </div>

            {!collapsed && isExpanded && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                    {projects.map(project => (
                        <button
                            key={project.id}
                            onClick={() => onSelectProject?.(project.id)}
                            className="w-full text-left px-2 py-1.5 text-[13px] text-[#565552] hover:bg-[#1f1e1d0f] rounded-md truncate transition-colors flex items-center gap-2 group"
                        >
                            <FolderOpen className="h-3.5 w-3.5 text-muted-foreground/70 group-hover:text-[#c6613f]" />
                            <span className="truncate flex-1">{project.name}</span>
                            <span className="text-[10px] text-muted-foreground bg-white px-1.5 py-0.5 rounded-full border border-black/5">
                                {project.items.length}
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

function CollapsibleMaterials({
    collapsed,
    sources,
    onViewMaterials,
    onSelectSource,
    onDeleteSource,
    onRenameSource
}: {
    collapsed: boolean;
    sources?: { id: string; name: string }[];
    onViewMaterials?: () => void;
    onSelectSource?: (id: string) => void;
    onDeleteSource?: (id: string) => void;
    onRenameSource?: (id: string, newName: string) => void;
}) {
    const [isExpanded, setIsExpanded] = React.useState(true);
    const [editingId, setEditingId] = React.useState<string | null>(null);
    const [editName, setEditName] = React.useState("");

    const isCustom = (id: string) => !['catalog', 'woocommerce'].includes(id);

    const handleStartEdit = (e: React.MouseEvent, id: string, name: string) => {
        e.stopPropagation();
        setEditingId(id);
        setEditName(name);
    };

    const handleSaveEdit = (e: React.SyntheticEvent) => {
        e.stopPropagation();
        if (editingId && editName.trim()) {
            onRenameSource?.(editingId, editName.trim());
            setEditingId(null);
        }
    };

    const handleCancelEdit = (e: React.SyntheticEvent) => {
        e.stopPropagation();
        setEditingId(null);
    };

    return (
        <div className="mt-2 animate-in fade-in slide-in-from-left-2">
            <div className="flex items-center group">
                <div className="flex-1" onClick={onViewMaterials}>
                    <NavItem icon={<Boxes className="h-4 w-4" />} label="Каталог" collapsed={collapsed} />
                </div>
                {!collapsed && (
                    <button
                        onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                        className="mr-2 p-1 text-muted-foreground/50 hover:text-foreground transition-colors"
                    >
                        <ChevronRight className={cn("h-3 w-3 transition-transform", isExpanded && "rotate-90")} />
                    </button>
                )}
            </div>

            {!collapsed && isExpanded && (
                <div className="pl-6 pr-1 py-1 space-y-1">
                    {/* All Materials (Reset Filter) */}
                    <div className="relative group rounded-md hover:bg-[#1f1e1d0f] transition-colors flex items-center">
                        <button
                            onClick={onViewMaterials}
                            className="w-full text-left px-2 py-1.5 text-[13px] text-[#565552] truncate flex items-center gap-2"
                        >
                            <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
                            <span className="truncate flex-1">Все</span>
                        </button>
                    </div>

                    {/* Sources List */}
                    {sources?.map(source => (
                        <div
                            key={source.id}
                            className="relative group rounded-md hover:bg-[#1f1e1d0f] transition-colors flex items-center min-h-[32px]"
                        >
                            {editingId === source.id ? (
                                <div className="flex items-center w-full px-2 gap-1" onClick={(e) => e.stopPropagation()}>
                                    <input
                                        type="text"
                                        value={editName}
                                        onChange={(e) => setEditName(e.target.value)}
                                        className="flex-1 h-6 text-[13px] bg-white border border-input rounded px-1 focus:outline-none focus:ring-1 focus:ring-ring"
                                        autoFocus
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleSaveEdit(e);
                                            if (e.key === 'Escape') handleCancelEdit(e);
                                        }}
                                    />
                                    <button onClick={handleSaveEdit} className="p-0.5 hover:text-green-600 text-muted-foreground">
                                        <Check className="h-3.5 w-3.5" />
                                    </button>
                                    <button onClick={handleCancelEdit} className="p-0.5 hover:text-red-600 text-muted-foreground">
                                        <X className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <button
                                        onClick={() => onSelectSource?.(source.id)}
                                        className="w-full text-left px-2 py-1.5 text-[13px] text-[#565552] truncate pr-16 flex items-center gap-2"
                                    >
                                        {source.id === 'woocommerce' ? (
                                            <Globe className="h-3 w-3 text-muted-foreground/70" />
                                        ) : (
                                            <span className={cn("w-1.5 h-1.5 rounded-full", isCustom(source.id) ? "bg-amber-500" : "bg-neutral-400")} />
                                        )}
                                        <span className="truncate flex-1" title={source.name}>{source.name}</span>
                                    </button>

                                    {/* Action Buttons */}
                                    <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={(e) => handleStartEdit(e, source.id, source.name)}
                                            className="p-1 text-muted-foreground/40 hover:text-blue-500 transition-colors"
                                            title="Переименовать"
                                        >
                                            <Pencil className="h-3 w-3" />
                                        </button>

                                        {isCustom(source.id) && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteSource?.(source.id);
                                                }}
                                                className="p-1 text-muted-foreground/40 hover:text-red-500 transition-colors"
                                                title="Удалить источник"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
