"use client";

import React from "react";

export default function WeatherWidget() {
    // Placeholder - static weather data
    return (
        <div className="nf-card nf-card--glow nf-animate-in">
            <div className="nf-weather">
                <div className="nf-weather__icon">
                    {/* Sun + Cloud SVG */}
                    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                        <circle cx="22" cy="22" r="8" fill="#fbbf24" />
                        <path d="M22 10v-4M22 38v-4M10 22H6M38 22h-4M13.5 13.5l-2.8-2.8M33.3 33.3l-2.8-2.8M13.5 30.5l-2.8 2.8M33.3 10.7l-2.8 2.8" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" />
                        <path d="M30 30c2-1 4-1 6 0s4 3 4 6c0 3-2 5-5 5H20c-4 0-7-3-7-6s2-5 5-6c1-3 4-5 7-5s6 2 7 5l-2 1z" fill="rgba(200,210,230,0.3)" stroke="rgba(200,210,230,0.5)" strokeWidth="1" />
                    </svg>
                </div>
                <div className="nf-weather__temp">18°C / 64°F</div>
                <div className="nf-weather__desc">
                    Mild day ahead, perfect<br />for focused work.
                </div>
            </div>
        </div>
    );
}
