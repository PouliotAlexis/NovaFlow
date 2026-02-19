"use client";

import React from "react";

export default function ProductivityTrend() {
    // Placeholder - static SVG chart
    const points = [30, 45, 35, 55, 50, 65, 60, 72, 68, 78, 75, 82];
    const width = 240;
    const height = 80;
    const maxVal = Math.max(...points);
    const minVal = Math.min(...points);
    const range = maxVal - minVal || 1;

    const pathData = points
        .map((val, i) => {
            const x = (i / (points.length - 1)) * width;
            const y = height - ((val - minVal) / range) * (height - 10) - 5;
            return `${i === 0 ? "M" : "L"} ${x} ${y}`;
        })
        .join(" ");

    const areaData = pathData + ` L ${width} ${height} L 0 ${height} Z`;

    return (
        <div className="nf-card nf-card--glow nf-animate-in">
            <div className="nf-card__header">
                <span className="nf-card__title">📈 Productivity Trend</span>
                <span className="nf-productivity__badge">↑ +12% this week</span>
            </div>
            <div className="nf-productivity">
                <div className="nf-productivity__chart">
                    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="rgba(124, 92, 252, 0.3)" />
                                <stop offset="100%" stopColor="rgba(124, 92, 252, 0)" />
                            </linearGradient>
                        </defs>
                        <path d={areaData} fill="url(#trendGrad)" />
                        <path d={pathData} fill="none" stroke="#7c5cfc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </div>
            </div>
        </div>
    );
}
