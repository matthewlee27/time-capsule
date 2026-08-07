"use client";

import Basic from "@/components/visualizations/basicVis";

export default function VisualDashboard({ visualType }) {
    if (visualType == "basic") {
        return <Basic />;
    }
    return <p>No visualization of this type exists.</p>
}