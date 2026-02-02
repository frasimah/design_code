import { Product } from "@/lib/api";

export interface Message {
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

export interface HistoryItem {
    id: string;
    title: string;
    date: string;
    messages: Message[];
}
