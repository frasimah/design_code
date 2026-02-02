import { useState } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'; // Adjust for production

export interface Product {
    slug: string;
    name: string;
    article?: string;
    base_color?: string;
    texture?: string;
    image_url?: string;
    distance?: number;
    price?: number;
    [key: string]: unknown;
}

export interface ChatResponse {
    answer: string;
    products?: Product[];
    simulation_image?: string;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    products?: Product[];
    image?: string; // For simulation or uploaded image
}

export async function sendMessage(query: string, history: ChatMessage[] = []): Promise<ChatResponse> {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                history: history.map(h => ({ role: h.role, parts: [h.content] })) // Format for backend if needed, or simple list
            }),
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error("Chat API Error:", error);
        throw error;
    }
}
