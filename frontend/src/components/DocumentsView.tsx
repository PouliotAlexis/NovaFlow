"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Document {
    id: string;
    name: string;
    type: string;
    ext: string;
    size: string;
    pages: number;
    chars: number;
    chunks: number;
    uploadedAt: string;
    status: "analyzed" | "pending" | "error";
    tags: string[];
    summary?: string;
}

const FILE_ICONS: Record<string, string> = {
    pdf: "📕",
    doc: "📘",
    docx: "📘",
    xlsx: "📗",
    pptx: "📙",
    txt: "📝",
    md: "📝",
    csv: "📊",
};

const STATUS_CONFIG = {
    analyzed: { label: "Analysé", badge: "nf-card__badge--success" },
    pending: { label: "En attente", badge: "nf-card__badge--warning" },
    error: { label: "Erreur", badge: "nf-card__badge--danger" },
};

function getFileIcon(fileName: string): string {
    const ext = fileName.split(".").pop()?.toLowerCase() || "";
    return FILE_ICONS[ext] || "📄";
}

function buildTags(doc: {
    file_ext: string;
    total_pages: number;
    chunks: number;
    total_chars: number;
    file_size: string;
}): string[] {
    const tags: string[] = [];
    if (doc.file_ext) tags.push(doc.file_ext.toUpperCase());
    if (doc.total_pages > 0) tags.push(`${doc.total_pages} page${doc.total_pages > 1 ? "s" : ""}`);
    tags.push(`${doc.chunks} chunk${doc.chunks > 1 ? "s" : ""}`);
    if (doc.total_chars > 0) {
        const words = Math.round(doc.total_chars / 5);
        tags.push(words > 1000 ? `~${(words / 1000).toFixed(1)}k mots` : `~${words} mots`);
    }
    if (doc.file_size && doc.file_size !== "—") tags.push(doc.file_size);
    tags.push("RAG indexé");
    return tags;
}

export default function DocumentsView() {
    const [filter, setFilter] = useState<"all" | "analyzed" | "pending">("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchDocuments = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/documents`);
            if (!res.ok) throw new Error("Erreur API");
            const data = await res.json();

            const docs: Document[] = (data.documents || []).map(
                (doc: {
                    doc_id: string;
                    file_name: string;
                    file_ext: string;
                    file_size: string;
                    total_pages: number;
                    total_chars: number;
                    chunks: number;
                    ingested_at: string;
                }) => ({
                    id: doc.doc_id,
                    name: doc.file_name,
                    type: doc.file_ext || doc.file_name.split(".").pop()?.toLowerCase() || "txt",
                    ext: doc.file_ext,
                    size: doc.file_size || "—",
                    pages: doc.total_pages || 0,
                    chars: doc.total_chars || 0,
                    chunks: doc.chunks,
                    uploadedAt: doc.ingested_at
                        ? new Date(doc.ingested_at).toLocaleDateString("fr-CA", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                        })
                        : "—",
                    status: "analyzed" as const,
                    tags: buildTags(doc),
                    summary: `Document indexé avec ${doc.chunks} passage${doc.chunks > 1 ? "s" : ""} pour la recherche contextuelle.`,
                })
            );

            setDocuments(docs);
        } catch {
            console.error("Impossible de charger les documents");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDocuments();
        const interval = setInterval(fetchDocuments, 10000);
        return () => clearInterval(interval);
    }, [fetchDocuments]);

    const handleDelete = async (docId: string) => {
        try {
            const res = await fetch(`${API_URL}/api/documents/${docId}`, { method: "DELETE" });
            if (res.ok) {
                setDocuments((prev) => prev.filter((d) => d.id !== docId));
            }
        } catch {
            console.error("Erreur de suppression");
        }
    };

    const handleOpen = (docId: string) => {
        window.open(`${API_URL}/api/documents/${docId}/download`, "_blank");
    };

    const filteredDocs = documents.filter((doc) => {
        const matchesFilter = filter === "all" || doc.status === filter;
        const matchesSearch =
            searchQuery === "" ||
            doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            doc.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
        return matchesFilter && matchesSearch;
    });

    const analyzedCount = documents.filter((d) => d.status === "analyzed").length;
    const pendingCount = documents.filter((d) => d.status === "pending").length;

    return (
        <div className="nf-animate-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Stats Bar */}
            <div style={{ display: "flex", gap: "16px" }}>
                <div className="nf-stat" style={{ flex: 1 }}>
                    <span className="nf-stat__value" style={{ color: "var(--nf-accent-primary)" }}>{documents.length}</span>
                    <span className="nf-stat__label">Total</span>
                </div>
                <div className="nf-stat" style={{ flex: 1 }}>
                    <span className="nf-stat__value" style={{ color: "var(--nf-success)" }}>{analyzedCount}</span>
                    <span className="nf-stat__label">Analysés</span>
                </div>
                <div className="nf-stat" style={{ flex: 1 }}>
                    <span className="nf-stat__value" style={{ color: "var(--nf-warning)" }}>{pendingCount}</span>
                    <span className="nf-stat__label">En attente</span>
                </div>
            </div>

            {/* Search & Filters */}
            <div className="nf-card">
                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                    <input
                        className="nf-chat__input"
                        placeholder="🔍 Rechercher un document ou un tag..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ flex: 1 }}
                    />
                    <div style={{ display: "flex", gap: "4px" }}>
                        {(["all", "analyzed", "pending"] as const).map((f) => (
                            <button
                                key={f}
                                className={`nf-btn ${filter === f ? "nf-btn--primary" : "nf-btn--ghost"}`}
                                onClick={() => setFilter(f)}
                                style={{ fontSize: "12px", padding: "8px 14px" }}
                            >
                                {f === "all" ? "Tous" : f === "analyzed" ? "✅ Analysés" : "⏳ En attente"}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="nf-card" style={{ textAlign: "center", padding: "40px" }}>
                    <span style={{ fontSize: "32px", display: "block", marginBottom: "8px" }}>⏳</span>
                    <p style={{ color: "var(--nf-text-muted)" }}>Chargement des documents...</p>
                </div>
            )}

            {/* Documents List */}
            {!isLoading && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {filteredDocs.map((doc) => (
                        <div
                            key={doc.id}
                            className="nf-card"
                            style={{ padding: "16px", cursor: "pointer", transition: "transform 0.15s" }}
                            onClick={() => handleOpen(doc.id)}
                            onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1px)")}
                            onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
                        >
                            <div style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
                                {/* File Icon */}
                                <div style={{
                                    fontSize: "32px",
                                    width: "48px",
                                    height: "48px",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    background: "var(--nf-bg-tertiary)",
                                    borderRadius: "var(--nf-radius-sm)",
                                    flexShrink: 0,
                                }}>
                                    {getFileIcon(doc.name)}
                                </div>

                                {/* Content */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                                        <span style={{ fontSize: "14px", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                            {doc.name}
                                        </span>
                                        <span className={`nf-card__badge ${STATUS_CONFIG[doc.status].badge}`}>
                                            {STATUS_CONFIG[doc.status].label}
                                        </span>
                                    </div>

                                    {doc.summary && (
                                        <p style={{ fontSize: "13px", color: "var(--nf-text-secondary)", lineHeight: 1.5, marginBottom: "8px" }}>
                                            {doc.summary}
                                        </p>
                                    )}

                                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                                        {/* Tags */}
                                        {doc.tags.map((tag) => (
                                            <span
                                                key={tag}
                                                style={{
                                                    fontSize: "11px",
                                                    padding: "2px 8px",
                                                    borderRadius: "12px",
                                                    background: tag === "RAG indexé"
                                                        ? "rgba(139, 92, 246, 0.15)"
                                                        : "var(--nf-bg-tertiary)",
                                                    color: tag === "RAG indexé"
                                                        ? "var(--nf-accent-primary)"
                                                        : "var(--nf-text-muted)",
                                                    border: tag === "RAG indexé"
                                                        ? "1px solid rgba(139, 92, 246, 0.3)"
                                                        : "1px solid var(--nf-border)",
                                                }}
                                            >
                                                {tag}
                                            </span>
                                        ))}

                                        <span style={{ fontSize: "12px", color: "var(--nf-text-muted)", marginLeft: "auto", whiteSpace: "nowrap" }}>
                                            {doc.uploadedAt}
                                        </span>

                                        {/* Actions */}
                                        <button
                                            className="nf-btn nf-btn--ghost"
                                            onClick={(e) => { e.stopPropagation(); handleOpen(doc.id); }}
                                            style={{ fontSize: "12px", padding: "4px 10px" }}
                                            title="Ouvrir"
                                        >
                                            📂 Ouvrir
                                        </button>
                                        <button
                                            className="nf-btn nf-btn--ghost"
                                            onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                                            style={{ fontSize: "12px", padding: "4px 10px", color: "var(--nf-danger)" }}
                                            title="Supprimer"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}

                    {filteredDocs.length === 0 && (
                        <div className="nf-card" style={{ textAlign: "center", padding: "40px" }}>
                            <span style={{ fontSize: "32px", display: "block", marginBottom: "8px" }}>
                                {documents.length === 0 ? "📄" : "🔍"}
                            </span>
                            <p style={{ color: "var(--nf-text-muted)" }}>
                                {documents.length === 0
                                    ? "Aucun document. Glisse un fichier dans la Drop Zone pour commencer !"
                                    : "Aucun document trouvé pour cette recherche."}
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
