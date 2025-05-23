import {
    App,
    Plugin,
    PluginSettingTab,
    Setting,
    addIcon,
    WorkspaceLeaf
} from 'obsidian';
import { RAGApi } from './api/RAGApi';
import { DEFAULT_SETTINGS } from './settings';
import { RAGService } from './services/rag-service';
import { ServerManager } from './services/server-manager';
import { StatusBar } from './components/status-bar';
import { SearchView } from './views/search-view';
import { SettingsData } from './types';

addIcon('rag', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`);

export default class RAGPlugin extends Plugin {
    settings: SettingsData;
    api: RAGApi;
    ragService: RAGService;
    serverManager: ServerManager;
    statusBar: StatusBar;
    searchView: SearchView;

    async onload() {
        await this.loadSettings();

        this.api = new RAGApi(this.settings.serverUrl, this.settings.apiKey);
        this.ragService = new RAGService(this.settings, this.app, this);
        this.serverManager = new ServerManager(this);
        this.statusBar = new StatusBar(this);
        
        // Register views
        this.registerView(
            'rag-search',
            (leaf) => {
                this.searchView = new SearchView(leaf, this);
                return this.searchView;
            }
        );

        // Add settings tab
        this.addSettingTab(new PluginSettingTab(this.app, this));

        // Initialize server
        await this.serverManager.initialize();

        // Add commands
        this.addCommand({
            id: 'rag-search',
            name: 'Search with RAG',
            callback: () => this.ragService.openSearch()
        });

        this.addCommand({
            id: 'rag-index',
            name: 'Index current vault',
            callback: () => this.ragService.indexVault()
        });

        // Auto-start server if configured
        if (this.settings.autoStartServer) {
            await this.serverManager.startServer();
        }

        // Register event handlers
        this.registerEvent(
            this.app.workspace.on('file-open', async () => {
                await this.statusBar.updateStatus();
            })
        );

        this.registerEvent(
            this.app.vault.on('modify', async () => {
                await this.ragService.handleFileModify();
            })
        );
    }

    async onunload() {
        await this.serverManager.shutdown();
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
        this.ragService.updateSettings(this.settings);
        this.serverManager.updateSettings(this.settings);
    }

    public async activateView() {
        const { workspace } = this.app;
        
        let leaf = workspace.getLeavesOfType('rag-search')[0];
        if (!leaf) {
            leaf = workspace.getRightLeaf(false);
            if (leaf) {
                await leaf.setViewState({ type: 'rag-search' });
                workspace.revealLeaf(leaf);
            }
        } else {
            workspace.revealLeaf(leaf);
        }
    }
}

export class RAGSettingTab extends PluginSettingTab {
    plugin: RAGPlugin;

    constructor(app: App, plugin: RAGPlugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display(): void {
        const { containerEl } = this;
        containerEl.empty();

        containerEl.createEl('h2', { text: 'RAG Settings' });

        new Setting(containerEl)
            .setName('Server URL')
            .setDesc('URL of the RAG server')
            .addText(text => text
                .setPlaceholder('Enter server URL')
                .setValue(this.plugin.settings.serverUrl)
                .onChange(async (value) => {
                    this.plugin.settings.serverUrl = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('API Key')
            .setDesc('Optional API key for server authentication')
            .addText(text => text
                .setPlaceholder('Enter API key')
                .setValue(this.plugin.settings.apiKey)
                .onChange(async (value) => {
                    this.plugin.settings.apiKey = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Auto-start Server')
            .setDesc('Automatically start the server when plugin loads')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.autoStartServer)
                .onChange(async (value) => {
                    this.plugin.settings.autoStartServer = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Cache Enabled')
            .setDesc('Enable caching of embeddings')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.cacheEnabled)
                .onChange(async (value) => {
                    this.plugin.settings.cacheEnabled = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Cache Size')
            .setDesc('Maximum cache size in MB')
            .addSlider(slider => slider
                .setLimits(100, 1000, 100)
                .setValue(this.plugin.settings.maxCacheSize)
                .setDynamicTooltip()
                .onChange(async (value) => {
                    this.plugin.settings.maxCacheSize = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Embedding Model')
            .setDesc('Model to use for text embeddings')
            .addDropdown(dropdown => dropdown
                .addOption('all-MiniLM-L6-v2', 'MiniLM-L6')
                .addOption('all-mpnet-base-v2', 'MPNet Base')
                .setValue(this.plugin.settings.embedModel)
                .onChange(async (value) => {
                    this.plugin.settings.embedModel = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Max Results')
            .setDesc('Maximum number of search results to display')
            .addSlider(slider => slider
                .setLimits(1, 20, 1)
                .setValue(this.plugin.settings.maxResults)
                .setDynamicTooltip()
                .onChange(async (value) => {
                    this.plugin.settings.maxResults = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Use Neural Engine')
            .setDesc('Use Apple Neural Engine when available')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.useNeuralEngine)
                .onChange(async (value) => {
                    this.plugin.settings.useNeuralEngine = value;
                    await this.plugin.saveSettings();
                }));

        new Setting(containerEl)
            .setName('Debug Mode')
            .setDesc('Enable debug logging')
            .addToggle(toggle => toggle
                .setValue(this.plugin.settings.debugMode)
                .onChange(async (value) => {
                    this.plugin.settings.debugMode = value;
                    await this.plugin.saveSettings();
                }));
    }
} 