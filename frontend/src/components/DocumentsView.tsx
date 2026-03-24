"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
    FileText, FilePlus, Search, CheckCircle, Clock, 
    Trash2, ExternalLink, Filter, FolderOpen 
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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

const FILE_ICONS: Record<string, React.ReactNode> = {
    pdf: <FileText size={24} color="#ef4444" />,
    doc: <FileText size={24} color="#3b82f6" />,
    docx: <FileText size={24} color="#3b82f6" />,
    xlsx: <FilePlus size={24} color="#10b981" />,
    pptx: <FilePlus size={24} color="#f59e0b" />,
    txt: <FileText size={24} color="#6b7280" />,
    md: <FileText size={24} color="#6b7280" />,
    csv: <FilePlus size={24} color="#10b981" />,
};

const STATUS_CONFIG = {
    analyzed: { label: "Analyzed", badge: "nf-card__badge--success" },
    pending: { label: "Pending", badge: "nf-card__badge--warning" },
    error: { label: "Error", badge: "nf-card__badge--danger" },
};

function getFileIcon(fileName: string): React.ReactNode {
    const ext = fileName.split(".").pop()?.toLowerCase() || "";
    return FILE_ICONS[ext] || <FileText size={24} />;
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
        tags.push(words > 1000 ? `~${(words / 1000).toFixed(1)}k words` : `~${words} words`);
    }
    if (doc.file_size && doc.file_size !== "—") tags.push(doc.file_size);
    tags.push("RAG indexed");
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
            if (!res.ok) throw new Error("API Error");
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
                        ? new Date(doc.ingested_at).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                        })
                        : "—",
                    status: "analyzed" as const,
                    tags: buildTags(doc),
                    summary: `Document indexed with ${doc.chunks} passage${doc.chunks > 1 ? "s" : ""} for contextual search.`,
                })
            );

            setDocuments(docs);
        } catch {
            console.error("Unable to load documents");
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
            console.error("Delete error");
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
            <div className="nf-page-header">
                <h1 className="nf-page-header__title">Documents</h1>
                <p className="nf-page-header__subtitle">Manage your knowledge base</p>
            </div>

            {/* Stats Bar */}
            <div style={{ display: "flex", gap: "12px" }}>
                {[
                    { label: "Total", value: documents.length, color: "var(--nf-accent)" },
                    { label: "Analyzed", value: analyzedCount, color: "var(--nf-success)" },
                    { label: "Pending", value: pendingCount, color: "var(--nf-warning)" },
                ].map((stat) => (
                    <div key={stat.label} className="nf-card" style={{ flex: 1, textAlign: "center", padding: "16px" }}>
                        <div style={{ fontSize: "24px", fontWeight: 700, color: stat.color }}>{stat.value}</div>
                        <div style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginTop: "4px" }}>{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Search & Filters */}
            <div className="nf-card">
                <div style={{ display: "flex", gap: "12px", alignItems: "center", position: "relative" }}>
                    <Search size={16} style={{ position: "absolute", left: "12px", color: "var(--nf-text-muted)" }} />
                    <input
                        className="nf-input"
                        placeholder="Search documents or tags..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ flex: 1, paddingLeft: "36px" }}
                    />
                    <div style={{ display: "flex", gap: "4px" }}>
                        {(["all", "analyzed", "pending"] as const).map((f) => (
                            <button
                                key={f}
                                className={`nf-btn ${filter === f ? "nf-btn--primary" : "nf-btn--ghost"}`}
                                onClick={() => setFilter(f)}
                                style={{ fontSize: "12px", padding: "8px 14px", display: "flex", alignItems: "center", gap: "6px" }}
                            >
                                {f === "all" ? "All" : f === "analyzed" ? <><CheckCircle size={14} /> Analyzed</> : <><Clock size={14} /> Pending</>}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Loading */}
            {isLoading && (
                <div className="nf-loading" style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "center" }}>
                    <Clock size={16} className="nf-spin" /> Loading documents...
                </div>
            )}

            {/* Documents List */}
            {!isLoading && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {filteredDocs.map((doc) => (
                        <div
                            key={doc.id}
                            className="nf-card nf-card--glow"
                            style={{ padding: "16px", cursor: "pointer" }}
                            onClick={() => handleOpen(doc.id)}
                        >
                            <div style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
                                {/* File Icon */}
                                <div style={{
                                    fontSize: "28px",
                                    width: "44px",
                                    height: "44px",
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
                                        <p style={{ fontSize: "12px", color: "var(--nf-text-secondary)", lineHeight: 1.5, marginBottom: "8px" }}>
                                            {doc.summary}
                                        </p>
                                    )}

                                    <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                                        {doc.tags.map((tag) => (
                                            <span
                                                key={tag}
                                                style={{
                                                    fontSize: "10px",
                                                    padding: "2px 8px",
                                                    borderRadius: "10px",
                                                    background: tag === "RAG indexed"
                                                        ? "rgba(124, 92, 252, 0.15)"
                                                        : "var(--nf-bg-tertiary)",
                                                    color: tag === "RAG indexed"
                                                        ? "var(--nf-accent)"
                                                        : "var(--nf-text-muted)",
                                                    border: tag === "RAG indexed"
                                                        ? "1px solid rgba(124, 92, 252, 0.3)"
                                                        : "1px solid var(--nf-border)",
                                                }}
                                            >
                                                {tag}
                                            </span>
                                        ))}

                                        <span style={{ fontSize: "11px", color: "var(--nf-text-muted)", marginLeft: "auto", whiteSpace: "nowrap" }}>
                                            {doc.uploadedAt}
                                        </span>

                                        <button
                                            className="nf-btn nf-btn--ghost"
                                            onClick={(e) => { e.stopPropagation(); handleOpen(doc.id); }}
                                            style={{ fontSize: "11px", padding: "4px 10px", display: "flex", alignItems: "center", gap: "4px" }}
                                        >
                                            <FolderOpen size={14} /> Open
                                        </button>
                                        <button
                                            className="nf-btn nf-btn--danger"
                                            onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                                            style={{ fontSize: "11px", padding: "4px 10px" }}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}

                    {filteredDocs.length === 0 && (
                        <div className="nf-empty-state">
                            <span className="nf-empty-state__icon" style={{ opacity: 0.5 }}>
                                {documents.length === 0 ? <FilePlus size={48} /> : <Search size={48} />}
                            </span>
                            <span className="nf-empty-state__text">
                                {documents.length === 0
                                    ? "No documents yet. Drop a file in the Drop Zone to get started!"
                                    : "No documents match your search."}
                            </span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
