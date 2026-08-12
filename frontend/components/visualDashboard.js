"use client";

import Basic from "@/components/visualizations/basicVis";
import TopTracksVis from "@/components/visualizations/topTracksVis";
import LiftedTopTracksVis from "@/components/visualizations/liftedTopTracks";

export default function VisualDashboard({ visualType, fromDate, toDate }) {
    if (visualType == "basic") {
        return <Basic fromDate={fromDate} toDate={toDate} />;
    }
    if (visualType == "topTracks") {
        return <TopTracksVis fromDate={fromDate} toDate={toDate} />;
    }
    if (visualType == "liftedTopTracks") {
        return <LiftedTopTracksVis fromDate={fromDate} toDate={toDate} />;
    }
    return <p>No visualization of this type exists.</p>
}