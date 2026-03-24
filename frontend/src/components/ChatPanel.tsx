"use client";

import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageSquare, Zap, User, Trash2, Loader2, AlertCircle, Send } from "lucide-react";

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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface ChatPanelProps {
    compact?: boolean;
    courseId?: string;
}

export default function ChatPanel({ compact = false, courseId }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

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

        const aiMsgId = (Date.now() + 1).toString();
        setMessages((prev) => [...prev, { id: aiMsgId, role: "ai", content: "" }]);

        try {
            const response = await fetch(`${API_URL}/api/chat/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: userMsg.content,
                    system_prompt:
                        "Tu es NovaFlow, un assistant personnel intelligent. Réponds de manière concise et utile en français.",
                    course_id: courseId,
                }),
            });

            if (!response.ok || !response.body) throw new Error("API Error");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === "token") {
                            const cleanedToken = data.content;
                            setMessages((prev) =>
                                prev.map((msg) =>
                                    msg.id === aiMsgId
                                        ? { ...msg, content: msg.content + cleanedToken }
                                        : msg
                                )
                            );
                        } else if (data.type === "done") {
                            setMessages((prev) =>
                                prev.map((msg) =>
                                    msg.id === aiMsgId ? { ...msg, content: data.response } : msg
                                )
                            );
                        }
                    } catch (err) {
                        console.error("SSE Parse Error:", err, line);
                    }
                }
            }
        } catch {
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === aiMsgId
                        ? {
                              ...msg,
                              content:
                                  "⚠️ I can't respond right now. Make sure the backend server (`python main.py`) and Ollama are running.",
                          }
                        : msg
                )
            );
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
                    <span className="nf-card__title">
                        <MessageSquare size={18} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--nf-accent)' }} />
                        Chat AI
                    </span>
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
                                {msg.role === "ai" ? <Zap size={14} color="white" /> : <User size={14} />}
                            </div>
                            <div className={`nf-chat__bubble nf-chat__bubble--${msg.role} ${msg.role === "ai" ? "nf-markdown" : ""}`} style={{
                                padding: "6px 10px", borderRadius: "10px",
                                fontSize: "11px", lineHeight: 1.4, maxWidth: "80%",
                                background: msg.role === "ai" ? "var(--nf-bg-card)" : "var(--nf-accent)",
                                color: msg.role === "user" ? "white" : "var(--nf-text)",
                                border: msg.role === "ai" ? "1px solid var(--nf-border)" : "none",
                                overflowY: "auto", maxHeight: "150px"
                            }}>
                                {msg.role === "ai" ? (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {msg.content.length > 300 ? msg.content.slice(0, 300) + "..." : msg.content}
                                    </ReactMarkdown>
                                ) : (
                                    msg.content
                                )}
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
                        {isLoading ? <Loader2 size={14} className="nf-spin" /> : <Send size={14} />}
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
                        <span className="nf-card__title">
                            <MessageSquare size={18} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--nf-accent)' }} />
                            Chat AI
                        </span>
                        <button onClick={clearHistory} className="nf-btn nf-btn--ghost"
                            style={{ padding: "2px 6px", fontSize: "11px", opacity: 0.6 }}
                            title="Clear history">
                            <Trash2 size={14} />
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
                                {msg.role === "ai" ? <Zap size={16} color="white" /> : <User size={16} />}
                            </div>
                            <div className={`nf-chat__bubble nf-chat__bubble--${msg.role} ${msg.role === "ai" ? "nf-markdown" : ""}`}>
                                {msg.role === "ai" ? (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {msg.content || (isLoading ? "▋" : "")}
                                    </ReactMarkdown>
                                ) : (
                                    msg.content
                                )}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
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
                        {isLoading ? <Loader2 size={18} className="nf-spin" /> : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}
