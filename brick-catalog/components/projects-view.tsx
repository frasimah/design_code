"use client";

import { ProjectBoardCard } from "./project-board-card";
import { ArrowLeft, Plus } from "lucide-react";
import { Button } from "./ui/button";
import { Product } from "@/lib/api";

interface Project {
    id: string;
    name: string;
    items: Product[];
}

interface ProjectsViewProps {
    projects: Project[];
    onSelectProject: (id: string) => void;
    onCreateNew?: () => void;
}

export function ProjectsView({ projects, onSelectProject, onCreateNew }: ProjectsViewProps) {
    return (
        <div className="max-w-[calc(100%-2rem)] md:max-w-4xl mx-auto w-full py-8 pl-12 md:pl-0">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-[#c6613f] text-white flex items-center justify-center text-sm font-bold">AS</div>
                    <h1 className="text-2xl font-bold text-[#141413]">Ваши проекты</h1>
                </div>
                <Button variant="outline" className="gap-2" onClick={onCreateNew}>
                    <Plus className="h-4 w-4" />
                    Новый проект
                </Button>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-10">
                {projects.map(project => (
                    <ProjectBoardCard
                        key={project.id}
                        project={project}
                        onClick={() => onSelectProject(project.id)}
                    />
                ))}

                {/* Create New Placeholder Card */}
                <button
                    onClick={onCreateNew}
                    className="group flex flex-col gap-2 text-left"
                >
                    <div className="aspect-[236/157] w-full rounded-2xl overflow-hidden bg-secondary/30 flex items-center justify-center border-2 border-dashed border-[#1f1e1d1a] group-hover:border-[#c6613f]/50 transition-colors">
                        <Plus className="h-8 w-8 text-muted-foreground group-hover:text-[#c6613f] transition-colors" />
                    </div>
                    <div className="px-1">
                        <h3 className="font-semibold text-[#141413] text-[20px]">Создать проект</h3>
                    </div>
                </button>
            </div>
        </div>
    );
}
