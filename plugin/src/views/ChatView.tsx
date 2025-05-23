import { ItemView, WorkspaceLeaf } from 'obsidian';
import * as React from 'react';
import * as ReactDOM from 'react-dom';
import { ChatResponse } from '../api/RAGApi';
import RAGPlugin from '../main';

export const VIEW_TYPE_CHAT = 'rag-chat-view';

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    sources?: ChatResponse['sources'];
}

interface ChatViewProps {
    plugin: RAGPlugin;
}

interface ChatViewState {
    messages: ChatMessage[];
    input: string;
    loading: boolean;
    error?: string;
    selectedVault?: string;
}

class ChatViewComponent extends React.Component<ChatViewProps, ChatViewState> {
    constructor(props: ChatViewProps) {
        super(props);
        this.state = {
            messages: [],
            input: '',
            loading: false
        };
    }

    async componentDidMount() {
        // Load available vaults
        try {
            const vaults = await this.props.plugin.api.listVaults();
            if (vaults.length > 0) {
                this.setState({
                    selectedVault: this.props.plugin.settings.defaultVault || vaults[0].name
                });
            }
        } catch (error) {
            console.error('Error loading vaults:', error);
        }
    }

    handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        this.setState({ input: e.target.value });
    };

    handleSubmit = async () => {
        const { input, selectedVault, messages } = this.state;
        if (!input.trim()) return;

        // Add user message
        const newMessages = [
            ...messages,
            { role: 'user', content: input } as ChatMessage
        ];
        this.setState({ messages: newMessages, loading: true, error: undefined });

        try {
            // Get response from RAG server
            const response = await this.props.plugin.api.chat(input, selectedVault);

            // Add assistant message
            this.setState(state => ({
                messages: [
                    ...state.messages,
                    {
                        role: 'assistant',
                        content: response.response,
                        sources: response.sources
                    } as ChatMessage
                ],
                input: '',
                loading: false
            }));
        } catch (error) {
            console.error('Chat error:', error);
            this.setState({
                loading: false,
                error: 'Failed to get response from server'
            });
        }
    };

    handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSubmit();
        }
    };

    render() {
        const { messages, input, loading, error } = this.state;

        return (
            <div className="rag-chat-container">
                <div className="rag-messages">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`rag-message rag-message-${msg.role}`}>
                            <div className="rag-message-content">
                                {msg.content}
                            </div>
                            {msg.sources && (
                                <div className="rag-message-sources">
                                    <h4>Sources:</h4>
                                    <ul>
                                        {msg.sources.map((source, sourceIdx) => (
                                            <li key={sourceIdx}>
                                                <a
                                                    href="#"
                                                    onClick={(e) => {
                                                        e.preventDefault();
                                                        // TODO: Open source file
                                                    }}
                                                >
                                                    {source.file}
                                                </a>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ))}
                    {loading && (
                        <div className="rag-message rag-message-loading">
                            Thinking...
                        </div>
                    )}
                    {error && (
                        <div className="rag-message rag-message-error">
                            {error}
                        </div>
                    )}
                </div>
                <div className="rag-input">
                    <textarea
                        value={input}
                        onChange={this.handleInputChange}
                        onKeyPress={this.handleKeyPress}
                        placeholder="Ask a question..."
                        rows={3}
                    />
                    <button
                        onClick={this.handleSubmit}
                        disabled={loading || !input.trim()}
                    >
                        Send
                    </button>
                </div>
            </div>
        );
    }
}

export class ChatView extends ItemView {
    plugin: RAGPlugin;

    constructor(leaf: WorkspaceLeaf, plugin: RAGPlugin) {
        super(leaf);
        this.plugin = plugin;
    }

    getViewType(): string {
        return VIEW_TYPE_CHAT;
    }

    getDisplayText(): string {
        return 'Chat with Vault';
    }

    async onOpen(): Promise<void> {
        ReactDOM.render(
            <ChatViewComponent plugin={this.plugin} />,
            this.containerEl.children[1]
        );
    }

    async onClose(): Promise<void> {
        ReactDOM.unmountComponentAtNode(this.containerEl.children[1]);
    }
} 