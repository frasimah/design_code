
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { MessageSquare, Folder, Boxes, Code2, Plus, LogOut, PanelLeftClose, PanelLeftOpen, FolderOpen, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    onNewChat?: () => void;
    history?: { id: string; title: string; date: string }[];
    onSelectChat?: (id: string) => void;
    onDeleteChat?: (id: string) => void;
    projects?: { id: string; name: string; items: any[] }[];
    onViewProjects?: () => void;
    onSelectProject?: (id: string) => void;
    onViewMaterials?: () => void;
}

export function Sidebar({ className, onNewChat, history, onSelectChat, onDeleteChat, projects, onViewProjects, onSelectProject, onViewMaterials, ...props }: SidebarProps) {
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
                {!collapsed && <img src="/logo.svg" alt="Vandersanden" className="h-[48px]" />}
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

                    <div onClick={onViewMaterials}>
                        <NavItem icon={<Boxes className="h-4 w-4" />} label="Материалы" collapsed={collapsed} />
                    </div>
                </div>
            </div>

            <div className="p-3 mt-auto border-t border-[#1f1e1d0f]">
                <NavItem icon={<div className="h-5 w-5 rounded-full bg-[#c6613f] text-white flex items-center justify-center text-[10px] font-bold">AS</div>} label="Alexandr S." collapsed={collapsed} isUser />
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

import { Trash2 } from "lucide-react";

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

function CollapsibleProjects({ collapsed, projects, onViewProjects, onSelectProject }: { collapsed: boolean; projects?: any[]; onViewProjects?: () => void; onSelectProject?: (id: string) => void }) {
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
