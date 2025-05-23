export interface ChatResponse {
    response: string;
    sources: Array<{
        file: string;
        chunk: string;
        similarity?: number;
    }>;
}

export interface VaultConfig {
    name: string;
    path: string;
    file_types: string[];
    enabled: boolean;
}

export interface Document {
    content: string;
    metadata: {
        path: string;
        name: string;
        size: number;
        created: number;
        modified: number;
    };
}

export interface BenchmarkResponse {
    optimal_settings: {
        model_name: string;
        batch_size: number;
        compute_units?: string;
        expected_latency_ms: number;
        expected_throughput: number;
        expected_memory_mb: number;
    };
    results: Array<{
        config: string;
        latency_ms: number;
        throughput: number;
        memory_mb: number;
    }>;
}

export class RAGApi {
    private baseUrl: string;
    private apiKey?: string;

    constructor(baseUrl: string, apiKey?: string) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }

    private async request(endpoint: string, options: RequestInit = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        if (this.apiKey) {
            options.headers = {
                ...options.headers,
                'Authorization': `Bearer ${this.apiKey}`
            };
        }

        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        return response.json();
    }

    async search(query: string, maxResults = 5) {
        return this.request('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query, max_results: maxResults })
        });
    }

    async chat(query: string, vaultName?: string): Promise<ChatResponse> {
        return this.request('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query, vault_name: vaultName })
        });
    }

    async listVaults(): Promise<VaultConfig[]> {
        return this.request('/vaults');
    }

    async addVault(config: VaultConfig): Promise<{ status: string; vault: VaultConfig }> {
        return this.request('/vault', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
    }

    async processVault(name: string): Promise<{ status: string; stats: any }> {
        return this.request(`/vault/${name}/process`, {
            method: 'POST'
        });
    }

    async getServerStatus(): Promise<{ status: string; version: string; stats: any }> {
        return this.request('/');
    }

    async indexDocument(document: Document): Promise<void> {
        await this.request('/index', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ document })
        });
    }

    async runBenchmark(): Promise<BenchmarkResponse> {
        return this.request('/benchmark', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
} 