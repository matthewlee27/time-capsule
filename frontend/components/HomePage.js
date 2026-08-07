"use client";

import { useEffect, useState } from "react";
import ConnectForm from "@/components/ConnectForm";
import PullSection from "@/components/PullSection";
import { getConnectedUsername, getLastPull } from "@/lib/session";

export default function HomePage() {
  const [step, setStep] = useState("idle"); // idle | form | connected
  const [username, setUsername] = useState(null);
  const [initialPullStatus, setInitialPullStatus] = useState("");

  useEffect(() => {
    const connectedUsername = getConnectedUsername();
    if (connectedUsername) {
      setUsername(connectedUsername);
      setStep("connected");

      const lastPull = getLastPull();
      if (lastPull) {
        setInitialPullStatus(
          `Fetched ${lastPull.pulled_from_lastfm} scrobbles — ${lastPull.saved} new, ` +
            `${lastPull.duplicates} already saved (${lastPull.total_stored} stored total).`
        );
      }
    }
  }, []);

  return (
    <>
      <p>Turn your old listening habits into a new playlist.</p>

      {step === "idle" && (
        <button id="start-btn" onClick={() => setStep("form")}>
          Start
        </button>
      )}

      {step === "form" && (
        <ConnectForm
          onConnected={(connectedUsername) => {
            setUsername(connectedUsername);
            setStep("connected");
          }}
        />
      )}

      {step === "connected" && (
        <PullSection username={username} initialStatus={initialPullStatus} />
      )}
    </>
  );
}
