"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "../services/scholarshipApi";

type BackendStatusState = "checking" | "connected" | "not_connected";

export function BackendStatus() {
  const [status, setStatus] = useState<BackendStatusState>("checking");

  useEffect(() => {
    let isMounted = true;

    checkBackendHealth()
      .then(() => {
        if (isMounted) {
          setStatus("connected");
        }
      })
      .catch(() => {
        if (isMounted) {
          setStatus("not_connected");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className={`backend-status backend-status-${status}`} aria-live="polite">
      <span className="backend-status-dot" aria-hidden="true" />
      <span>Backend: {statusLabel(status)}</span>
    </div>
  );
}

function statusLabel(status: BackendStatusState) {
  if (status === "connected") {
    return "Connected";
  }
  if (status === "checking") {
    return "Checking";
  }
  return "Not connected";
}
