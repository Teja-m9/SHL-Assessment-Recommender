import { useEffect, useMemo, useState } from 'react';

const readStoredMessages = () => {
    if (typeof window === 'undefined') return [];
    const stored = window.localStorage.getItem('shl-chat-messages');
    if (!stored) return [];
    try {
        return JSON.parse(stored);
    } catch {
        return [];
    }
};

const readStoredSessionId = () => {
    if (typeof window === 'undefined') return '';
    return window.localStorage.getItem('shl-session-id') || '';
};

const defaultApiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const starterPrompts = [
    'I need a cognitive assessment for a mid-level Java engineer',
    'Compare SHL Cognitive Ability Test and SHL Java Programming Test',
    'Add personality tests too',
];

const formatTimestamp = (date) => {
    const now = new Date(date);
    return now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
};

const buildHistorySummary = (message) => {
    const text = message.content || '';
    return text.length > 38 ? `${text.slice(0, 35)}…` : text;
};

function App() {
    const [messages, setMessages] = useState(() => {
        const savedMessages = readStoredMessages();
        if (savedMessages.length > 0) {
            return savedMessages;
        }
        return [{ role: 'assistant', content: 'Hi! I can help you pick the most relevant SHL assessments for your hiring need.' }];
    });
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState(() => readStoredSessionId());
    const [recommendations, setRecommendations] = useState([]);
    const [status, setStatus] = useState('Checking service...');
    const [loading, setLoading] = useState(false);
    const [threadStore, setThreadStore] = useState(() => {
        if (typeof window === 'undefined') return {};
        const stored = window.localStorage.getItem('shl-thread-store');
        if (!stored) return {};
        try {
            return JSON.parse(stored);
        } catch {
            return {};
        }
    });
    const [history, setHistory] = useState(() => {
        if (typeof window === 'undefined') return [];
        const stored = window.localStorage.getItem('shl-thread-history');
        if (!stored) return [];
        try {
            return JSON.parse(stored);
        } catch {
            return [];
        }
    });

    useEffect(() => {
        if (messages.length > 1 && history.length === 0) {
            const latestUserMessage = [...messages].reverse().find((message) => message.role === 'user');
            if (latestUserMessage) {
                const summary = latestUserMessage.content.length > 44 ? `${latestUserMessage.content.slice(0, 41)}…` : latestUserMessage.content;
                setHistory([{ sessionId: sessionId || 'new-thread', title: summary, updatedAt: new Date().toISOString() }]);
            }
        }
    }, [messages, history.length, sessionId]);

    const updateThreadSnapshot = (threadId, nextMessages, titleOverride) => {
        const threadKey = threadId || 'new-thread';
        const titleSource = titleOverride || nextMessages.find((entry) => entry.role === 'user')?.content || 'New conversation';
        const summary = titleSource.length > 44 ? `${titleSource.slice(0, 41)}…` : titleSource;
        const timestamp = new Date().toISOString();

        setHistory((current) => {
            const base = current.filter((entry) => entry.sessionId !== threadKey);
            return [{ sessionId: threadKey, title: summary, updatedAt: timestamp }, ...base].slice(0, 8);
        });
        setThreadStore((current) => ({ ...current, [threadKey]: nextMessages }));
    };

    const resetThread = async (options = {}) => {
        const { keepSession = true, newSession = false } = options;
        if (typeof window !== 'undefined') {
            window.localStorage.removeItem('shl-chat-messages');
            if (!keepSession || newSession) {
                window.localStorage.removeItem('shl-session-id');
            }
        }

        if (!keepSession && sessionId) {
            try {
                await fetch(`${defaultApiUrl}/sessions/clear`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId }),
                });
            } catch {
                // Ignore API reset failures and continue with local reset.
            }
        }

        setMessages([{ role: 'assistant', content: 'Hi! I can help you pick the most relevant SHL assessments for your hiring need.' }]);
        setRecommendations([]);
        if (!newSession) {
            setHistory((current) => current.filter((entry) => entry.sessionId !== sessionId));
        }
        setStatus(newSession ? 'Started a new session' : 'Chat cleared');
        if (newSession) {
            setSessionId('');
        }
    };

    useEffect(() => {
        if (typeof window !== 'undefined' && sessionId) {
            window.localStorage.setItem('shl-session-id', sessionId);
        }
    }, [sessionId]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('shl-chat-messages', JSON.stringify(messages));
        }
    }, [messages]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('shl-thread-history', JSON.stringify(history));
        }
    }, [history]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('shl-thread-store', JSON.stringify(threadStore));
        }
    }, [threadStore]);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const response = await fetch(`${defaultApiUrl}/health`);
                if (response.ok) {
                    setStatus('Service online');
                } else {
                    setStatus('Service responded with an error');
                }
            } catch {
                setStatus('Service offline. Start the backend on port 8000.');
            }
        };

        checkHealth();
    }, []);

    const handleSend = async (text) => {
        const prompt = text.trim();
        if (!prompt) return;

        const activeThreadId = sessionId || 'new-thread';
        const nextMessages = [...messages, { role: 'user', content: prompt }];
        setMessages(nextMessages);
        updateThreadSnapshot(activeThreadId, nextMessages, prompt);
        setInput('');
        setLoading(true);
        setStatus('Thinking...');

        try {
            const response = await fetch(`${defaultApiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId || undefined,
                    messages: nextMessages.map(({ role, content }) => ({ role, content })),
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            const finalMessages = [...nextMessages, { role: 'assistant', content: data.reply }];
            if (data.session_id) {
                const activeSessionId = data.session_id;
                setSessionId(activeSessionId);
                updateThreadSnapshot(activeSessionId, finalMessages, prompt);
            }
            setMessages(finalMessages);
            setRecommendations(data.recommendations || []);
            setStatus('Recommendation ready');
        } catch (error) {
            setMessages([...nextMessages, { role: 'assistant', content: error.message || 'Something went wrong.' }]);
            setStatus('Request failed');
        } finally {
            setLoading(false);
        }
    };

    const loadThread = (entry) => {
        if (!entry?.sessionId) return;
        const storedMessages = threadStore[entry.sessionId] || [];
        if (storedMessages.length > 0) {
            setMessages(storedMessages);
            setSessionId(entry.sessionId);
            setRecommendations([]);
            if (typeof window !== 'undefined') {
                window.localStorage.setItem('shl-chat-messages', JSON.stringify(storedMessages));
                window.localStorage.setItem('shl-session-id', entry.sessionId);
            }
            setStatus(`Loaded thread: ${entry.title}`);
            return;
        }
        setMessages([{ role: 'assistant', content: 'Hi! I can help you pick the most relevant SHL assessments for your hiring need.' }]);
        setSessionId(entry.sessionId);
        setStatus('Loaded thread');
    };

    const promptChips = useMemo(() => starterPrompts, []);

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <div className="brand-block">
                    <div className="brand-badge">SC</div>
                    <div>
                        <h2>SHL Assessment Compass</h2>
                        <p>Assessment guidance assistant</p>
                    </div>
                </div>
                <div className="sidebar-card">
                    <p className="sidebar-label">Status</p>
                    <div className="status-pill">{status}</div>
                </div>
                <div className="sidebar-card">
                    <p className="sidebar-label">Recent threads</p>
                    <div className="history-list">
                        {history.length === 0 ? (
                            <div className="history-empty">No recent sessions yet.</div>
                        ) : (
                            history.map((entry) => (
                                <button key={entry.sessionId || entry.title} className="history-item" onClick={() => loadThread(entry)}>
                                    <span className="history-title">{entry.title}</span>
                                    <span className="history-time">{formatTimestamp(entry.updatedAt)}</span>
                                </button>
                            ))
                        )}
                    </div>
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
            </aside>

            <main className="main-panel">
                <div className="chat-card">
                    <div className="chat-header">
                        <div className="chat-header-badge" />
                        <div className="chat-title-block">
                            <h3>SHL Assessment Assistant</h3>
                            <p>Fast, grounded recommendations for hiring teams</p>
                        </div>
                        <div className="chat-actions">
                            <button className="ghost-button" onClick={() => resetThread({ keepSession: true })}>Clear chat</button>
                            <button className="ghost-button primary" onClick={() => resetThread({ keepSession: false, newSession: true })}>New session</button>
                        </div>
                    </div>
                    <div className="messages">
                        {messages.map((message, index) => (
                            <div key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
                                <div className="avatar">{message.role === 'assistant' ? 'A' : 'U'}</div>
                                <div className="bubble-content">
                                    <div className="bubble-meta">
                                        <span>{message.role === 'assistant' ? 'Assistant' : 'You'}</span>
                                        <span>{formatTimestamp(new Date())}</span>
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
                        <span>{recommendations.length} match</span>
                    </div>
                    {recommendations.length === 0 ? (
                        <div className="empty-state">
                            <h4>Start with a role or assessment need</h4>
                            <p>Ask for a cognitive, personality, or skills test and I’ll narrow the shortlist for you.</p>
                        </div>
                    ) : (
                        recommendations.map((item) => (
                            <a key={item.name} href={item.url} target="_blank" rel="noreferrer" className="recommendation">
                                <div>
                                    <strong>{item.name}</strong>
                                    <p>{item.description}</p>
                                </div>
                                <span>{item.test_type}</span>
                            </a>
                        ))
                    )}
                </div>
            </main>
        </div>
    );
}

export default App;
