export class Plugin {
    app: App;
    manifest: any;
    
    addRibbonIcon(icon: string, title: string, callback: () => any): HTMLElement {
        return document.createElement('div');
    }
    
    addStatusBarItem(): HTMLElement {
        return document.createElement('div');
    }
    
    registerView(type: string, viewCreator: any): void {}
    
    addCommand(command: any): void {}
    
    addSettingTab(tab: any): void {}
    
    loadData(): Promise<any> {
        return Promise.resolve({});
    }
    
    saveData(data: any): Promise<void> {
        return Promise.resolve();
    }
}

export class App {
    workspace: Workspace = new Workspace();
    vault: Vault = new Vault();
}

export class Workspace {
    getLeavesOfType(type: string): any[] {
        return [];
    }
    
    getActiveFile(): null {
        return null;
    }
    
    on(name: string, callback: (...args: any[]) => any): void {}
    
    getRightLeaf(active: boolean): any {
        return {};
    }
    
    getLeaf(vertical?: boolean): any {
        return {};
    }
    
    revealLeaf(leaf: any): void {}
}

export class Vault {
    getMarkdownFiles(): any[] {
        return [];
    }
    
    read(file: any): Promise<string> {
        return Promise.resolve('');
    }
    
    getAbstractFileByPath(path: string): any {
        return null;
    }
    
    on(name: string, callback: (...args: any[]) => any): void {}
}

export class Notice {
    constructor(message: string) {}
}

export class Modal {
    constructor(app: App) {}
    
    onOpen(): void {}
    onClose(): void {}
    open(): void {}
    close(): void {}
}

export class Setting {
    constructor(containerEl: HTMLElement) {}
    
    setName(name: string): this {
        return this;
    }
    
    setDesc(desc: string): this {
        return this;
    }
    
    addText(cb: (text: any) => any): this {
        return this;
    }
    
    addToggle(cb: (toggle: any) => any): this {
        return this;
    }
    
    addDropdown(cb: (dropdown: any) => any): this {
        return this;
    }
    
    addSlider(cb: (slider: any) => any): this {
        return this;
    }
    
    addButton(cb: (button: any) => any): this {
        return this;
    }
}

export function addIcon(iconId: string, svgContent: string): void {}

export class ItemView {
    constructor(leaf: any) {}
    
    getViewType(): string {
        return '';
    }
    
    onOpen(): Promise<void> {
        return Promise.resolve();
    }
    
    onClose(): Promise<void> {
        return Promise.resolve();
    }
} 