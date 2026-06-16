"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef, Suspense } from "react";
import { useChat, Message } from "ai/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Send, BookOpen, Paperclip, AlertTriangle, Loader2, ExternalLink, CheckSquare, Square, Sparkles, User } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

interface CourseFile {
  name: string;
  ingested: boolean;
  size: number;
  path: string;
}

function CourseChatContent() {
  const searchParams = useSearchParams();
  const courseId = searchParams.get("courseId") || "";
  const [files, setFiles] = useState<CourseFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [selectedFilenames, setSelectedFilenames] = useState<Set<string>>(new Set());
  const [courseName, setCourseName] = useState<string>("");

  
  // États pour le redimensionnement de la barre latérale
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback((e: MouseEvent) => {
    if (isResizing) {
      const newWidth = e.clientX;
      if (newWidth > 240 && newWidth < 600) {
        setSidebarWidth(newWidth);
      }
    }
  }, [isResizing]);

  useEffect(() => {
    if (isResizing) {
      window.addEventListener("mousemove", resize);
      window.addEventListener("mouseup", stopResizing);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    } else {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
      document.body.style.cursor = "default";
      document.body.style.userSelect = "auto";
    }
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
      document.body.style.cursor = "default";
      document.body.style.userSelect = "auto";
    };
  }, [isResizing, resize, stopResizing]);

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
    const fetchCourseDetails = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v2/moodle/courses/${courseId}`);
        if (res.ok) {
          const data = await res.json();
          setCourseName(data.name);
        }
      } catch (err) {
        console.error("Erreur lors de la récupération des détails du cours:", err);
      }
    };

    fetchFiles();
    fetchCourseDetails();
  }, [courseId]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    // On considère qu'on est en bas si on est à moins de 50px du bord
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    shouldAutoScroll.current = isAtBottom;
  };

  useEffect(() => {
    if (shouldAutoScroll.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [messages]);

  const sidebarRef = React.useRef<HTMLDivElement>(null);

  const handleDoubleClick = useCallback(() => {
    if (!sidebarRef.current) return;
    
    const sidebar = sidebarRef.current;
    
    // 1. On enlève le overflow: hidden des spans pour que le texte prenne sa taille naturelle
    const spans = sidebar.querySelectorAll('.nf-sidebar__item span');
    const originalSpanStyles: string[] = [];
    spans.forEach((span, i) => {
      const el = span as HTMLElement;
      originalSpanStyles[i] = el.style.cssText;
      el.style.overflow = "visible";
      el.style.textOverflow = "clip";
    });

    // 2. Sauvegarder les styles du sidebar
    const origCSS = sidebar.style.cssText;
    
    // 3. On retire le sidebar du flux flex et on le force à prendre sa taille minimale
    sidebar.style.position = "absolute";
    sidebar.style.width = "min-content";
    sidebar.style.minWidth = "0";

    // 4. On mesure la largeur naturelle du contenu
    const naturalWidth = sidebar.offsetWidth;

    // 5. On restaure tout
    sidebar.style.cssText = origCSS;
    spans.forEach((span, i) => {
      const el = span as HTMLElement;
      el.style.cssText = originalSpanStyles[i];
    });

    // 6. On applique la largeur mesurée (entre 260px et 600px)
    const finalWidth = Math.min(Math.max(naturalWidth + 4, 260), 600);
    setSidebarWidth(finalWidth);
  }, [files]);

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
      <div 
        ref={sidebarRef}
        className="nf-sidebar" 
        style={{ width: `${sidebarWidth}px`, flexBasis: `${sidebarWidth}px` }}
      >
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
                Aucun document trouvé.
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

      {/* Barre de redimensionnement */}
      <div 
        onMouseDown={startResizing}
        onDoubleClick={handleDoubleClick}
        style={{
          width: "4px",
          height: "100%",
          cursor: "col-resize",
          background: isResizing ? "var(--nf-accent)" : "transparent",
          transition: "background 0.2s",
          zIndex: 10,
          marginLeft: "-2px"
        }}
        onMouseOver={(e) => !isResizing && (e.currentTarget.style.background = "var(--nf-border)")}
        onMouseOut={(e) => !isResizing && (e.currentTarget.style.background = "transparent")}
      />

      <main className="nf-main nf-chat-layout">
        <header className="nf-header">
          <h1 className="nf-header__title">
            Second Brain : {courseName || `Chargement...`}
          </h1>
        </header>


        <div 
          className="nf-chat__messages" 
          ref={scrollContainerRef}
          onScroll={handleScroll}
        >
          {messages.length === 0 && (
            <div className="nf-chat__welcome">
              <h2>Comment puis-je vous aider pour ce cours ?</h2>
              <p>Je peux répondre à vos questions en me basant sur les documents synchronisés de Moodle (PDF, Office, etc.).</p>

            </div>
          )}
          {messages.map((m: Message) => (
            <div key={m.id} className={`nf-chat__message nf-chat__message--${m.role === 'assistant' ? 'ai' : 'user'}`}>
              <div className={`nf-chat__avatar nf-chat__avatar--${m.role === 'assistant' ? 'ai' : 'user'}`}>
                {m.role === 'assistant' ? <Sparkles size={16} color="white" /> : <User size={16} />}
              </div>
              <div className={`nf-chat__bubble nf-chat__bubble--${m.role === 'assistant' ? 'ai' : 'user'} ${m.role === 'assistant' ? 'nf-markdown' : ''}`}>
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
          <div ref={messagesEndRef} />
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

export default function CourseChatPage() {
  return (
    <Suspense fallback={<div className="nf-empty-state">Chargement du chat...</div>}>
      <CourseChatContent />
    </Suspense>
  );
}
