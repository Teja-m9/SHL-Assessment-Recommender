import { useEffect, useMemo, useState } from 'react';

const defaultApiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const starterPrompts = [
    'I need a cognitive assessment for a mid-level Java engineer',
    'Compare SHL Cognitive Ability Test and SHL Java Programming Test',
    'Add personality tests too for a senior engineering hire',
];

const formatTimestamp = (date) => new Date(date).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

function App() {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hi! Share the role, seniority, and test type, and I will recommend SHL assessments from the catalog.' },
    ]);
    const [input, setInput] = useState('');
    const [recommendations, setRecommendations] = useState([]);
    const [responseMeta, setResponseMeta] = useState({ reply_source: 'catalog', llm_model: null, state: 'clarifying' });
    const [status, setStatus] = useState('Checking service...');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
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

    const handleSend = async (text) => {
        const prompt = text.trim();
        if (!prompt || loading) return;

        const nextMessages = [...messages, { role: 'user', content: prompt }];
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

            setMessages([...nextMessages, { role: 'assistant', content: data.reply }]);
            setRecommendations(data.recommendations || []);
            setResponseMeta({
                reply_source: data.reply_source || 'catalog',
                llm_model: data.llm_model || null,
                state: data.state || (data.end_of_conversation ? 'recommending' : 'clarifying'),
            });
            setStatus(data.end_of_conversation ? 'Shortlist ready' : 'Need more context');
        } catch (error) {
            setMessages([...nextMessages, { role: 'assistant', content: error.message || 'Something went wrong.' }]);
            setStatus('Request failed');
        } finally {
            setLoading(false);
        }
    };

    const resetConversation = () => {
        setMessages([
            { role: 'assistant', content: 'Hi! Share the role, seniority, and test type, and I will recommend SHL assessments from the catalog.' },
        ]);
        setRecommendations([]);
        setResponseMeta({ reply_source: 'catalog', llm_model: null, state: 'clarifying' });
        setStatus('Chat cleared');
        setInput('');
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
            </aside>

            <main className="main-panel">
                <div className="chat-card">
                    <div className="chat-header">
                        <div className="chat-header-badge" />
                        <div className="chat-title-block">
                            <h3>SHL Assessment Assistant</h3>
                            <p>Every request sends the full conversation history</p>
                            <div className="meta-row">
                                <span className="meta-pill">state: {responseMeta.state}</span>
                                <span className="meta-pill">source: {responseMeta.reply_source}</span>
                                {responseMeta.llm_model ? <span className="meta-pill">model: {responseMeta.llm_model}</span> : null}
                            </div>
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
