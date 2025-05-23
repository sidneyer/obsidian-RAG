import { SettingsData, ServerStatus, ServerManagerInterface } from '../types';
import { spawn, ChildProcess } from 'child_process';
import { platform } from 'os';
import { Notice } from 'obsidian';
import * as path from 'path';
import RAGPlugin from '../main';

export class ServerManager implements ServerManagerInterface {
    private plugin: RAGPlugin;
    private process: ChildProcess | null = null;
    private settings: SettingsData;
    private serverPath: string;
    private isRunning: boolean;
    
    constructor(plugin: RAGPlugin) {
        this.plugin = plugin;
        this.settings = plugin.settings;
        this.serverPath = this.getServerPath();
        this.isRunning = false;
    }
    
    private getServerPath(): string {
        const pluginDir = path.resolve(__dirname, '../../..');
        const serverDir = path.join(pluginDir, 'server');
        return path.join(serverDir, 'src', 'main.py');
    }
    
    async initialize(): Promise<void> {
        if (this.plugin.settings.autoStartServer) {
            await this.startServer();
        }
    }
    
    async startServer(): Promise<void> {
        if (this.isRunning) {
            return;
        }
        
        try {
            const env = {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                RAG_SERVER_PORT: new URL(this.settings.serverUrl).port,
                RAG_DEBUG: this.settings.debugMode ? '1' : '0',
                RAG_CACHE_ENABLED: this.settings.cacheEnabled ? '1' : '0',
                RAG_CACHE_SIZE_MB: this.settings.maxCacheSize.toString(),
                RAG_USE_NEURAL_ENGINE: this.settings.useNeuralEngine ? '1' : '0'
            };
            
            const pythonCommand = platform() === 'win32' ? 'python' : 'python3';
            this.process = spawn(pythonCommand, [this.serverPath], {
                env,
                stdio: ['ignore', 'pipe', 'pipe']
            });
            
            // Handle process events
            this.process.stdout?.on('data', (data) => {
                if (this.settings.debugMode) {
                    console.log(`[RAG Server]: ${data}`);
                }
            });
            
            this.process.stderr?.on('data', (data) => {
                console.error(`[RAG Server Error]: ${data}`);
                new Notice(`RAG Server Error: ${data}`);
            });
            
            this.process.on('error', (err) => {
                console.error('[RAG Server] Failed to start:', err);
                new Notice('Failed to start RAG server');
                this.process = null;
            });
            
            this.process.on('exit', (code) => {
                if (code !== 0) {
                    console.error(`[RAG Server] Exited with code ${code}`);
                    new Notice(`RAG server exited unexpectedly (code ${code})`);
                }
                this.process = null;
            });
            
            // Wait for server to start
            await this.waitForServer();
            
            this.isRunning = true;
            new Notice('Server started successfully');
        } catch (error) {
            console.error('Error starting server:', error);
            new Notice('Error starting server');
            this.process = null;
        }
    }
    
    async stopServer(): Promise<void> {
        if (!this.process) {
            return;
        }
        
        try {
            return new Promise((resolve) => {
                if (!this.process) {
                    resolve();
                    return;
                }
                
                this.process.once('exit', () => {
                    this.process = null;
                    this.isRunning = false;
                    resolve();
                });
                
                // Send SIGTERM signal
                this.process.kill();
                
                // Force kill after timeout
                setTimeout(() => {
                    if (this.process) {
                        this.process.kill('SIGKILL');
                        this.process = null;
                        this.isRunning = false;
                        resolve();
                    }
                }, 5000);
            });
            
            new Notice('Server stopped successfully');
        } catch (error) {
            console.error('Error stopping server:', error);
            new Notice('Error stopping server');
        }
    }
    
    async getStatus(): Promise<ServerStatus> {
        const url = this.settings.serverUrl;
        
        try {
            if (!this.process) {
                return {
                    isRunning: false,
                    url
                };
            }
            
            // Check if server is responding
            const response = await fetch(`${url}/health`);
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            
            return {
                isRunning: true,
                url,
                pid: this.process.pid
            };
            
        } catch (error) {
            return {
                isRunning: false,
                url,
                error: error.message
            };
        }
    }
    
    updateSettings(settings: SettingsData): void {
        this.settings = settings;
    }
    
    private async waitForServer(): Promise<void> {
        const maxAttempts = 30;
        const interval = 1000;
        
        for (let i = 0; i < maxAttempts; i++) {
            try {
                const status = await this.getStatus();
                if (status.isRunning) {
                    return;
                }
            } catch (error) {
                // Ignore errors while waiting
            }
            
            await new Promise(resolve => setTimeout(resolve, interval));
        }
        
        throw new Error('Server failed to start within timeout');
    }

    async shutdown(): Promise<void> {
        await this.stopServer();
    }

    isServerRunning(): boolean {
        return this.isRunning;
    }
} 