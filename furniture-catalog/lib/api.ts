// Use relative path in production (proxy via Next.js or Nginx), fallback to localhost for dev
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

// Helper to get auth headers if token is available
function getAuthHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export interface Product {
    slug: string;
    name: string;
    title?: string; // Russian title
    brand?: string;
    source?: string; // Origin source
    price?: number;
    currency?: string;
    attributes?: Record<string, string>; // Dynamic attributes
    parameters?: Record<string, string>; // Technical parameters (height, weight etc)
    dimensions?: string;
    materials?: string[];
    material?: string; // Primary material
    images?: string[]; // New images array
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

export interface Project {
    id: string;
    name: string;
    items: Product[];
}

export interface ChatResponse {
    answer: string;
    products?: Product[];
    simulation_image?: string;
}

export interface ImportStatus {
    status: string;
    message: string;
    source_id?: string;
}

export interface UpdatePriceResponse {
    status: string;
    message: string;
    product: Product;
}

export interface UpdateImageResponse {
    status: string;
    image_url: string;
}

export interface DeleteImageResponse {
    status: string;
    deleted_image: string;
}

export interface DeleteProductResponse {
    status: string;
    message: string;
}

export const api = {
    async getProducts(query?: string, limit: number = 50, color?: string, source: string = 'catalog', skip: number = 0, category?: string, sort?: string, brand?: string, token?: string, stock_status?: string): Promise<{ items: Product[], total: number }> {
        const params = new URLSearchParams();
        if (query) params.append('query', query);
        if (color && color !== 'all') params.append('color', color);
        if (category && category !== 'all') params.append('category', category);
        if (brand && brand !== 'all') params.append('brand', brand);
        if (sort && sort !== 'default') params.append('sort', sort);
        if (stock_status && stock_status !== 'all') params.append('stock_status', stock_status);
        if (source) params.append('source', source);
        params.append('limit', limit.toString());
        params.append('skip', skip.toString());

        const url = `${API_BASE_URL}/products/?${params.toString()}`;
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error('Failed to fetch products');
        return res.json();
    },

    async getCategories(source: string = 'catalog', brand?: string): Promise<{ id: string, name: string }[]> {
        const params = new URLSearchParams({ source });
        if (brand && brand !== 'all') params.append('brand', brand);
        const res = await fetch(`${API_BASE_URL}/products/categories/?${params.toString()}`);
        if (!res.ok) throw new Error('Failed to fetch categories');
        return res.json();
    },

    async getBrands(source: string = 'catalog'): Promise<{ id: string, name: string }[]> {
        const res = await fetch(`${API_BASE_URL}/products/brands/?source=${source}`);
        if (!res.ok) throw new Error('Failed to fetch brands');
        return res.json();
    },

    async getProduct(slug: string): Promise<Product> {
        const res = await fetch(`${API_BASE_URL}/products/${slug}/`);
        if (!res.ok) throw new Error('Failed to fetch product');
        return res.json();
    },

    async chat(query: string, history: Array<{ role: 'user' | 'model', content: string }> = [], image?: string, token?: string): Promise<ChatResponse> {
        const res = await fetch(`${API_BASE_URL}/chat/`, {
            method: 'POST',
            headers: getAuthHeaders(token),
            body: JSON.stringify({ query, history, image })
        });
        if (!res.ok) throw new Error('Chat failed');
        return res.json();
    },

    async getChatHistory(token?: string): Promise<Array<{ role: 'user' | 'assistant', content: string, products?: Product[] }>> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE_URL}/chat/history/`, { headers });
        if (!res.ok) throw new Error('Failed to fetch chat history');
        return res.json();
    },

    async searchByImage(file: File): Promise<Product[]> {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${API_BASE_URL}/search/`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error('Image search failed');
        return res.json();
    },

    async getProjects(token?: string): Promise<Project[]> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE_URL}/projects/`, { headers });
        if (!res.ok) throw new Error("Failed to fetch projects");
        return res.json();
    },

    async saveProjects(projects: Project[], token?: string): Promise<Project[]> {
        const res = await fetch(`${API_BASE_URL}/projects/`, {
            method: "POST",
            headers: getAuthHeaders(token),
            body: JSON.stringify(projects)
        });
        if (!res.ok) throw new Error("Failed to save projects");
        return res.json();
    },


    async importCatalog(file: File, name: string, token?: string): Promise<{ status: string, message: string, source_id: string }> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', name);

        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/products/import/`, {
            method: 'POST',
            headers,
            body: formData
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Import failed');
        }
        return res.json();
    },

    async syncWoocommerceCatalog(token?: string): Promise<{ status: string, message: string }> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/products/sync-woocommerce`, {
            method: 'POST',
            headers
        });

        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to start sync');
        }
        return res.json();
    },

    async getSyncStatus(token?: string): Promise<{
        is_running: boolean;
        status: string;
        fetched: number;
        total_est: number;
        message: string;
        error: string | null;
        started_at: number;
    }> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/products/sync-woocommerce/status`, {
            headers
        });

        if (!res.ok) throw new Error('Failed to get sync status');
        return res.json();
    },

    async getSources(token?: string): Promise<{ id: string, name: string }[]> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const response = await fetch(`${API_BASE_URL}/products/sources/`, { headers });
        return response.json();
    },

    async deleteSource(sourceId: string, token?: string): Promise<ImportStatus> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/sources/${sourceId}`, {
            method: 'DELETE',
            headers
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete source');
        }
        return response.json();
    },

    async renameSource(sourceId: string, name: string, token?: string): Promise<ImportStatus> {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/sources/${sourceId}/rename`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ name })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to rename source');
        }
        return response.json();
    },

    async updateProductPrice(slug: string, price: number, currency: string = "EUR", token?: string): Promise<UpdatePriceResponse> {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/${slug}/price`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ price, currency })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update price');
        }
        return response.json();
    },

    async updateProductTitle(slug: string, title: string, token?: string): Promise<{ status: string; title: string }> {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/${slug}/title`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ title })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update title');
        }
        return response.json();
    },

    async updateProductImage(slug: string, imageUrl: string, token?: string): Promise<UpdateImageResponse> {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/${slug}/image`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ image_url: imageUrl })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update image');
        }
        return response.json();
    },

    async deleteProductImage(slug: string, imageUrl: string, token?: string): Promise<DeleteImageResponse> {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/${slug}/image`, {
            method: 'DELETE',
            headers,
            body: JSON.stringify({ image_url: imageUrl })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete image');
        }
        return response.json();
    },

    async deleteProduct(slug: string, token?: string): Promise<DeleteProductResponse> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE_URL}/products/${slug}`, {
            method: 'DELETE',
            headers
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete product');
        }
        return response.json();
    },

    async getCurrencyRate(): Promise<{ currency: string, rate: number, source: string }> {
        const response = await fetch(`${API_BASE_URL}/currency/rate`);
        if (!response.ok) {
            return { currency: "RUB", rate: 105.0, source: "fallback_client" };
        }
        return response.json();
    },

    getProxyImageUrl(url?: string): string {
        if (!url || typeof url !== 'string') return '';
        // If it's an external URL (not localhost/127.0.0.1), proxy it
        if (url.startsWith('http') && !url.includes('localhost') && !url.includes('127.0.0.1')) {
            return `${API_BASE_URL}/products/proxy-image?url=${encodeURIComponent(url)}`;
        }
        return url;
    },

    async uploadImage(file: File, token?: string): Promise<{ url: string }> {
        const formData = new FormData();
        formData.append('file', file);

        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/upload/image`, {
            method: 'POST',
            headers,
            body: formData
        });
        if (!res.ok) throw new Error('Upload failed');
        const data = await res.json();
        // Return full URL by prepending base if needed, currently server returns /uploads/uuid.ext relative to root
        return { url: `${API_BASE_URL.replace('/api', '')}${data.url}` };
    },

    async getProfile(token?: string): Promise<UserProfile> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(`${API_BASE_URL}/profile/`, { headers });
        if (!res.ok) {
            // If 401, return empty profile or throw
            if (res.status === 401) throw new Error("Unauthorized");
            return { manager_name: "", phone: "", email: "", company_name: "" };
        }
        return res.json();
    },

    async saveProfile(profile: UserProfile, token?: string): Promise<UserProfile> {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        try {
            const res = await fetch(`${API_BASE_URL}/profile/`, {
                method: "PUT",
                headers: getAuthHeaders(token),
                body: JSON.stringify(profile),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!res.ok) throw new Error("Failed to save profile");
            return res.json();
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    },

    async printProject(slug: string, token?: string): Promise<string> {
        const headers: HeadersInit = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE_URL}/print/${slug}`, { headers });
        if (!res.ok) {
            if (res.status === 401) throw new Error("Unauthorized");
            const error = await res.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to generate proposal');
        }
        return res.text();
    }
};

export interface UserProfile {
    manager_name: string;
    phone: string;
    email: string;
    company_name: string;
}
