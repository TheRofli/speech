import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import "./styles.css";

type AppSnapshot = {
  running: boolean;
  modelInstalled: boolean;
  modelSizeLabel: string;
  modelSnapshot: string;
  historyCount: number;
  speechRoot: string;
};

type HistoryItem = {
  id: string;
  createdAt: string;
  text: string;
};

type Tab = "overview" | "controls" | "history" | "install";

const emptySnapshot: AppSnapshot = {
  running: false,
  modelInstalled: false,
  modelSizeLabel: "0 GB",
  modelSnapshot: "",
  historyCount: 0,
  speechRoot: "D:\\Speech",
};

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "controls", label: "Controls" },
  { id: "history", label: "History" },
  { id: "install", label: "Install" },
];

function App() {
  const [snapshot, setSnapshot] = useState<AppSnapshot>(emptySnapshot);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [filter, setFilter] = useState("");
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");

  async function refresh() {
    const [nextSnapshot, nextHistory] = await Promise.all([
      invoke<AppSnapshot>("app_snapshot"),
      invoke<HistoryItem[]>("recent_history", { limit: 24 }),
    ]);
    setSnapshot(nextSnapshot);
    setHistory(nextHistory);
    setSelectedId((current) => current || nextHistory[0]?.id || "");
  }

  async function runAction(command: "speech_status" | "speech_diagnose" | "speech_restart" | "speech_stop") {
    setBusy(true);
    try {
      const output = await invoke<string>(command);
      setLog(output.trim() || "Done");
      await refresh();
    } catch (error) {
      setLog(String(error));
    } finally {
      setBusy(false);
    }
  }

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setLog("Copied transcript");
    } catch (error) {
      setLog(`Copy failed: ${String(error)}`);
    }
  }

  useEffect(() => {
    refresh().catch((error) => setLog(String(error)));
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(timer);
  }, []);

  const statusText = snapshot.running ? "Ready" : "Stopped";
  const selected = history.find((item) => item.id === selectedId) || history[0];
  const filteredHistory = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) {
      return history;
    }
    return history.filter((item) => item.text.toLowerCase().includes(query));
  }, [filter, history]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
          <div>
            <h1>Speech</h1>
            <p>local dictation</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="Speech sections">
          {tabs.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "active" : ""}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="soft-note">
          <span>Parakeet</span>
          <strong>{snapshot.modelInstalled ? snapshot.modelSizeLabel : "missing"}</strong>
        </div>
      </aside>

      <section className="content">
        <header className="top-strip">
          <div>
            <p className="quiet-label">Status</p>
            <h2>{statusText}</h2>
          </div>
          <div className={snapshot.running ? "status-pill on" : "status-pill"}>
            <span />
            {snapshot.running ? "Running" : "Off"}
          </div>
          <button className="secondary-button" onClick={() => refresh()} disabled={busy}>
            Refresh
          </button>
        </header>

        {tab === "overview" && (
          <div className="overview-layout">
            <article className="hero-card">
              <div>
                <p className="quiet-label">Push-to-talk</p>
                <h3>Hold, speak, release.</h3>
                <p>
                  Speech keeps transcription local, then sends the text to the active
                  input, clipboard, and history.
                </p>
              </div>
              <WavePreview />
            </article>

            <div className="metric-grid">
              <Metric title="Runtime" value={statusText} detail={snapshot.speechRoot} />
              <Metric title="Model" value={snapshot.modelSizeLabel} detail={snapshot.modelSnapshot || "Install Parakeet"} />
              <Metric title="History" value={String(snapshot.historyCount)} detail="local transcript rows" />
              <Metric title="Device" value="CPU" detail="stable default" />
            </div>

            {selected && (
              <article className="latest-card">
                <div>
                  <p className="quiet-label">Latest transcript</p>
                  <p>{selected.text}</p>
                </div>
                <button onClick={() => copyText(selected.text)}>Copy</button>
              </article>
            )}
          </div>
        )}

        {tab === "controls" && (
          <section className="control-stack">
            <article className="control-card">
              <div>
                <p className="quiet-label">Engine</p>
                <h3>Python runtime bridge</h3>
                <p>
                  The Tauri window controls the proven Python engine while the UI moves
                  into a smoother native shell.
                </p>
              </div>
              <div className="button-row">
                <button onClick={() => runAction("speech_status")} disabled={busy}>Status</button>
                <button onClick={() => runAction("speech_diagnose")} disabled={busy}>Diagnose</button>
                <button onClick={() => runAction("speech_restart")} disabled={busy}>Restart</button>
                <button className="danger" onClick={() => runAction("speech_stop")} disabled={busy}>Stop</button>
              </div>
            </article>
            <pre className="log-output">{log || "Command output will appear here."}</pre>
          </section>
        )}

        {tab === "history" && (
          <section className="history-panel">
            <div className="history-toolbar">
              <div>
                <p className="quiet-label">History</p>
                <h3>{filteredHistory.length} transcripts</h3>
              </div>
              <input
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                placeholder="Search transcripts"
              />
            </div>
            <div className="history-list">
              {filteredHistory.length === 0 && <div className="empty">No matching transcripts.</div>}
              {filteredHistory.map((item) => (
                <article
                  className={item.id === selected?.id ? "history-item selected" : "history-item"}
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                >
                  <div>
                    <time>{formatTime(item.createdAt)}</time>
                    <p>{item.text}</p>
                  </div>
                  <button onClick={(event) => { event.stopPropagation(); copyText(item.text); }}>
                    Copy
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        {tab === "install" && (
          <section className="install-panel">
            <article>
              <p className="quiet-label">One command</p>
              <h3>Install from GitHub</h3>
              <code>
                powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1 | iex"
              </code>
            </article>
            <article>
              <p className="quiet-label">Model</p>
              <h3>Download Parakeet</h3>
              <code>speech parakeet install</code>
            </article>
            <article>
              <p className="quiet-label">Requirements</p>
              <h3>Comfortable setup</h3>
              <p>Windows 11, Python 3.11, 16 GB RAM, 20 GB free disk, microphone.</p>
            </article>
          </section>
        )}
      </section>
    </main>
  );
}

function Metric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <p className="quiet-label">{title}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}

function WavePreview() {
  return (
    <div className="wave-preview" aria-hidden="true">
      {[12, 24, 34, 24, 14, 28, 18].map((height, index) => (
        <span key={index} style={{ height }} />
      ))}
    </div>
  );
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
