"use client";

import { Product } from "@/lib/api";
import { Lock } from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface Project {
    id: string;
    name: string;
    items: Product[];
}

interface ProjectBoardCardProps {
    project: Project;
    onClick: () => void;
}

export function ProjectBoardCard({ project, onClick }: ProjectBoardCardProps) {
    const coverImage = project.items[0]?.main_image;
    const image2 = project.items[1]?.main_image;
    const image3 = project.items[2]?.main_image;

    return (
        <div
            onClick={onClick}
            className="group cursor-pointer flex flex-col gap-2"
        >
            {/* Collage Container */}
            <div className="aspect-[236/157] w-full rounded-2xl overflow-hidden grid grid-cols-3 gap-0.5 bg-secondary/30 relative">
                {/* Main large image (Left, spans 2 cols if only 1 image, or 2/3 width) */}
                <div className={cn(
                    "h-full relative bg-secondary/50 transition-all",
                    (image2 || image3) ? "col-span-2" : "col-span-3"
                )}>
                    {coverImage ? (
                        <Image
                            src={coverImage}
                            alt={project.name}
                            fill
                            className="object-cover group-hover:brightness-95 transition-all duration-300"
                            sizes="(max-width: 768px) 66vw, 20vw"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center bg-[#f0eee6]" />
                    )}
                </div>

                {/* Right Column (Stacked images) */}
                {(image2 || image3) && (
                    <div className="col-span-1 flex flex-col gap-0.5 h-full">
                        <div className="h-1/2 relative bg-secondary/50">
                            {image2 && (
                                <Image
                                    src={image2}
                                    alt=""
                                    fill
                                    className="object-cover group-hover:brightness-95 transition-all duration-300"
                                    sizes="(max-width: 768px) 33vw, 10vw"
                                />
                            )}
                        </div>
                        <div className="h-1/2 relative bg-secondary/50">
                            {image3 && (
                                <Image
                                    src={image3}
                                    alt=""
                                    fill
                                    className="object-cover group-hover:brightness-95 transition-all duration-300"
                                    sizes="(max-width: 768px) 33vw, 10vw"
                                />
                            )}
                        </div>
                    </div>
                )}

                {/* Hover Overlay */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors duration-300" />
            </div>

            {/* Info */}
            <div className="px-1">
                <h3 className="font-semibold text-[#141413] text-[20px] leading-tight truncate">
                    {project.name}
                </h3>
                <div className="flex items-center gap-2 text-xs text-[#565552] mt-1">
                    <span>{project.items.length} пинов</span>
                    <span className="text-[#1f1e1d40]">•</span>
                    <span>1 ч.</span>
                </div>
            </div>
        </div>
    );
}
