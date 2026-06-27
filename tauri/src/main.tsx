import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import "./styles.css";

type AppSnapshot = {
  running: boolean;
  modelRuntimeState: string;
  modelInstalled: boolean;
  modelSizeLabel: string;
  modelSnapshot: string;
  historyCount: number;
  speechRoot: string;
  aiMode: string;
  aiRuntimeState: string;
  aiModelInstalled: boolean;
  aiModelSizeLabel: string;
};

type HistoryItem = {
  id: string;
  createdAt: string;
  text: string;
  originalText: string;
  processingMode: string;
  processingStatus: string;
  processingMs: number;
};

type AiSettings = {
  aiMode: "off" | "local" | "api";
  aiLocalModelId: string;
  aiApiBaseUrl: string;
  aiApiModel: string;
  aiTimeoutSeconds: number;
};

type Tab = "overview" | "controls" | "history" | "analysis" | "install";
type ActionCommand = "speech_status" | "speech_diagnose" | "speech_restart" | "speech_stop";

const emptySnapshot: AppSnapshot = {
  running: false,
  modelRuntimeState: "stopped",
  modelInstalled: false,
  modelSizeLabel: "Not installed",
  modelSnapshot: "",
  historyCount: 0,
  speechRoot: "Speech install folder",
  aiMode: "off",
  aiRuntimeState: "stopped",
  aiModelInstalled: false,
  aiModelSizeLabel: "Not installed",
};

const defaultAiSettings: AiSettings = {
  aiMode: "off",
  aiLocalModelId: "ai-forever/sage-fredt5-distilled-95m",
  aiApiBaseUrl: "https://api.openai.com/v1",
  aiApiModel: "",
  aiTimeoutSeconds: 12,
};

const demoHistory: HistoryItem[] = [
  {
    id: "demo-1",
    createdAt: new Date().toISOString(),
    text: "Your latest transcript will appear here as a soft local note.",
    originalText: "Your latest transcript will appear here as a soft local note.",
    processingMode: "off",
    processingStatus: "skipped",
    processingMs: 0,
  },
  {
    id: "demo-2",
    createdAt: new Date(Date.now() - 900000).toISOString(),
    text: "History stays on this device, ready to search, copy, and review.",
    originalText: "History stays on this device, ready to search, copy, and review.",
    processingMode: "off",
    processingStatus: "skipped",
    processingMs: 0,
  },
];

const tabs: Array<{ id: Tab; label: string; short: string }> = [
  { id: "overview", label: "Overview", short: "Home" },
  { id: "controls", label: "Controls", short: "Run" },
  { id: "history", label: "History", short: "Text" },
  { id: "analysis", label: "Analysis", short: "Later" },
  { id: "install", label: "Install", short: "Setup" },
];

function App() {
  const [snapshot, setSnapshot] = useState<AppSnapshot>(emptySnapshot);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [filter, setFilter] = useState("");
  const [log, setLog] = useState("");
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>(getInitialTab());
  const [aiSettings, setAiSettings] = useState<AiSettings>(defaultAiSettings);
  const [apiKey, setApiKey] = useState("");

  async function refresh() {
    try {
      const [nextSnapshot, nextHistory] = await Promise.all([
        invoke<AppSnapshot>("app_snapshot"),
        invoke<HistoryItem[]>("recent_history", { limit: 80 }),
      ]);
      setSnapshot(nextSnapshot);
      setHistory(nextHistory);
      setSelectedId((current) => current || nextHistory[0]?.id || "");
    } catch (error) {
      setLog(String(error));
      setHistory((current) => (current.length ? current : demoHistory));
    }
  }

  async function saveAiSettings() {
    setBusy(true);
    try {
      await invoke("save_app_settings", { payload: aiSettings });
      await invoke<string>("speech_restart");
      await refresh();
      showToast("AI settings saved");
    } catch (error) {
      setLog(String(error));
      showToast("Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function installAiModel() {
    setBusy(true);
    try {
      setLog("Downloading SAGE 95M...");
      const output = await invoke<string>("speech_ai_install");
      setLog(output.trim());
      await refresh();
      showToast("SAGE is ready");
    } catch (error) {
      setLog(String(error));
      showToast("Download failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveApiKey() {
    if (!apiKey.trim()) return;
    setBusy(true);
    try {
      await invoke<string>("speech_set_api_key", { apiKey });
      setApiKey("");
      showToast("API key saved securely");
    } catch (error) {
      setLog(String(error));
      showToast("Key save failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteApiKey() {
    setBusy(true);
    try {
      await invoke<string>("speech_delete_api_key");
      setApiKey("");
      showToast("API key removed");
    } catch (error) {
      setLog(String(error));
      showToast("Key removal failed");
    } finally {
      setBusy(false);
    }
  }

  async function runAction(command: ActionCommand) {
    setBusy(true);
    try {
      const output = await invoke<string>(command);
      setLog(output.trim() || "Done");
      await refresh();
      showToast("Command finished");
    } catch (error) {
      setLog(String(error));
      showToast("Command failed");
    } finally {
      setBusy(false);
    }
  }

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Copied");
    } catch (error) {
      setLog(`Copy failed: ${String(error)}`);
      showToast("Copy failed");
    }
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 1700);
  }

  function chooseTab(nextTab: Tab) {
    setTab(nextTab);
    window.location.hash = nextTab;
  }

  useEffect(() => {
    refresh();
    invoke<AiSettings>("app_settings").then(setAiSettings).catch((error) => setLog(String(error)));
    const timer = window.setInterval(() => {
      refresh();
    }, 2500);
    return () => window.clearInterval(timer);
  }, []);

  const modelRuntimeState = snapshot.modelRuntimeState || "unknown";
  const statusText = getStatusText(snapshot.running, modelRuntimeState);
  const selected = history.find((item) => item.id === selectedId) || history[0];
  const latest = history[0];
  const filteredHistory = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) {
      return history;
    }
    return history.filter((item) => item.text.toLowerCase().includes(query));
  }, [filter, history]);

  return (
    <main className="app-shell">
      <aside className="shelf">
        <Brand />
        <nav className="nav-list" aria-label="Speech sections">
          {tabs.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "active" : ""}
              onClick={() => chooseTab(item.id)}
            >
              <span>{item.label}</span>
              <small>{item.short}</small>
            </button>
          ))}
        </nav>
        <div className="model-ticket">
          <span>Parakeet</span>
          <strong>
            {modelRuntimeState === "loading"
              ? "loading..."
              : snapshot.modelInstalled
                ? snapshot.modelSizeLabel
                : "missing"}
          </strong>
          <small>
            {modelRuntimeState === "loading"
              ? "starting Parakeet"
              : snapshot.modelSnapshot
                ? shortHash(snapshot.modelSnapshot)
                : "local model"}
          </small>
        </div>
      </aside>

      <section className="stage">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local dictation</p>
            <h1>{statusText}</h1>
          </div>
          <div className="topbar-actions">
            <StatusPill running={snapshot.running} modelState={modelRuntimeState} />
            <button className="ghost-button" onClick={() => refresh()} disabled={busy}>
              Refresh
            </button>
          </div>
        </header>

        <section className="page" key={tab}>
          {tab === "overview" && (
            <Overview
              snapshot={snapshot}
              statusText={statusText}
              latest={latest}
              onCopyLatest={() => latest && copyText(latest.text)}
            />
          )}

          {tab === "controls" && (
            <Controls
              aiSettings={aiSettings}
              apiKey={apiKey}
              busy={busy}
              log={log}
              snapshot={snapshot}
              onAiSettings={setAiSettings}
              onAction={runAction}
              onApiKey={setApiKey}
              onDeleteApiKey={deleteApiKey}
              onInstallAi={installAiModel}
              onSaveAi={saveAiSettings}
              onSaveApiKey={saveApiKey}
            />
          )}

          {tab === "history" && (
            <History
              filteredHistory={filteredHistory}
              filter={filter}
              selected={selected}
              selectedId={selectedId}
              onCopy={copyText}
              onFilter={setFilter}
              onSelect={setSelectedId}
            />
          )}

          {tab === "analysis" && (
            <Analysis historyCount={snapshot.historyCount || history.length} />
          )}

          {tab === "install" && <Install />}
        </section>
      </section>

      {toast && <div className="toast">{toast}</div>}
    </main>
  );
}

function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div>
        <h2>Speech</h2>
        <p>soft local voice</p>
      </div>
    </div>
  );
}

function StatusPill({ running, modelState }: { running: boolean; modelState: string }) {
  const loading = running && modelState === "loading";
  return (
    <div className={loading ? "status-pill loading" : running ? "status-pill running" : "status-pill"}>
      <span />
      {loading ? "Loading" : running ? "Running" : "Off"}
    </div>
  );
}

function Overview({
  snapshot,
  statusText,
  latest,
  onCopyLatest,
}: {
  snapshot: AppSnapshot;
  statusText: string;
  latest?: HistoryItem;
  onCopyLatest: () => void;
}) {
  return (
    <div className="overview-grid">
      <article className="hero-card lifted">
        <div className="hero-copy">
          <p className="eyebrow">Push-to-talk</p>
          <h3>Hold, speak, release.</h3>
          <p>
            Speech keeps dictation local, then sends the transcript to your active
            input, clipboard, and searchable history.
          </p>
          <div className="hero-actions">
            <kbd>Ctrl</kbd>
            <kbd>Win</kbd>
            <span>Windows</span>
            <kbd>Control</kbd>
            <kbd>Command</kbd>
            <span>macOS</span>
          </div>
        </div>
        <WavePreview />
      </article>

      <section className="stat-grid">
        <Metric title="Runtime" value={statusText} detail={snapshot.speechRoot} />
        <Metric
          title="Model"
          value={snapshot.modelRuntimeState === "loading" ? "Loading" : snapshot.modelSizeLabel}
          detail={
            snapshot.modelRuntimeState === "loading"
              ? "Starting Parakeet"
              : snapshot.modelSnapshot || "Install Parakeet"
          }
        />
        <Metric title="History" value={String(snapshot.historyCount)} detail="local transcripts" />
        <Metric title="Device" value="CPU" detail="stable default" />
        <Metric
          title="AI cleanup"
          value={snapshot.aiMode === "off" ? "Off" : snapshot.aiMode === "local" ? "Local" : "API"}
          detail={snapshot.aiMode === "local" ? `${snapshot.aiModelSizeLabel} · ${snapshot.aiRuntimeState}` : "conservative correction"}
        />
      </section>

      <article className="note-card latest-note">
        <div>
          <p className="eyebrow">Latest transcript</p>
          <p>{latest?.text || "No transcript yet. Hold the default hotkey and say something."}</p>
        </div>
        <button className="ghost-button" onClick={onCopyLatest} disabled={!latest}>
          Copy
        </button>
      </article>
    </div>
  );
}

function Controls({
  aiSettings,
  apiKey,
  busy,
  log,
  snapshot,
  onAction,
  onAiSettings,
  onApiKey,
  onDeleteApiKey,
  onInstallAi,
  onSaveAi,
  onSaveApiKey,
}: {
  aiSettings: AiSettings;
  apiKey: string;
  busy: boolean;
  log: string;
  snapshot: AppSnapshot;
  onAction: (command: ActionCommand) => void;
  onAiSettings: (settings: AiSettings) => void;
  onApiKey: (value: string) => void;
  onDeleteApiKey: () => void;
  onInstallAi: () => void;
  onSaveAi: () => void;
  onSaveApiKey: () => void;
}) {
  return (
    <div className="controls-layout">
      <article className="control-hero lifted">
        <div>
          <p className="eyebrow">Engine</p>
          <h3>Python bridge, Tauri face.</h3>
          <p>
            The background engine stays proven and local. This window is the smoother
            control surface for status, diagnostics, restarts, and history.
          </p>
        </div>
        <StatusPill
          running={snapshot.running}
          modelState={snapshot.modelRuntimeState || "unknown"}
        />
      </article>

      <section className="control-grid">
        <RuntimeCard
          title="Runtime actions"
          detail="Use these when the tray needs a nudge."
          actions={[
            ["Status", "speech_status"],
            ["Diagnose", "speech_diagnose"],
            ["Restart", "speech_restart"],
            ["Stop", "speech_stop"],
          ]}
          busy={busy}
          onAction={onAction}
        />

        <article className="soft-panel">
          <p className="eyebrow">Mode</p>
          <h4>Dictation profile</h4>
          <div className="segmented readonly" aria-label="Runtime mode">
            <span className="active">CPU</span>
            <span>CUDA</span>
            <span>Auto</span>
          </div>
          <p className="panel-copy">
            CPU stays the stable default. CUDA and NeMo controls can become live
            settings in the next settings bridge.
          </p>
        </article>

        <article className="soft-panel">
          <p className="eyebrow">Output</p>
          <h4>Where text goes</h4>
          <div className="route-list">
            <Route label="Active input" active />
            <Route label="Clipboard" active />
            <Route label="History" active />
          </div>
        </article>

        <article className="soft-panel ai-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI cleanup</p>
              <h4>Transcript polish</h4>
            </div>
            <span className={`mini-status ${aiSettings.aiMode}`}>{aiSettings.aiMode}</span>
          </div>
          <div className="segmented interactive" aria-label="AI cleanup mode">
            {(["off", "local", "api"] as const).map((mode) => (
              <button
                key={mode}
                className={aiSettings.aiMode === mode ? "active" : ""}
                onClick={() => onAiSettings({ ...aiSettings, aiMode: mode })}
              >
                {mode === "off" ? "Off" : mode === "local" ? "Local" : "API"}
              </button>
            ))}
          </div>

          {aiSettings.aiMode === "local" && (
            <div className="ai-config">
              <div className="model-line">
                <div>
                  <strong>SAGE 95M</strong>
                  <span>{snapshot.aiModelInstalled ? `${snapshot.aiModelSizeLabel} · ${snapshot.aiRuntimeState}` : "Not installed"}</span>
                </div>
                <button className="ghost-button" disabled={busy || snapshot.aiModelInstalled} onClick={onInstallAi}>
                  {snapshot.aiModelInstalled ? (snapshot.aiRuntimeState === "loaded" ? "Loaded" : "Ready") : "Download"}
                </button>
              </div>
              <p className="panel-copy">Russian spelling, punctuation, and casing on CPU.</p>
            </div>
          )}

          {aiSettings.aiMode === "api" && (
            <div className="ai-config form-stack">
              <label>
                <span>Base URL</span>
                <input
                  value={aiSettings.aiApiBaseUrl}
                  onChange={(event) => onAiSettings({ ...aiSettings, aiApiBaseUrl: event.target.value })}
                />
              </label>
              <label>
                <span>Model</span>
                <input
                  value={aiSettings.aiApiModel}
                  onChange={(event) => onAiSettings({ ...aiSettings, aiApiModel: event.target.value })}
                  placeholder="provider model name"
                />
              </label>
              <label>
                <span>API key</span>
                <div className="secret-row">
                  <input type="password" value={apiKey} onChange={(event) => onApiKey(event.target.value)} placeholder="stored in system keychain" />
                  <button className="ghost-button" disabled={busy || !apiKey.trim()} onClick={onSaveApiKey}>Save key</button>
                </div>
              </label>
              <button className="text-button" disabled={busy} onClick={onDeleteApiKey}>Remove saved key</button>
              <p className="privacy-note">API mode sends transcript text to this endpoint.</p>
            </div>
          )}

          <button className="primary-button full-button" disabled={busy} onClick={onSaveAi}>
            Save and restart
          </button>
        </article>
      </section>

      <pre className="log-output">{log || "Command output will appear here."}</pre>
    </div>
  );
}

function RuntimeCard({
  title,
  detail,
  actions,
  busy,
  onAction,
}: {
  title: string;
  detail: string;
  actions: Array<[string, ActionCommand]>;
  busy: boolean;
  onAction: (command: ActionCommand) => void;
}) {
  return (
    <article className="soft-panel action-panel">
      <p className="eyebrow">Control</p>
      <h4>{title}</h4>
      <p className="panel-copy">{detail}</p>
      <div className="button-row">
        {actions.map(([label, command]) => (
          <button
            key={command}
            className={command === "speech_stop" ? "danger-button" : ""}
            disabled={busy}
            onClick={() => onAction(command)}
          >
            {label}
          </button>
        ))}
      </div>
    </article>
  );
}

function Route({ label, active }: { label: string; active: boolean }) {
  return (
    <div className={active ? "route active" : "route"}>
      <span />
      {label}
    </div>
  );
}

function History({
  filteredHistory,
  filter,
  selected,
  selectedId,
  onCopy,
  onFilter,
  onSelect,
}: {
  filteredHistory: HistoryItem[];
  filter: string;
  selected?: HistoryItem;
  selectedId: string;
  onCopy: (text: string) => void;
  onFilter: (value: string) => void;
  onSelect: (id: string) => void;
}) {
  const [showOriginal, setShowOriginal] = useState(false);
  const selectedText = showOriginal ? selected?.originalText : selected?.text;
  return (
    <div className="history-layout">
      <header className="history-header">
        <div>
          <p className="eyebrow">History</p>
          <h3>{filteredHistory.length} shown</h3>
        </div>
        <input
          value={filter}
          onChange={(event) => onFilter(event.target.value)}
          placeholder="Search transcripts"
        />
      </header>

      <section className="history-body">
        <div className="history-feed" aria-label="Transcript history">
          {filteredHistory.length === 0 && (
            <div className="empty">No matching transcripts.</div>
          )}
          {filteredHistory.map((item) => (
            <button
              className={item.id === selectedId ? "history-row selected" : "history-row"}
              key={item.id}
              onClick={() => onSelect(item.id)}
            >
              <time>{formatTime(item.createdAt)}</time>
              <span>{item.text}</span>
            </button>
          ))}
        </div>

        <article className="reader-card lifted">
          <div>
            <div className="reader-heading">
              <div>
                <p className="eyebrow">Selected transcript</p>
                {selected && <span className={`history-state ${selected.processingStatus}`}>{selected.processingMode} · {selected.processingStatus} · {selected.processingMs} ms</span>}
              </div>
              {selected && selected.originalText !== selected.text && (
                <div className="segmented compact">
                  <button className={!showOriginal ? "active" : ""} onClick={() => setShowOriginal(false)}>Clean</button>
                  <button className={showOriginal ? "active" : ""} onClick={() => setShowOriginal(true)}>Original</button>
                </div>
              )}
            </div>
            <p>{selectedText || "Choose a transcript from the left."}</p>
          </div>
          <button className="ghost-button" onClick={() => selectedText && onCopy(selectedText)} disabled={!selected}>
            Copy
          </button>
        </article>
      </section>
    </div>
  );
}

function Analysis({ historyCount }: { historyCount: number }) {
  return (
    <div className="analysis-layout">
      <article className="analysis-card lifted">
        <div>
          <p className="eyebrow">Future idea</p>
          <h3>Personality analysis, later.</h3>
          <p>
            A future API connector could read selected transcripts and generate a
            playful profile: thinking style, mood patterns, detective mode, writing
            habits, and little observations about how you speak.
          </p>
        </div>
        <div className="analysis-badge">
          <span>API</span>
          <strong>soon</strong>
        </div>
      </article>

      <section className="analysis-steps">
        <article>
          <span>1</span>
          <h4>Connect provider</h4>
          <p>DeepSeek, OpenAI, local model, or another API key.</p>
        </article>
        <article>
          <span>2</span>
          <h4>Select source</h4>
          <p>Use recent history, pinned transcripts, or a custom range.</p>
        </article>
        <article>
          <span>3</span>
          <h4>Generate profile</h4>
          <p>Produce a fun private report. Current local rows: {historyCount}.</p>
        </article>
      </section>
    </div>
  );
}

function Install() {
  return (
    <div className="install-layout">
      <article className="install-hero lifted">
        <p className="eyebrow">Setup</p>
        <h3>Clean GitHub install.</h3>
        <p>
          The repo ships source and docs. Models, virtualenvs, cache, and transcripts
          stay local on each machine.
        </p>
      </article>

      <CommandCard
        title="Install on Windows"
        command={'powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1 | iex"'}
      />
      <CommandCard
        title="Install on macOS"
        command={'/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/TheRofli/speech/main/bootstrap.sh)"'}
      />
      <CommandCard title="Download Parakeet" command="speech parakeet install" />
      <CommandCard title="Open this UI" command="speech open" />

      <article className="soft-panel">
        <p className="eyebrow">Requirements</p>
        <h4>Comfortable setup</h4>
        <p className="panel-copy">
          Windows 11 or macOS 13+, microphone, 8 GB RAM minimum, 16 GB+
          recommended, and 10-20 GB free disk space. CPU is the stable default.
        </p>
      </article>
    </div>
  );
}

function CommandCard({ title, command }: { title: string; command: string }) {
  return (
    <article className="command-card">
      <p className="eyebrow">{title}</p>
      <code>{command}</code>
    </article>
  );
}

function Metric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <p className="eyebrow">{title}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}

function WavePreview() {
  return (
    <div className="wave-preview" aria-hidden="true">
      {[14, 26, 38, 24, 16, 30, 20].map((height, index) => (
        <span key={index} style={{ "--bar-height": `${height}px` } as React.CSSProperties} />
      ))}
    </div>
  );
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || "local";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortHash(value: string) {
  return value.length > 10 ? `${value.slice(0, 10)}...` : value;
}

function getStatusText(running: boolean, modelState: string) {
  if (!running) {
    return "Stopped";
  }
  if (modelState === "loading") {
    return "Loading Parakeet";
  }
  if (modelState === "loaded") {
    return "Ready";
  }
  if (modelState === "error") {
    return "Needs attention";
  }
  return "Running";
}

function getInitialTab(): Tab {
  const hash = window.location.hash.replace("#", "");
  return tabs.some((item) => item.id === hash) ? (hash as Tab) : "overview";
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
