import { useEffect, useMemo, useState } from 'react';

const defaultApiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const conversationStorageKey = 'shl-assessment-compass-history';
const starterPrompts = [
    'I need a cognitive assessment for a mid-level Java engineer',
    'Compare SHL Cognitive Ability Test and SHL Java Programming Test',
    'Add personality tests too for a senior engineering hire',
];

const formatTimestamp = (date) => new Date(date).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
const createSessionId = () => (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
const createAssistantGreeting = () => ({
    role: 'assistant',
    content: 'Hi! Share the role, seniority, and test type, and I will recommend SHL assessments from the catalog.',
    createdAt: new Date().toISOString(),
});

const createMessage = (role, content) => ({
    role,
    content,
    createdAt: new Date().toISOString(),
});

const createHistoryTitle = (messages) => {
    const firstUserMessage = messages.find((message) => message.role === 'user')?.content;
    if (!firstUserMessage) return 'Untitled conversation';
    return firstUserMessage.length > 58 ? `${firstUserMessage.slice(0, 58)}...` : firstUserMessage;
};

function App() {
    const [messages, setMessages] = useState([createAssistantGreeting()]);
    const [input, setInput] = useState('');
    const [recommendations, setRecommendations] = useState([]);
    const [conversationHistory, setConversationHistory] = useState([]);
    const [activeConversationId, setActiveConversationId] = useState(createSessionId());
    const [status, setStatus] = useState('Checking service...');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        try {
            const saved = localStorage.getItem(conversationStorageKey);
            if (saved) {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed)) {
                    setConversationHistory(parsed);
                }
            }
        } catch {
            setConversationHistory([]);
        }

        const checkHealth = async () => {
            try {
                const response = await fetch(`${defaultApiUrl}/health`);
                setStatus(response.ok ? 'Service online' : 'Service responded with an error');
            } catch {
                setStatus('Service offline. Start the backend on port 8000.');
            }
        };

        checkHealth();
    }, []);

    useEffect(() => {
        localStorage.setItem(conversationStorageKey, JSON.stringify(conversationHistory));
    }, [conversationHistory]);

    useEffect(() => {
        const hasUserMessages = messages.some((message) => message.role === 'user');
        if (!hasUserMessages) return;

        const updatedAt = new Date().toISOString();
        const nextEntry = {
            id: activeConversationId,
            title: createHistoryTitle(messages),
            updatedAt,
            messages,
            recommendations,
        };

        setConversationHistory((previous) => {
            const withoutActive = previous.filter((entry) => entry.id !== activeConversationId);
            return [nextEntry, ...withoutActive].sort(
                (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
            );
        });
    }, [activeConversationId, messages, recommendations]);

    const handleSend = async (text) => {
        const prompt = text.trim();
        if (!prompt || loading) return;

        const nextMessages = [...messages, createMessage('user', prompt)];
        setMessages(nextMessages);
        setInput('');
        setLoading(true);
        setStatus('Thinking...');

        try {
            const response = await fetch(`${defaultApiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: nextMessages.map(({ role, content }) => ({ role, content })),
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            setMessages([...nextMessages, createMessage('assistant', data.reply)]);
            setRecommendations(data.recommendations || []);
            setStatus(data.end_of_conversation ? 'Shortlist ready' : 'Need more context');
        } catch (error) {
            setMessages([...nextMessages, createMessage('assistant', error.message || 'Something went wrong.')]);
            setStatus('Request failed');
        } finally {
            setLoading(false);
        }
    };

    const resetConversation = () => {
        setMessages([createAssistantGreeting()]);
        setRecommendations([]);
        setActiveConversationId(createSessionId());
        setStatus('Chat cleared');
        setInput('');
    };

    const loadConversation = (entry) => {
        setActiveConversationId(entry.id);
        setMessages(entry.messages || [createAssistantGreeting()]);
        setRecommendations(entry.recommendations || []);
        setStatus('Conversation loaded');
        setInput('');
    };

    const deleteConversation = (conversationId) => {
        setConversationHistory((previous) => {
            const remaining = previous.filter((entry) => entry.id !== conversationId);

            if (conversationId === activeConversationId) {
                if (remaining.length > 0) {
                    const nextActive = remaining[0];
                    setActiveConversationId(nextActive.id);
                    setMessages(nextActive.messages || [createAssistantGreeting()]);
                    setRecommendations(nextActive.recommendations || []);
                    setStatus('Conversation deleted');
                } else {
                    setActiveConversationId(createSessionId());
                    setMessages([createAssistantGreeting()]);
                    setRecommendations([]);
                    setStatus('Conversation deleted');
                }
                setInput('');
            }

            return remaining;
        });
    };

    const promptChips = useMemo(() => starterPrompts, []);

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <div className="brand-block">
                    <div className="brand-badge">SC</div>
                    <div>
                        <h2>SHL Assessment Compass</h2>
                        <p>Stateless assessment recommender</p>
                    </div>
                </div>
                <div className="sidebar-card">
                    <p className="sidebar-label">Status</p>
                    <div className="status-pill">{status}</div>
                </div>
                <div className="sidebar-card">
                    <p className="sidebar-label">Try these</p>
                    <div className="prompt-list">
                        {promptChips.map((prompt) => (
                            <button key={prompt} onClick={() => handleSend(prompt)}>
                                {prompt}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="sidebar-card">
                    <p className="sidebar-label">Conversation history</p>
                    {conversationHistory.length === 0 ? (
                        <p className="history-empty">No saved conversations yet.</p>
                    ) : (
                        <div className="history-list">
                            {conversationHistory.map((entry) => (
                                <div key={entry.id} className="history-item">
                                    <button
                                        className={`history-open ${entry.id === activeConversationId ? 'active' : ''}`}
                                        onClick={() => loadConversation(entry)}
                                    >
                                        <span className="history-title">{entry.title}</span>
                                        <span className="history-time">{formatTimestamp(entry.updatedAt)}</span>
                                    </button>
                                    <button
                                        className="history-delete"
                                        onClick={() => deleteConversation(entry.id)}
                                        aria-label={`Delete ${entry.title}`}
                                        title="Delete conversation"
                                    >
                                        Delete
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </aside>

            <main className="main-panel">
                <div className="chat-card">
                    <div className="chat-header">
                        <div className="chat-header-badge" />
                        <div className="chat-title-block">
                            <h3>SHL Assessment Assistant</h3>
                            <p>Every request sends the full conversation history</p>
                        </div>
                        <div className="chat-actions">
                            <button className="ghost-button primary" onClick={resetConversation}>Clear chat</button>
                        </div>
                    </div>
                    <div className="messages">
                        {messages.map((message, index) => (
                            <div key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
                                <div className="avatar">{message.role === 'assistant' ? 'A' : 'U'}</div>
                                <div className="bubble-content">
                                    <div className="bubble-meta">
                                        <span>{message.role === 'assistant' ? 'Assistant' : 'You'}</span>
                                        <span>{formatTimestamp(message.createdAt || new Date())}</span>
                                    </div>
                                    <div className="bubble-text">{message.content}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="composer">
                        <input
                            value={input}
                            onChange={(event) => setInput(event.target.value)}
                            onKeyDown={(event) => event.key === 'Enter' && handleSend(input)}
                            placeholder="Ask about a role, test type, or compare assessments"
                        />
                        <button onClick={() => handleSend(input)} disabled={loading}>
                            {loading ? 'Thinking...' : 'Send'}
                        </button>
                    </div>
                </div>

                <div className="recommendations-card">
                    <div className="recommendations-header">
                        <h3>Recommended assessments</h3>
                        <span>{recommendations.length} match{recommendations.length === 1 ? '' : 'es'}</span>
                    </div>
                    {recommendations.length === 0 ? (
                        <div className="empty-state">
                            <h4>Start with a role or assessment need</h4>
                            <p>Ask for a cognitive, personality, or skills test and I will narrow the shortlist for you.</p>
                        </div>
                    ) : (
                        recommendations.map((item) => (
                            <a key={item.name} href={item.url} target="_blank" rel="noreferrer" className="recommendation">
                                <div>
                                    <strong>{item.name}</strong>
                                    <p>{item.url}</p>
                                </div>
                                <div className="recommendation-meta">
                                    <span>{item.test_type}</span>
                                    {typeof item.confidence === 'number' ? (
                                        <small>confidence {Math.round(item.confidence * 100)}%</small>
                                    ) : null}
                                </div>
                            </a>
                        ))
                    )}
                </div>
            </main>
        </div>
    );
}

export default App;
