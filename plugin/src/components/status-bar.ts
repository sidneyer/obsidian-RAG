import { Modal } from 'obsidian';
import RAGPlugin from '../main';
import { ServerStatus, IndexingStatus } from '../types';

export class StatusBar {
    private plugin: RAGPlugin;
    private statusBarEl: HTMLElement;
    private serverStatusEl: HTMLElement;
    private indexingStatusEl: HTMLElement;

    constructor(plugin: RAGPlugin) {
        this.plugin = plugin;
        this.statusBarEl = plugin.addStatusBarItem();
        this.serverStatusEl = this.statusBarEl.createDiv();
        this.indexingStatusEl = this.statusBarEl.createDiv();
        this.updateStatus();
    }

    async updateStatus(): Promise<void> {
        const serverStatus = await this.plugin.serverManager.getStatus();
        const indexingStatus = this.plugin.ragService.getIndexingStatus();
        
        this.updateServerStatus(serverStatus);
        this.updateIndexingStatus(indexingStatus);
    }

    private updateServerStatus(status: ServerStatus): void {
        this.serverStatusEl.empty();
        
        if (status.isRunning) {
            this.serverStatusEl.setText('RAG Server: Running');
            this.serverStatusEl.addClass('rag-status-running');
            this.serverStatusEl.removeClass('rag-status-stopped');
        } else {
            this.serverStatusEl.setText('RAG Server: Stopped');
            this.serverStatusEl.addClass('rag-status-stopped');
            this.serverStatusEl.removeClass('rag-status-running');
        }

        // Add click handler for server control
        this.serverStatusEl.addEventListener('click', async () => {
            if (status.isRunning) {
                await this.plugin.serverManager.stopServer();
            } else {
                await this.plugin.serverManager.startServer();
            }
            await this.updateStatus();
        });
    }

    private updateIndexingStatus(status: IndexingStatus): void {
        this.indexingStatusEl.empty();
        
        if (status.isIndexing) {
            const progress = Math.round((status.processedFiles / status.totalFiles) * 100);
            this.indexingStatusEl.setText(`Indexing: ${progress}%`);
            this.indexingStatusEl.addClass('rag-status-indexing');
        } else {
            this.indexingStatusEl.setText('Index: Ready');
            this.indexingStatusEl.removeClass('rag-status-indexing');
        }

        // Add click handler for reindexing
        this.indexingStatusEl.addEventListener('click', async () => {
            if (!status.isIndexing) {
                await this.plugin.ragService.indexVault();
                await this.updateStatus();
            }
        });
    }

    private showStatusModal(serverStatus: ServerStatus, indexingStatus: IndexingStatus): void {
        const modal = new Modal(this.plugin.app);
        modal.titleEl.setText('RAG Status');
        
        const contentEl = modal.contentEl;
        contentEl.empty();
        
        // Server status
        const serverSection = contentEl.createDiv();
        serverSection.createEl('h3', { text: 'Server Status' });
        serverSection.createEl('p', { text: `Status: ${serverStatus.isRunning ? 'Running' : 'Stopped'}` });
        if (serverStatus.error) {
            serverSection.createEl('p', { text: `Error: ${serverStatus.error}`, cls: 'error' });
        }
        
        // Indexing status
        const indexSection = contentEl.createDiv();
        indexSection.createEl('h3', { text: 'Indexing Status' });
        if (indexingStatus.isIndexing) {
            const progress = Math.round((indexingStatus.processedFiles / indexingStatus.totalFiles) * 100);
            indexSection.createEl('p', { text: `Progress: ${progress}%` });
            indexSection.createEl('p', { text: `Files: ${indexingStatus.processedFiles}/${indexingStatus.totalFiles}` });
        } else {
            indexSection.createEl('p', { text: 'Not currently indexing' });
        }
        
        modal.open();
    }
    
    onunload(): void {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }

    setDefaultStatus(): void {
        this.statusBarEl.empty();
        this.statusBarEl.createEl('span', {
            text: 'RAG: Ready',
            cls: 'rag-status'
        });
    }

    setStatus(text: string): void {
        this.statusBarEl.empty();
        this.statusBarEl.createEl('span', {
            text: `RAG: ${text}`,
            cls: 'rag-status'
        });
    }

    setError(text: string): void {
        this.statusBarEl.empty();
        this.statusBarEl.createEl('span', {
            text: `RAG: Error - ${text}`,
            cls: 'rag-status rag-error'
        });
    }
} 