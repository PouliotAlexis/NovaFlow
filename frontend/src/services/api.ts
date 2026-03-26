// NovaFlow API Service

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function getAuthHeaders() {
    const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
    return {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
    };
}

export const api = {
    async get(endpoint: string) {
        const headers = await getAuthHeaders();
        const url = `${API_BASE_URL}${endpoint}`;
        console.log(`[DEBUG API] GET Request to: "${url}"`, { headers });
        try {
            const response = await fetch(url, {
                method: "GET",
                headers,
                cache: 'no-store'
            });
            console.log(`[DEBUG API] GET Response for "${url}":`, response.status);
            
            if (response.status === 401) {
                this.handleUnauthorized();
            }
            return response;
        } catch (error) {
            console.error(`[DEBUG API] GET FETCH ERROR for "${url}":`, error);
            throw error;
        }
    },

    async post(endpoint: string, data?: any, signal?: AbortSignal) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers,
            body: data ? JSON.stringify(data) : undefined,
            signal
        });
        if (response.status === 401) {
            this.handleUnauthorized();
        }
        return response;
    },

    async patch(endpoint: string, data?: any) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "PATCH",
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
        if (response.status === 401) {
            this.handleUnauthorized();
        }
        return response;
    },

    async delete(endpoint: string) {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "DELETE",
            headers
        });
        if (response.status === 401) {
            this.handleUnauthorized();
        }
        return response;
    },

    handleUnauthorized() {
        if (typeof window !== "undefined") {
            localStorage.removeItem("nf_token");
            localStorage.removeItem("nf_user");
            window.location.href = "/auth/login";
        }
    },
    
    // Support pour le streaming de chat
    async stream(endpoint: string, data: any, signal?: AbortSignal) {
        const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { "Authorization": `Bearer ${token}` } : {})
            },
            body: JSON.stringify(data),
            signal
        });

        if (response.status === 401) {
            this.handleUnauthorized();
        }
        return response;
    }
};
