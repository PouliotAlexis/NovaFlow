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
            "Salut ! Je suis NovaFlow, ton assistant personnel. Je peux analyser tes documents, gérer tes tâches et organiser ton emploi du temps. Que veux-tu faire ?",
    },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPanel() {
    const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    // Charger l'historique au montage
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
                console.error("Erreur lors du chargement de l'historique:", error);
            }
        };
        fetchHistory();
    }, []);

    const clearHistory = async () => {
        if (!confirm("Effacer tout l'historique de chat ?")) return;

        try {
            const response = await fetch(`${API_URL}/api/chat/history`, { method: "DELETE" });
            if (response.ok) {
                setMessages(INITIAL_MESSAGES);
            }
        } catch (error) {
            console.error("Erreur lors de la suppression de l'historique:", error);
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

            if (!response.ok) throw new Error("Erreur API");

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
                    "⚠️ Je ne peux pas répondre pour le moment. Vérifie que le serveur backend est en marche (`python main.py`) et qu'Ollama est actif.",
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

    return (
        <div className="nf-card nf-animate-in" style={{ display: "flex", flexDirection: "column", minHeight: "400px" }}>
            <div className="nf-card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="nf-card__title">💬 Chat AI</span>
                    <button
                        onClick={clearHistory}
                        className="nf-btn nf-btn--ghost"
                        style={{ padding: '2px 6px', fontSize: '0.8rem', opacity: 0.6 }}
                        title="Effacer l'historique"
                    >
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
                    <div
                        key={msg.id}
                        className={`nf-chat__message nf-chat__message--${msg.role}`}
                    >
                        <div className={`nf-chat__avatar nf-chat__avatar--${msg.role}`}>
                            {msg.role === "ai" ? "⚡" : "👤"}
                        </div>
                        <div className={`nf-chat__bubble nf-chat__bubble--${msg.role} ${msg.role === 'ai' ? 'nf-markdown' : ''}`}>
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
                            En train de réfléchir...
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="nf-chat__input-area">
                <input
                    className="nf-chat__input"
                    placeholder="Pose une question à NovaFlow..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                />
                <button
                    className="nf-btn nf-btn--primary"
                    onClick={sendMessage}
                    disabled={isLoading || !input.trim()}
                >
                    {isLoading ? "⏳" : "Envoyer"}
                </button>
            </div>
        </div>
    );
}
