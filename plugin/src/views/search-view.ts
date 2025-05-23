import { ItemView, WorkspaceLeaf, Notice } from 'obsidian';
import { SearchResult } from '../types';
import RAGPlugin from '../main';
import { TFile, TAbstractFile } from 'obsidian';

export class SearchView extends ItemView {
    private plugin: RAGPlugin;
    private searchInput: HTMLInputElement;
    private resultsContainer: HTMLDivElement;
    private loadingIndicator: HTMLDivElement;
    
    constructor(leaf: WorkspaceLeaf, plugin: RAGPlugin) {
        super(leaf);
        this.plugin = plugin;
    }
    
    getViewType(): string {
        return 'rag-search';
    }
    
    getDisplayText(): string {
        return 'RAG Search';
    }
    
    async onOpen(): Promise<void> {
        const container = this.containerEl.children[1];
        container.empty();
        
        // Create search interface
        const searchContainer = container.createDiv('rag-search-container');
        
        // Search input
        const inputContainer = searchContainer.createDiv('rag-search-input-container');
        this.searchInput = inputContainer.createEl('input', {
            type: 'text',
            placeholder: 'Search your vault...'
        });
        
        const searchButton = inputContainer.createEl('button', {
            text: 'Search'
        });
        
        // Loading indicator
        this.loadingIndicator = searchContainer.createDiv('rag-loading-indicator');
        this.loadingIndicator.setText('Searching...');
        this.loadingIndicator.hide();
        
        // Results container
        this.resultsContainer = searchContainer.createDiv('rag-results-container');
        
        // Event listeners
        this.searchInput.addEventListener('keypress', async (e) => {
            if (e.key === 'Enter') {
                await this.performSearch();
            }
        });
        
        searchButton.addEventListener('click', async () => {
            await this.performSearch();
        });
        
        // Add styles
        this.addStyles();
    }
    
    private async performSearch(): Promise<void> {
        const query = this.searchInput.value.trim();
        if (!query) {
            return;
        }
        
        try {
            this.showLoading();
            this.resultsContainer.empty();
            
            const results = await this.plugin.ragService.search(
                query,
                this.plugin.settings.maxResults
            );
            
            this.displayResults(results);
            
        } catch (error) {
            console.error('Search error:', error);
            new Notice('Search failed. Please try again.');
            
        } finally {
            this.hideLoading();
        }
    }
    
    private displayResults(results: SearchResult[]): void {
        if (!results.length) {
            this.resultsContainer.createDiv('rag-no-results')
                .setText('No results found');
            return;
        }
        
        results.forEach((result) => {
            const resultEl = this.resultsContainer.createDiv('rag-result');
            
            // Result header
            const header = resultEl.createDiv('rag-result-header');
            const title = header.createDiv('rag-result-title');
            title.setText(result.metadata.name || result.source);
            
            const score = header.createDiv('rag-result-score');
            score.setText(`${Math.round(result.similarity * 100)}% match`);
            
            // Result content
            const content = resultEl.createDiv('rag-result-content');
            content.setText(result.content);
            
            // Click handler
            resultEl.addEventListener('click', () => {
                this.openResult(result);
            });
        });
    }
    
    private async openResult(result: SearchResult): Promise<void> {
        try {
            const file = this.app.vault.getAbstractFileByPath(result.source);
            if (file) {
                await this.openFile(file);
            }
        } catch (error) {
            console.error('Error opening file:', error);
            new Notice('Could not open file');
        }
    }
    
    private async openFile(file: TAbstractFile): Promise<void> {
        if (file instanceof TFile) {
            await this.app.workspace.getLeaf().openFile(file);
        }
    }
    
    private showLoading(): void {
        this.loadingIndicator.show();
        this.searchInput.disabled = true;
    }
    
    private hideLoading(): void {
        this.loadingIndicator.hide();
        this.searchInput.disabled = false;
        this.searchInput.focus();
    }
    
    private addStyles(): void {
        // Add CSS classes
        this.containerEl.addClass('rag-view');
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .rag-search-container {
                padding: 16px;
            }
            
            .rag-search-input-container {
                display: flex;
                gap: 8px;
                margin-bottom: 16px;
            }
            
            .rag-search-input-container input {
                flex: 1;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid var(--background-modifier-border);
            }
            
            .rag-search-input-container button {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: var(--interactive-accent);
                color: var(--text-on-accent);
                border: none;
                cursor: pointer;
            }
            
            .rag-loading-indicator {
                text-align: center;
                padding: 16px;
                color: var(--text-muted);
            }
            
            .rag-result {
                padding: 16px;
                margin-bottom: 16px;
                border-radius: 4px;
                background-color: var(--background-primary);
                border: 1px solid var(--background-modifier-border);
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .rag-result:hover {
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            
            .rag-result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            
            .rag-result-title {
                font-weight: bold;
                color: var(--text-normal);
            }
            
            .rag-result-score {
                font-size: 0.8em;
                color: var(--text-muted);
            }
            
            .rag-result-content {
                color: var(--text-muted);
                font-size: 0.9em;
                line-height: 1.5;
                max-height: 100px;
                overflow: hidden;
                position: relative;
            }
            
            .rag-result-content::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 40px;
                background: linear-gradient(
                    transparent,
                    var(--background-primary)
                );
            }
            
            .rag-no-results {
                text-align: center;
                padding: 32px;
                color: var(--text-muted);
            }
        `;
        
        document.head.appendChild(style);
    }
} 