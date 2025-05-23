import { Notice, TFile } from 'obsidian';
import { App } from 'obsidian';
import { SettingsData, SearchResult, IndexingStatus, RAGServiceInterface } from '../types';
import RAGPlugin from '../main';
import { debounce } from 'lodash';

export class RAGService implements RAGServiceInterface {
    private settings: SettingsData;
    private app: App;
    private plugin: RAGPlugin;
    private isIndexing: boolean;
    private modifiedFiles: Set<string>;
    private indexingProgress: IndexingStatus;
    private indexDebounced: () => void;
    
    constructor(settings: SettingsData, app: App, plugin: RAGPlugin) {
        this.settings = settings;
        this.app = app;
        this.plugin = plugin;
        this.isIndexing = false;
        this.modifiedFiles = new Set();
        this.indexingProgress = {
            isIndexing: false,
            progress: 0,
            totalFiles: 0,
            processedFiles: 0
        };
        
        // Create debounced index function
        this.indexDebounced = debounce(
            async () => {
                await this.processModifiedFiles();
            },
            5000,  // Wait 5 seconds after last modification
            {
                leading: false,
                trailing: true
            }
        );
    }
    
    async search(query: string, maxResults?: number): Promise<SearchResult[]> {
        try {
            const response = await this.plugin.api.search(
                query,
                maxResults || this.settings.maxResults
            );
            return response.results;
        } catch (error) {
            console.error('Search error:', error);
            new Notice('Search failed. Please try again.');
            throw error;
        }
    }
    
    async indexVault(): Promise<void> {
        if (this.isIndexing) {
            new Notice('Indexing already in progress');
            return;
        }
        
        this.isIndexing = true;
        this.indexingProgress = {
            isIndexing: true,
            progress: 0,
            totalFiles: 0,
            processedFiles: 0
        };
        
        try {
            const files = this.app.vault.getFiles();
            const markdownFiles = files.filter(file => file.extension === 'md');
            
            this.indexingProgress.totalFiles = markdownFiles.length;
            
            // Process files in batches
            const batchSize = 10;
            for (let i = 0; i < markdownFiles.length; i += batchSize) {
                const batch = markdownFiles.slice(i, i + batchSize);
                await this.indexBatch(batch);
                
                this.indexingProgress.processedFiles += batch.length;
                this.indexingProgress.progress = 
                    this.indexingProgress.processedFiles / this.indexingProgress.totalFiles;
                    
                // Update status bar
                await this.plugin.statusBar.updateStatus();
            }
            
            new Notice('Vault indexing complete');
            
        } catch (error) {
            console.error('Indexing error:', error);
            new Notice('Indexing failed. Please try again.');
            throw error;
        } finally {
            this.isIndexing = false;
            this.indexingProgress.isIndexing = false;
            await this.plugin.statusBar.updateStatus();
        }
    }
    
    private async indexBatch(files: TFile[]): Promise<void> {
        const promises = files.map(async (file) => {
            try {
                const content = await this.app.vault.read(file);
                await this.plugin.api.indexDocument({
                    content,
                    metadata: {
                        path: file.path,
                        name: file.name,
                        size: file.stat.size,
                        created: file.stat.ctime,
                        modified: file.stat.mtime
                    }
                });
            } catch (error) {
                console.error(`Error indexing file ${file.path}:`, error);
            }
        });
        
        await Promise.all(promises);
    }
    
    async handleFileModify(file?: TFile): Promise<void> {
        if (!file || file.extension !== 'md') {
            return;
        }
        
        // Add to modified files set
        this.modifiedFiles.add(file.path);
        
        // Trigger debounced processing
        this.indexDebounced();
    }
    
    private async processModifiedFiles(): Promise<void> {
        if (this.modifiedFiles.size === 0) {
            return;
        }
        
        try {
            const files = Array.from(this.modifiedFiles)
                .map(path => this.app.vault.getAbstractFileByPath(path))
                .filter((file): file is TFile => file instanceof TFile);
                
            if (files.length === 0) {
                return;
            }
            
            // Update status
            new Notice(`Updating index for ${files.length} modified files...`);
            
            // Process files
            await this.indexBatch(files);
            
            // Clear processed files
            this.modifiedFiles.clear();
            
            new Notice('Index updated successfully');
            
        } catch (error) {
            console.error('Error processing modified files:', error);
            new Notice('Failed to update index for modified files');
        }
    }
    
    async runBenchmark(): Promise<void> {
        try {
            await this.plugin.api.runBenchmark();
        } catch (error) {
            console.error('Benchmark error:', error);
            new Notice('Failed to run benchmark');
            throw error;
        }
    }
    
    updateSettings(settings: SettingsData): void {
        this.settings = settings;
    }
    
    getIndexingStatus(): IndexingStatus {
        return this.indexingProgress;
    }
    
    async openSearch(): Promise<void> {
        await this.plugin.activateView();
    }
} 