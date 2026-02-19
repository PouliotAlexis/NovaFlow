"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
    id: string;
    role: "user" | "ai";
    content: string;
}

const INITIAL_MESSAGES: Message[] = [
    {
        id: "1",
        role: "ai",
        content:
            "Hi! I'm NovaFlow, your personal assistant. I can analyze documents, manage tasks, and organize your schedule. What would you like to do?",
    },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatPanelProps {
    compact?: boolean;
}

export default function ChatPanel({ compact = false }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    React.useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await fetch(`${API_URL}/api/chat/history`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.history && data.history.length > 0) {
                        setMessages(data.history);
                    }
                }
            } catch (error) {
                console.error("Error loading chat history:", error);
            }
        };
        fetchHistory();
    }, []);

    const clearHistory = async () => {
        if (!confirm("Clear all chat history?")) return;
        try {
            const response = await fetch(`${API_URL}/api/chat/history`, { method: "DELETE" });
            if (response.ok) {
                setMessages(INITIAL_MESSAGES);
            }
        } catch (error) {
            console.error("Error clearing history:", error);
        }
    };

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setIsLoading(true);

        try {
            const response = await fetch(`${API_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMsg.content,
                    system_prompt:
                        "Tu es NovaFlow, un assistant personnel intelligent. Réponds de manière concise et utile en français.",
                }),
            });

            if (!response.ok) throw new Error("API Error");

            const data = await response.json();

            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "ai",
                content: data.response,
            };

            setMessages((prev) => [...prev, aiMsg]);
        } catch {
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "ai",
                content:
                    "⚠️ I can't respond right now. Make sure the backend server (`python main.py`) and Ollama are running.",
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Dashboard compact mode
    if (compact) {
        const recentMessages = messages.slice(-4);

        return (
            <div className="nf-card nf-card--glow nf-animate-in" style={{ display: "flex", flexDirection: "column" }}>
                <div className="nf-card__header">
                    <span className="nf-card__title">💬 Chat AI</span>
                    <div className="nf-ai-mode nf-ai-mode--local" style={{ fontSize: "10px" }}>
                        <span className="nf-ai-mode__dot" />
                        Local
                    </div>
                </div>

                {/* Recent messages */}
                <div style={{ flex: 1, overflow: "hidden", marginBottom: "12px" }}>
                    {recentMessages.map((msg) => (
                        <div key={msg.id} style={{
                            display: "flex", gap: "8px", marginBottom: "8px",
                            flexDirection: msg.role === "user" ? "row-reverse" : "row",
                        }}>
                            <div style={{
                                fontSize: "14px", flexShrink: 0,
                                width: "24px", height: "24px", borderRadius: "50%",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                background: msg.role === "ai" ? "var(--nf-accent-gradient)" : "var(--nf-bg-tertiary)",
                            }}>
                                {msg.role === "ai" ? "⚡" : "👤"}
                            </div>
                            <div style={{
                                padding: "6px 10px", borderRadius: "10px",
                                fontSize: "11px", lineHeight: 1.4, maxWidth: "80%",
                                background: msg.role === "ai" ? "var(--nf-bg-card)" : "var(--nf-accent)",
                                color: msg.role === "user" ? "white" : "var(--nf-text)",
                                border: msg.role === "ai" ? "1px solid var(--nf-border)" : "none",
                            }}>
                                {msg.content.length > 100 ? msg.content.slice(0, 100) + "..." : msg.content}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Compact input */}
                <div style={{ display: "flex", gap: "8px" }}>
                    <input
                        className="nf-input"
                        placeholder="Ask NovaFlow..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        style={{ fontSize: "12px", padding: "6px 10px" }}
                    />
                    <button className="nf-btn nf-btn--primary" onClick={sendMessage}
                        disabled={isLoading || !input.trim()}
                        style={{ fontSize: "11px", padding: "6px 10px" }}>
                        {isLoading ? "⏳" : "→"}
                    </button>
                </div>
            </div>
        );
    }

    // Full page mode
    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div className="nf-page-header">
                <h1 className="nf-page-header__title">Chat AI</h1>
                <p className="nf-page-header__subtitle">Ask NovaFlow anything</p>
            </div>

            <div className="nf-card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: "400px" }}>
                <div className="nf-card__header">
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span className="nf-card__title">💬 Chat AI</span>
                        <button onClick={clearHistory} className="nf-btn nf-btn--ghost"
                            style={{ padding: "2px 6px", fontSize: "11px", opacity: 0.6 }}
                            title="Clear history">
                            🗑️
                        </button>
                    </div>
                    <div className="nf-ai-mode nf-ai-mode--local">
                        <span className="nf-ai-mode__dot" />
                        Local (Ollama)
                    </div>
                </div>

                {/* Messages */}
                <div className="nf-chat__messages" style={{ flex: 1 }}>
                    {messages.map((msg) => (
                        <div key={msg.id}
                            className={`nf-chat__message nf-chat__message--${msg.role}`}>
                            <div className={`nf-chat__avatar nf-chat__avatar--${msg.role}`}>
                                {msg.role === "ai" ? "⚡" : "👤"}
                            </div>
                            <div className={`nf-chat__bubble nf-chat__bubble--${msg.role} ${msg.role === "ai" ? "nf-markdown" : ""}`}>
                                {msg.role === "ai" ? (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {msg.content}
                                    </ReactMarkdown>
                                ) : (
                                    msg.content
                                )}
                            </div>
                        </div>
                    ))}

                    {isLoading && (
                        <div className="nf-chat__message nf-chat__message--ai">
                            <div className="nf-chat__avatar nf-chat__avatar--ai">⚡</div>
                            <div className="nf-chat__bubble nf-chat__bubble--ai" style={{ opacity: 0.7 }}>
                                Thinking...
                            </div>
                        </div>
                    )}
                </div>

                {/* Input */}
                <div className="nf-chat__input-area">
                    <input
                        className="nf-chat__input"
                        placeholder="Ask NovaFlow anything..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                    />
                    <button className="nf-btn nf-btn--primary" onClick={sendMessage}
                        disabled={isLoading || !input.trim()}>
                        {isLoading ? "⏳" : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}
