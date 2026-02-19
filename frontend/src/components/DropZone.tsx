"use client";

import React, { useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UploadedFile {
    name: string;
    status: "uploading" | "analyzed" | "error";
    doc_id?: string;
    pages?: number;
    chunks?: number;
    preview?: string;
    message?: string;
}

export default function DropZone() {
    const [isDragging, setIsDragging] = useState(false);
    const [files, setFiles] = useState<UploadedFile[]>([]);

    const uploadFile = async (file: File) => {
        const tempFile: UploadedFile = { name: file.name, status: "uploading" };
        setFiles((prev) => [...prev, tempFile]);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(`${API_URL}/api/upload`, {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Upload error");
            }

            const result = await response.json();

            setFiles((prev) =>
                prev.map((f) =>
                    f.name === file.name
                        ? {
                            ...f,
                            status: result.status === "analyzed" ? "analyzed" : "error",
                            doc_id: result.doc_id,
                            pages: result.pages,
                            chunks: result.chunks,
                            preview: result.preview,
                            message: result.message,
                        }
                        : f
                )
            );
        } catch (err) {
            setFiles((prev) =>
                prev.map((f) =>
                    f.name === file.name
                        ? { ...f, status: "error", message: err instanceof Error ? err.message : "Unknown error" }
                        : f
                )
            );
        }
    };

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const droppedFiles = Array.from(e.dataTransfer.files);
        droppedFiles.forEach(uploadFile);
    }, []);

    const handleClick = useCallback(() => {
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = true;
        input.accept = ".pdf,.txt,.md,.csv,.docx,.jpg,.png";
        input.onchange = (e) => {
            const target = e.target as HTMLInputElement;
            if (target.files) {
                Array.from(target.files).forEach(uploadFile);
            }
        };
        input.click();
    }, []);

    const statusIcons: Record<string, string> = {
        uploading: "⏳",
        analyzed: "✅",
        error: "❌",
    };

    const statusLabels: Record<string, { text: string; badge: string }> = {
        uploading: { text: "Analyzing...", badge: "nf-card__badge--warning" },
        analyzed: { text: "Analyzed", badge: "nf-card__badge--success" },
        error: { text: "Error", badge: "nf-card__badge--danger" },
    };

    return (
        <div className="nf-card nf-card--glow nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">📥 Drop Zone</span>
                {files.length > 0 && (
                    <span className="nf-card__badge nf-card__badge--info">
                        {files.filter((f) => f.status === "analyzed").length}/{files.length} analyzed
                    </span>
                )}
            </div>

            <div
                className={`nf-dropzone ${isDragging ? "nf-dropzone--active" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <span className="nf-dropzone__icon">
                    {isDragging ? "🎯" : "☁️"}
                </span>
                <span className="nf-dropzone__title">
                    {isDragging ? "Drop it here!" : "Drag & Drop Files Here"}
                </span>
                <span className="nf-dropzone__subtitle">
                    or Click to Browse
                </span>
                <span className="nf-dropzone__formats">
                    Supported formats: PDF, DOCX, JPG, PNG. Max size: 50MB.
                </span>
            </div>

            {files.length > 0 && (
                <div className="nf-task-list" style={{ marginTop: "12px" }}>
                    {files.map((file, i) => (
                        <div key={i} className="nf-task">
                            <span style={{ fontSize: "16px" }}>{statusIcons[file.status]}</span>
                            <div className="nf-task__content">
                                <div className="nf-task__title">{file.name}</div>
                                <div className="nf-task__meta">
                                    {file.status === "analyzed"
                                        ? `${file.pages} page${(file.pages || 0) > 1 ? "s" : ""} · ${file.chunks} chunks indexed`
                                        : file.message || statusLabels[file.status].text}
                                </div>
                                {file.preview && file.status === "analyzed" && (
                                    <div className="nf-task__meta" style={{
                                        marginTop: "4px", fontStyle: "italic", opacity: 0.6,
                                        maxHeight: "32px", overflow: "hidden",
                                    }}>
                                        &quot;{file.preview.slice(0, 120)}...&quot;
                                    </div>
                                )}
                            </div>
                            <span className={`nf-card__badge ${statusLabels[file.status].badge}`}>
                                {statusLabels[file.status].text}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
