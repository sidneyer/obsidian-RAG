import { App, PluginSettingTab, Setting } from 'obsidian';
import RAGPlugin from './main';
import { SettingsData } from './types';

export const DEFAULT_SETTINGS: SettingsData = {
    serverUrl: 'http://localhost:8000',
    apiKey: '',
    autoStartServer: true,
    embedModel: 'all-MiniLM-L6-v2',
    maxResults: 5,
    chunkSize: 500,
    chunkOverlap: 50,
    preserveMarkdown: true,
    useNeuralEngine: true,
    debugMode: false
};

export class RAGSettingTab extends PluginSettingTab {
    plugin: RAGPlugin;
    settings: SettingsData;

    constructor(app: App, plugin: RAGPlugin) {
        super(app, plugin);
        this.plugin = plugin;
        this.settings = DEFAULT_SETTINGS;
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
                .setValue(this.settings.serverUrl)
                .onChange(async (value) => {
                    this.settings.serverUrl = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('API Key')
            .setDesc('Optional API key for server authentication')
            .addText(text => text
                .setPlaceholder('Enter API key')
                .setValue(this.settings.apiKey)
                .onChange(async (value) => {
                    this.settings.apiKey = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Auto-start Server')
            .setDesc('Automatically start the server when plugin loads')
            .addToggle(toggle => toggle
                .setValue(this.settings.autoStartServer)
                .onChange(async (value) => {
                    this.settings.autoStartServer = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Embedding Model')
            .setDesc('Model to use for text embeddings')
            .addDropdown(dropdown => dropdown
                .addOption('all-MiniLM-L6-v2', 'MiniLM-L6')
                .addOption('all-mpnet-base-v2', 'MPNet Base')
                .setValue(this.settings.embedModel)
                .onChange(async (value) => {
                    this.settings.embedModel = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Max Results')
            .setDesc('Maximum number of search results to display')
            .addSlider(slider => slider
                .setLimits(1, 20, 1)
                .setValue(this.settings.maxResults)
                .setDynamicTooltip()
                .onChange(async (value) => {
                    this.settings.maxResults = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Chunk Size')
            .setDesc('Size of text chunks for processing')
            .addSlider(slider => slider
                .setLimits(100, 1000, 50)
                .setValue(this.settings.chunkSize)
                .setDynamicTooltip()
                .onChange(async (value) => {
                    this.settings.chunkSize = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Chunk Overlap')
            .setDesc('Overlap between consecutive chunks')
            .addSlider(slider => slider
                .setLimits(0, 200, 10)
                .setValue(this.settings.chunkOverlap)
                .setDynamicTooltip()
                .onChange(async (value) => {
                    this.settings.chunkOverlap = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Preserve Markdown')
            .setDesc('Keep markdown formatting in chunks')
            .addToggle(toggle => toggle
                .setValue(this.settings.preserveMarkdown)
                .onChange(async (value) => {
                    this.settings.preserveMarkdown = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Use Neural Engine')
            .setDesc('Use Apple Neural Engine when available')
            .addToggle(toggle => toggle
                .setValue(this.settings.useNeuralEngine)
                .onChange(async (value) => {
                    this.settings.useNeuralEngine = value;
                    await this.plugin.saveData(this.settings);
                }));

        new Setting(containerEl)
            .setName('Debug Mode')
            .setDesc('Enable debug logging')
            .addToggle(toggle => toggle
                .setValue(this.settings.debugMode)
                .onChange(async (value) => {
                    this.settings.debugMode = value;
                    await this.plugin.saveData(this.settings);
                }));
    }
} 