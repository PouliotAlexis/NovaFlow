"use client";

import React, { useState, useEffect } from "react";
import { useChat, Message } from "ai/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Send, BookOpen, Paperclip, AlertTriangle, Loader2 } from "lucide-react";
import Link from "next/link";

interface CourseFile {
  name: string;
  ingested: boolean;
  size: number;
  path: string;
}

export default function CourseChatPage({ params }: { params: Promise<{ courseId: string }> }) {
  const { courseId } = React.use(params);
  const [files, setFiles] = useState<CourseFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "http://localhost:8000/api/v2/chat",
    body: { course_id: courseId, use_rag: true },
  });

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v2/moodle/courses/${courseId}/files`);
        if (res.ok) {
          const data = await res.json();
          setFiles(data);
        }
      } catch (err) {
        console.error("Erreur lors de la récupération des fichiers:", err);
      } finally {
        setLoadingFiles(false);
      }
    };
    fetchFiles();
  }, [courseId]);

  return (
    <div className="nf-layout">
      <div className="nf-sidebar">
        <Link href="/?view=courses" className="nf-sidebar__item">
          <ArrowLeft size={20} />
          Retour aux cours
        </Link>
        
        <div className="nf-sidebar__section">
          <h4 className="nf-sidebar__label">Documents du cours</h4>
          <div className="nf-sidebar__list" style={{ maxHeight: "calc(100vh - 200px)", overflowY: "auto" }}>
            {loadingFiles ? (
              <div className="nf-sidebar__item" style={{ opacity: 0.5 }}>
                <Loader2 size={16} className="nf-animate-spin" />
                Chargement...
              </div>
            ) : files.length === 0 ? (
              <div className="nf-sidebar__item" style={{ opacity: 0.5, fontSize: "12px" }}>
                Aucun document PDF trouvé.
              </div>
            ) : (
              files.map((file, idx) => (
                <div 
                  key={idx} 
                  className={`nf-sidebar__item ${idx === 0 ? 'nf-sidebar__item--active' : ''}`}
                  title={!file.ingested ? "Ce document n'a pas encore été analysé par l'IA et ne peut pas servir de contexte." : file.name}
                >
                  <BookOpen size={16} style={{ minWidth: "16px" }} />
                  <span style={{ 
                    overflow: "hidden", 
                    textOverflow: "ellipsis", 
                    whiteSpace: "nowrap",
                    flex: 1
                  }}>
                    {file.name}
                  </span>
                  {!file.ingested && (
                    <AlertTriangle 
                      size={14} 
                      color="var(--nf-warning)" 
                      style={{ minWidth: "14px" }} 
                    />
                  )}
                </div>
              ))
            )}
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
              <div className={`nf-chat__message-content ${m.role === 'assistant' ? 'nf-markdown' : ''}`}>
                {m.role === 'assistant' ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                ) : (
                  m.content
                )}
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
