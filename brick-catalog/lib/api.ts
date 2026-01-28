
const API_BASE_URL = 'http://localhost:8000/api';

export interface Product {
    slug: string;
    name: string;
    texture?: string;
    description?: string;
    article?: string;
    main_image?: string;
    gallery?: string[];
    color?: {
        base_color?: string;
        nuance?: string;
        additional_colors?: string[];
    };
    available_formats?: Array<{
        name: string;
        dimensions: string;
        weight?: string;
    }>;
    joints?: Array<{
        name: string;
    }>;
    vision_confidence?: number;
    analysis?: {
        color_description?: string;
        texture_description?: string;
    };
}

export interface ChatResponse {
    answer: string;
    products?: Product[];
    simulation_image?: string;
}

export const api = {
    async getProducts(query?: string, limit: number = 1000, color?: string): Promise<Product[]> {
        const params = new URLSearchParams();
        if (query) params.append('query', query);
        if (color && color !== 'all') params.append('color', color);
        params.append('limit', limit.toString());

        const url = `${API_BASE_URL}/products?${params.toString()}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch products');
        return res.json();
    },

    async getProduct(slug: string): Promise<Product> {
        const res = await fetch(`${API_BASE_URL}/products/${slug}`);
        if (!res.ok) throw new Error('Failed to fetch product');
        return res.json();
    },

    async chat(query: string, history: Array<{ role: 'user' | 'model', content: string }> = [], image?: string): Promise<ChatResponse> {
        const res = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, history, image })
        });
        if (!res.ok) throw new Error('Chat failed');
        return res.json();
    },

    async searchByImage(file: File): Promise<Product[]> {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${API_BASE_URL}/search`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error('Image search failed');
        return res.json();
    }
};
