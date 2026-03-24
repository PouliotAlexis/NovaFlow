"use client";

import React, { useState } from "react";
import { useChat, Message } from "ai/react";
import { ArrowLeft, Send, BookOpen, Paperclip } from "lucide-react";
import Link from "next/link";

export default function CourseChatPage({ params }: { params: Promise<{ courseId: string }> }) {
  const { courseId } = React.use(params);
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "http://localhost:8000/api/v2/chat", // Point vers le backend FastAPI V2
    body: { course_id: courseId, use_rag: true },
  });

  return (
    <div className="nf-layout">
      <div className="nf-sidebar">
        <Link href="/?view=courses" className="nf-sidebar__item">
          <ArrowLeft size={20} />
          Retour aux cours
        </Link>
        
        <div className="nf-sidebar__section">
          <h4 className="nf-sidebar__label">Documents du cours</h4>
          <div className="nf-sidebar__list">
            <div className="nf-sidebar__item nf-sidebar__item--active">
              <BookOpen size={16} />
              Syllabus.pdf
            </div>
            {/* Simulation de liste de fichiers */}
          </div>
        </div>
      </div>

      <main className="nf-main nf-chat-layout">
        <header className="nf-header">
          <h1 className="nf-header__title">Second Brain : Cours {courseId}</h1>
        </header>

        <div className="nf-chat__messages">
          {messages.length === 0 && (
            <div className="nf-chat__welcome">
              <div className="nf-chat__welcome-icon">🧠</div>
              <h2>Comment puis-je vous aider pour ce cours ?</h2>
              <p>Je peux répondre à vos questions en me basant sur les PDF synchronisés de Moodle.</p>
            </div>
          )}
          {messages.map((m: Message) => (
            <div key={m.id} className={`nf-chat__message nf-chat__message--${m.role}`}>
              <div className="nf-chat__message-content">
                {m.content}
              </div>
            </div>
          ))}
        </div>

        <form className="nf-chat__input-container" onSubmit={handleSubmit}>
          <button type="button" className="nf-chat__input-action">
            <Paperclip size={20} />
          </button>
          <input
            className="nf-chat__input"
            value={input}
            placeholder="Posez une question sur le cours..."
            onChange={handleInputChange}
          />
          <button 
            type="submit" 
            className="nf-chat__send-button"
            disabled={isLoading || !input.trim()}
          >
            <Send size={20} />
          </button>
        </form>
      </main>
    </div>
  );
}
