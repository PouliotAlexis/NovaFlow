"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useChat, Message } from "ai/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Send, BookOpen, Paperclip, AlertTriangle, Loader2, ExternalLink, CheckSquare, Square } from "lucide-react";
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
  const [selectedFilenames, setSelectedFilenames] = useState<Set<string>>(new Set());

  const filenamesArray = useMemo(() => Array.from(selectedFilenames), [selectedFilenames]);

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "http://localhost:8000/api/v2/chat",
    body: { 
      course_id: courseId, 
      use_rag: true,
      filenames: filenamesArray
    },
  });

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v2/moodle/courses/${courseId}/files`);
        if (res.ok) {
          const data = await res.json();
          setFiles(data);
          // Par défaut, sélectionner tous les fichiers injectés
          const ingested = data.filter((f: CourseFile) => f.ingested).map((f: CourseFile) => f.name);
          setSelectedFilenames(new Set(ingested));
        }
      } catch (err) {
        console.error("Erreur lors de la récupération des fichiers:", err);
      } finally {
        setLoadingFiles(false);
      }
    };
    fetchFiles();
  }, [courseId]);

  const toggleFileSelection = (filename: string) => {
    const newSelection = new Set(selectedFilenames);
    if (newSelection.has(filename)) {
      newSelection.delete(filename);
    } else {
      newSelection.add(filename);
    }
    setSelectedFilenames(newSelection);
  };

  const toggleAll = () => {
    if (selectedFilenames.size === files.filter(f => f.ingested).length) {
      setSelectedFilenames(new Set());
    } else {
      setSelectedFilenames(new Set(files.filter(f => f.ingested).map(f => f.name)));
    }
  };

  return (
    <div className="nf-layout">
      <div className="nf-sidebar">
        <Link href="/?view=courses" className="nf-sidebar__item">
          <ArrowLeft size={20} />
          Retour aux cours
        </Link>
        
        <div className="nf-sidebar__section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", paddingRight: "4px" }}>
            <h4 className="nf-sidebar__label" style={{ margin: 0 }}>Documents du cours</h4>
            <button 
              onClick={toggleAll}
              style={{ 
                background: "none", 
                border: "none", 
                color: "var(--nf-accent)", 
                fontSize: "10px", 
                fontWeight: "700",
                textTransform: "uppercase",
                cursor: "pointer",
                padding: "2px 6px",
                letterSpacing: "0.05em",
                opacity: 0.7,
                transition: "opacity 0.2s"
              }}
              className="nf-sidebar-action-toggle"
              onMouseOver={(e) => e.currentTarget.style.opacity = "1"}
              onMouseOut={(e) => e.currentTarget.style.opacity = "0.7"}
            >
              {files.length > 0 && selectedFilenames.size === files.filter(f => f.ingested).length 
                ? "AUCUN" 
                : "TOUS"}
            </button>
          </div>
          
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
                  className={`nf-sidebar__item ${selectedFilenames.has(file.name) ? 'nf-sidebar__item--active' : ''}`}
                  style={{ 
                    padding: "8px 12px", 
                    gap: "8px", 
                    opacity: file.ingested ? 1 : 0.6,
                    cursor: "default"
                  }}
                >
                  <div 
                    onClick={() => file.ingested && toggleFileSelection(file.name)}
                    style={{ cursor: file.ingested ? "pointer" : "not-allowed", display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: 0 }}
                    title={!file.ingested ? "Document non indexé" : "Cliquer pour inclure/exclure du contexte"}
                  >
                    {selectedFilenames.has(file.name) ? (
                      <CheckSquare size={16} color="var(--nf-accent)" style={{ minWidth: "16px", flexShrink: 0 }} />
                    ) : (
                      <Square size={16} color="var(--nf-text-muted)" style={{ minWidth: "16px", flexShrink: 0 }} />
                    )}
                    <span style={{ 
                      overflow: "hidden", 
                      textOverflow: "ellipsis", 
                      whiteSpace: "nowrap",
                      fontSize: "12px",
                      color: selectedFilenames.has(file.name) ? "var(--nf-text)" : "var(--nf-text-muted)"
                    }}>
                      {file.name}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {!file.ingested && (
                      <span title="Non indexé par l'IA">
                        <AlertTriangle 
                          size={14} 
                          color="var(--nf-warning)" 
                        />
                      </span>
                    )}
                    <button
                      onClick={() => window.open(`http://localhost:8000/api/v2/moodle/courses/${courseId}/files/${file.path}`, '_blank')}
                      style={{ 
                        background: "none", 
                        border: "none", 
                        padding: "4px", 
                        cursor: "pointer", 
                        color: "var(--nf-text-muted)",
                        borderRadius: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center"
                      }}
                      className="nf-button-ghost"
                      title="Ouvrir le document"
                    >
                      <ExternalLink size={14} />
                    </button>
                  </div>
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
