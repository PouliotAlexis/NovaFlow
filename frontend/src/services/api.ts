// NovaFlow API Service

const API_BASE_URL = "";

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
                // Redirection vers login si token invalide
                if (typeof window !== "undefined") {
                    localStorage.removeItem("nf_token");
                    localStorage.removeItem("nf_user");
                    window.location.href = "/auth/login";
                }
            }
            return response;
        } catch (error) {
            console.error(`[DEBUG API] GET FETCH ERROR for "${url}":`, error);
            throw error;
        }
    },

    async post(endpoint: string, data?: any) {
        const headers = await getAuthHeaders();
        return fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
    },

    async patch(endpoint: string, data?: any) {
        const headers = await getAuthHeaders();
        return fetch(`${API_BASE_URL}${endpoint}`, {
            method: "PATCH",
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
    },

    async delete(endpoint: string) {
        const headers = await getAuthHeaders();
        return fetch(`${API_BASE_URL}${endpoint}`, {
            method: "DELETE",
            headers
        });
    },
    
    // Support pour le streaming de chat
    async stream(endpoint: string, data: any) {
        const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : null;
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { "Authorization": `Bearer ${token}` } : {})
            },
            body: JSON.stringify(data)
        });

        if (response.status === 401) {
            if (typeof window !== "undefined") {
                localStorage.removeItem("nf_token");
                localStorage.removeItem("nf_user");
                window.location.href = "/auth/login";
            }
        }
        return response;
    }
};
