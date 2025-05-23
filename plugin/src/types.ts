import { WorkspaceLeaf } from 'obsidian';

export interface SettingsData {
    serverUrl: string;
    apiKey: string;
    autoStartServer: boolean;
    embedModel: string;
    maxResults: number;
    chunkSize: number;
    chunkOverlap: number;
    preserveMarkdown: boolean;
    useNeuralEngine: boolean;
    debugMode: boolean;
    cacheEnabled: boolean;
    maxCacheSize: number;
    defaultVault?: string;
}

export interface SearchResult {
    content: string;
    source: string;
    similarity: number;
    metadata: {
        [key: string]: any;
    };
}

export interface IndexingStatus {
    isIndexing: boolean;
    progress: number;
    totalFiles: number;
    processedFiles: number;
}

export interface BenchmarkProgress {
    stage: string;
    progress: number;
    message: string;
}

export interface ServerStatus {
    isRunning: boolean;
    url: string;
    pid?: number;
    error?: string;
}

// View interfaces
export interface SearchViewProps {
    leaf: WorkspaceLeaf;
}

export interface StatusBarProps {
    indexingStatus: IndexingStatus;
    serverStatus: ServerStatus;
}

// Service interfaces
export interface RAGServiceInterface {
    search(query: string, maxResults?: number): Promise<SearchResult[]>;
    indexVault(): Promise<void>;
    handleFileModify(): Promise<void>;
    runBenchmark(): Promise<void>;
    updateSettings(settings: SettingsData): void;
}

export interface ServerManagerInterface {
    startServer(): Promise<void>;
    stopServer(): Promise<void>;
    getStatus(): Promise<ServerStatus>;
    updateSettings(settings: SettingsData): void;
}

// Event types
export type IndexingProgressCallback = (status: IndexingStatus) => void;
export type BenchmarkProgressCallback = (progress: BenchmarkProgress) => void;
export type ServerStatusCallback = (status: ServerStatus) => void;

// API Response types
export interface SearchResponse {
    results: SearchResult[];
    timing: {
        total_ms: number;
        embedding_ms: number;
        search_ms: number;
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