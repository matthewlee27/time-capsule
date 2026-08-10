"use client";

import Basic from "@/components/visualizations/basicVis";
import TopTracksVis from "@/components/visualizations/topTracksVis";

export default function VisualDashboard({ visualType }) {
    if (visualType == "basic") {
        return <Basic />;
    }
    if (visualType == "topTracks") {
        return <TopTracksVis />;
    }
    return <p>No visualization of this type exists.</p>
}