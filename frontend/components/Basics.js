"use client";

import { useEffect, useState } from "react";

export default function Dropdown({ options, value, onChange }) {
    return (
        <select value={value} onChange={(e) => onChange(e.target.value)}>
            {options.map((opt) => (
                <option key={opt} value={opt}>
                    {opt}
                </option>
            ))}
        </select>

    )
}