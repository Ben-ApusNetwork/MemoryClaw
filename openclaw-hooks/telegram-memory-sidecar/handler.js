const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const { promisify } = require("node:util");
const { execFile } = require("node:child_process");
const { createHash } = require("node:crypto");

const execFileAsync = promisify(execFile);
const HOOK_DIR = __dirname;
const HOOK_STATE_DIR = path.join(HOOK_DIR, "state");
const PENDING_PATH = path.join(HOOK_STATE_DIR, "pending.json");
const META_PATH = path.join(HOOK_STATE_DIR, "meta.json");
const EVENTS_LOG_PATH = path.join(HOOK_STATE_DIR, "events.log");
const OPENCLAW_CONFIG_PATH = path.join(os.homedir(), ".openclaw", "openclaw.json");
const INBOUND_MEDIA_DIR = path.join(os.homedir(), ".openclaw", "media", "inbound");
const SKILL_DIR = path.join(os.homedir(), ".openclaw", "skills", "openclaw-memoryloop-demo");
const OBSERVER_SCRIPT = path.join(SKILL_DIR, "scripts", "instant_memory_feedback.py");
const VISION_SCRIPT = path.join(SKILL_DIR, "scripts", "vision_caption.py");
const OBSERVER_STATE = path.join(SKILL_DIR, "state", "live_demo.json");
const SIDECAR_MARKER = "SOURCE_ACCEPTED=";
const MEMORY_COMMAND_PATTERN = /^\/memory(?:@\w+)?(?:\s+.*)?$/i;

function isTelegramEvent(event) {
  return event?.type === "message" && event?.context?.channelId === "telegram";
}

function isSidecarContent(text) {
  const trimmed = String(text || "").trim();
  return trimmed.startsWith(SIDECAR_MARKER) || trimmed.includes(`\n${SIDECAR_MARKER}`);
}

function pendingKeyFor(event) {
  const context = event?.context || {};
  const sessionKey = String(event?.sessionKey || "").trim();
  if (sessionKey) return `session:${sessionKey}`;

  const conversationId = String(context.conversationId || context.groupId || "").trim();
  if (conversationId) return `conversation:${context.channelId || "unknown"}:${conversationId}`;

  const peerId = String(context.from || context.to || context.senderId || "").trim();
  if (peerId) return `peer:${context.channelId || "unknown"}:${peerId}`;

  return `message:${context.channelId || "unknown"}:${context.messageId || "unknown"}`;
}

function cleanupTelegramEnvelope(text) {
  const raw = String(text || "").trim();
  if (!raw) return "";
  return raw.replace(/^\[[^\]]+\]\s*/u, "").trim();
}

function isImagePlaceholder(text) {
  const normalized = String(text || "").trim().toLowerCase();
  return normalized === "<media:image>" || normalized === "[image]" || normalized === "<image>";
}

function inboundTextFromContext(context) {
  const preferred = context?.bodyForAgent || context?.transcript || context?.body || context?.content || "";
  return cleanupTelegramEnvelope(preferred);
}

function isMemoryCommand(text) {
  return MEMORY_COMMAND_PATTERN.test(String(text || "").trim());
}

function titleFromText(text) {
  const singleLine = String(text || "").replace(/\s+/g, " ").trim();
  if (!singleLine) return "interaction";
  return singleLine.slice(0, 48);
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object") return [value];
  return [];
}

function candidateImageRef(entry, fallbackKind = "") {
  if (!entry || typeof entry !== "object") return null;
  const pathValue = entry.localPath || entry.filePath || entry.path || entry.downloadedPath || "";
  if (typeof pathValue === "string" && pathValue.trim()) {
    return { kind: "path", value: pathValue.trim() };
  }

  const urlValue = entry.url || entry.downloadUrl || entry.fileUrl || entry.href || "";
  if (typeof urlValue === "string" && urlValue.trim()) {
    return { kind: "url", value: urlValue.trim() };
  }

  const fileId = entry.file_id || entry.fileId || "";
  if (typeof fileId === "string" && fileId.trim() && (fallbackKind === "photo" || String(entry.mime_type || entry.mimeType || "").startsWith("image/"))) {
    return { kind: "telegram-file-id", value: fileId.trim() };
  }

  return null;
}

function extractImageReference(context) {
  const pools = [
    { value: context?.attachments, kind: "" },
    { value: context?.files, kind: "" },
    { value: context?.media, kind: "" },
    { value: context?.image, kind: "photo" },
    { value: context?.images, kind: "photo" },
    { value: context?.photo, kind: "photo" },
    { value: context?.photos, kind: "photo" },
    { value: context?.telegram?.message?.photo, kind: "photo" },
    { value: context?.telegram?.message?.document, kind: "" },
    { value: context?.raw?.message?.photo, kind: "photo" },
    { value: context?.raw?.message?.document, kind: "" },
  ];

  for (const pool of pools) {
    for (const entry of asArray(pool.value)) {
      const ref = candidateImageRef(entry, pool.kind);
      if (ref) return ref;
    }
  }

  return null;
}

async function ensureStateDir() {
  await fs.mkdir(HOOK_STATE_DIR, { recursive: true });
}

async function readJson(pathname, fallback) {
  try {
    return JSON.parse(await fs.readFile(pathname, "utf-8"));
  } catch {
    return fallback;
  }
}

async function writeJson(pathname, value) {
  await ensureStateDir();
  await fs.writeFile(pathname, JSON.stringify(value, null, 2), "utf-8");
}

async function appendEventLog(kind, details) {
  await ensureStateDir();
  const line = `${new Date().toISOString()} ${kind} ${JSON.stringify(details)}\n`;
  await fs.appendFile(EVENTS_LOG_PATH, line, "utf-8");
}

async function findRecentInboundImage(recordedAt) {
  let entries;
  try {
    entries = await fs.readdir(INBOUND_MEDIA_DIR, { withFileTypes: true });
  } catch {
    return "";
  }

  const referenceMs = Number(recordedAt || 0) || Date.now();
  const maxAgeMs = 10 * 60 * 1000;
  const candidates = [];
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    if (!/\.(jpg|jpeg|png|webp)$/i.test(entry.name)) continue;
    const fullPath = path.join(INBOUND_MEDIA_DIR, entry.name);
    try {
      const stat = await fs.stat(fullPath);
      const delta = Math.abs(stat.mtimeMs - referenceMs);
      if (delta <= maxAgeMs) {
        candidates.push({ path: fullPath, mtimeMs: stat.mtimeMs, delta });
      }
    } catch {
      continue;
    }
  }

  candidates.sort((a, b) => {
    if (a.delta !== b.delta) return a.delta - b.delta;
    return b.mtimeMs - a.mtimeMs;
  });
  return candidates[0]?.path || "";
}

function sha1(text) {
  return createHash("sha1").update(text).digest("hex");
}

async function resolveTelegramBotToken() {
  const config = await readJson(OPENCLAW_CONFIG_PATH, {});
  const token = String(config?.channels?.telegram?.botToken || "").trim();
  if (!token) {
    throw new Error("telegram bot token missing from ~/.openclaw/openclaw.json");
  }
  return token;
}

async function resolveTelegramFileUrl(fileId) {
  const token = await resolveTelegramBotToken();
  const response = await fetch(`https://api.telegram.org/bot${token}/getFile?file_id=${encodeURIComponent(fileId)}`);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false || !payload?.result?.file_path) {
    const detail = payload?.description || payload?.error_code || response.status;
    throw new Error(`telegram getFile failed: ${detail}`);
  }
  return `https://api.telegram.org/file/bot${token}/${payload.result.file_path}`;
}

function resolveTelegramChatId(event, current) {
  const candidates = [
    event?.context?.conversationId,
    current?.conversationId,
    event?.context?.to,
    event?.context?.groupId,
  ];
  for (const value of candidates) {
    const raw = String(value || "").trim();
    if (!raw) continue;
    if (raw.startsWith("telegram:")) return raw.slice("telegram:".length);
    return raw;
  }
  return "";
}

async function sendTelegramSidecar(chatId, summary) {
  const token = await resolveTelegramBotToken();
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: summary,
      disable_web_page_preview: true,
    }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    const detail = payload?.description || payload?.error_code || response.status;
    throw new Error(`telegram sendMessage failed: ${detail}`);
  }

  return payload;
}

async function deleteTelegramMessage(chatId, messageId) {
  const token = await resolveTelegramBotToken();
  const response = await fetch(`https://api.telegram.org/bot${token}/deleteMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      message_id: Number(messageId),
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    const detail = payload?.description || payload?.error_code || response.status;
    throw new Error(`telegram deleteMessage failed: ${detail}`);
  }
}

function truncateLine(text, max = 120) {
  const single = String(text || "").replace(/\s+/g, " ").trim();
  if (single.length <= max) return single;
  return single.slice(0, max - 1) + "…";
}

async function loadMemoryState() {
  return readJson(OBSERVER_STATE, { sources: [], history: [], working_signals: [] });
}

function uniquePromotedMemories(history) {
  const promoted = [];
  const seen = new Set();
  for (const entry of history) {
    for (const item of entry?.memory_pack?.promoted_memories || []) {
      const key = String(item?.key || "");
      if (!key || seen.has(key)) continue;
      seen.add(key);
      promoted.push(item);
    }
  }
  return promoted;
}

function recentAcceptedCandidates(history, limit = 10) {
  const accepted = [];
  for (const entry of history.slice(-10)) {
    const sourceTitle = String(entry?.source?.title || "");
    for (const candidate of entry?.audited_candidates || []) {
      if (candidate?.decision !== "accepted") continue;
      accepted.push({
        key: String(candidate?.key || ""),
        source: sourceTitle,
        reason: String(candidate?.reason || ""),
      });
      if (accepted.length >= limit) return accepted;
    }
  }
  return accepted;
}

function recentImageSources(sources, limit = 5) {
  return sources.filter((item) => item?.type === "image").slice(-limit);
}

async function buildMemoryReport() {
  const data = await loadMemoryState();
  const history = Array.isArray(data?.history) ? data.history : [];
  const sources = Array.isArray(data?.sources) ? data.sources : [];
  const promoted = uniquePromotedMemories(history);
  const accepted = recentAcceptedCandidates(history, 10);
  const images = recentImageSources(sources, 5);

  const lines = [];
  lines.push("MEMORY REPORT");
  lines.push("");
  lines.push("PROMOTED");
  if (!promoted.length) {
    lines.push("(none)");
  } else {
    for (const item of promoted) {
      lines.push(`- ${item.key} [${item.category}] conf=${item.confidence} evidence=${item.evidence_count}`);
    }
  }
  lines.push("");
  lines.push("ACCEPTED (recent 10)");
  if (!accepted.length) {
    lines.push("(none)");
  } else {
    for (const item of accepted) {
      lines.push(`- ${item.key} <= ${truncateLine(item.source, 44)}`);
      lines.push(`  ${truncateLine(item.reason, 110)}`);
    }
  }
  lines.push("");
  lines.push("RECENT IMAGES (last 5)");
  if (!images.length) {
    lines.push("(none)");
  } else {
    for (const item of images) {
      lines.push(`- ${item.id}: ${truncateLine(item.title, 44)}`);
      lines.push(`  ${truncateLine(item.content, 110)}`);
    }
  }
  return lines.join("\n");
}

async function runVisionCaption(imageRef, hintText) {
  if (!imageRef?.kind || !imageRef?.value) return "";

  try {
    const args = [VISION_SCRIPT];
    if (imageRef.kind === "path") {
      args.push("--image-path", imageRef.value);
    } else if (imageRef.kind === "url") {
      args.push("--image-url", imageRef.value);
    } else if (imageRef.kind === "telegram-file-id") {
      const url = await resolveTelegramFileUrl(imageRef.value);
      args.push("--image-url", url);
    } else {
      return "";
    }

    if (hintText.trim()) {
      args.push("--hint-text", hintText.trim());
    }

    const { stdout } = await execFileAsync("python3", args, {
      cwd: SKILL_DIR,
      maxBuffer: 1024 * 1024,
    });
    return String(stdout || "").trim();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await appendEventLog("vision_failed", { reason: message, imageKind: imageRef.kind });
    return "";
  }
}

async function buildInboundObservation(context) {
  const text = inboundTextFromContext(context);
  const imageRef = extractImageReference(context);
  if (!imageRef) {
    return {
      sourceType: "interaction",
      userText: text,
      title: titleFromText(text),
    };
  }

  const visionCaption = await runVisionCaption(imageRef, text);
  const parts = [];
  if (text) parts.push(text);
  if (visionCaption) parts.push(visionCaption);
  const userText = parts.join("\n").trim() || "Uploaded image for taste memory audit.";
  const titleSeed = text || visionCaption || "image upload";

  return {
    sourceType: "image",
    userText,
    title: titleFromText(titleSeed),
  };
}

async function buildObservedSource(current, outbound) {
  const currentText = String(current?.userText || "").trim();
  if ((current?.sourceType || "") === "image") {
    return {
      sourceType: "image",
      userText: currentText,
      title: current?.title || "image upload",
    };
  }

  if (!isImagePlaceholder(currentText)) {
    return {
      sourceType: current?.sourceType || "interaction",
      userText: currentText,
      title: current?.title || "interaction",
    };
  }

  const recentImagePath = await findRecentInboundImage(current?.recordedAt);
  const visionCaption = recentImagePath
    ? await runVisionCaption({ kind: "path", value: recentImagePath }, "")
    : "";
  const answerHint = String(outbound || "").replace(/\s+/g, " ").trim();
  const derivedParts = [];
  if (visionCaption) derivedParts.push(visionCaption);
  if (answerHint) derivedParts.push(answerHint);
  const derivedText = derivedParts.join("\n").trim() || "Uploaded image for memory audit.";
  await appendEventLog("image_placeholder_resolved", {
    title: current?.title || "",
    imagePath: recentImagePath,
    usedVisionCaption: Boolean(visionCaption),
    usedAssistantHint: Boolean(answerHint),
  });
  return {
    sourceType: "image",
    userText: derivedText,
    title: current?.title && !isImagePlaceholder(current.title) ? current.title : "uploaded image",
  };
}

async function handlePreprocessed(event) {
  const inbound = await buildInboundObservation(event.context);
  const text = String(inbound.userText || "").trim();
  if (!text) return;
  const memoryCommand = inbound.sourceType === "interaction" && isMemoryCommand(text);
  if (inbound.sourceType === "interaction" && text.startsWith("/") && !memoryCommand) return;

  const pending = await readJson(PENDING_PATH, {});
  const key = pendingKeyFor(event);
  pending[key] = {
    userText: text,
    sourceType: inbound.sourceType,
    commandType: memoryCommand ? "memory" : "",
    title: inbound.title,
    recordedAt: Date.now(),
    conversationId: event?.context?.conversationId || "",
    messageId: event?.context?.messageId || "",
  };
  await writeJson(PENDING_PATH, pending);
  await appendEventLog("preprocessed", {
    key,
    conversationId: event?.context?.conversationId || "",
    messageId: event?.context?.messageId || "",
    sourceType: inbound.sourceType,
    commandType: memoryCommand ? "memory" : "",
    title: inbound.title,
  });
}

async function handleSent(event) {
  if (!event?.context?.success) return;
  const outbound = String(event?.context?.content || "").trim();
  if (!outbound) return;
  if (isSidecarContent(outbound)) return;

  const key = pendingKeyFor(event);
  const pending = await readJson(PENDING_PATH, {});
  const current = pending[key];
  if (!current?.userText) {
    await appendEventLog("sent_skipped_missing_pending", {
      key,
      conversationId: event?.context?.conversationId || "",
      messageId: event?.context?.messageId || "",
      outboundPreview: outbound.slice(0, 120),
    });
    return;
  }

  const meta = await readJson(META_PATH, {});
  const fingerprint = sha1(`${key}|${event?.context?.messageId || ""}|${outbound}`);
  if (meta[key] === fingerprint) {
    await appendEventLog("sent_skipped_duplicate", {
      key,
      conversationId: event?.context?.conversationId || "",
      messageId: event?.context?.messageId || "",
    });
    return;
  }

  try {
    let summary = "";
    if (current.commandType === "memory") {
      summary = await buildMemoryReport();
    } else {
      const observed = await buildObservedSource(current, outbound);
      const { stdout } = await execFileAsync(
        "python3",
        [
          OBSERVER_SCRIPT,
          "--state",
          OBSERVER_STATE,
          "observe",
          "--source-type",
          observed.sourceType || "interaction",
          "--user-text",
          observed.userText,
          "--assistant-text",
          outbound,
          "--title",
          observed.title || "interaction",
        ],
        {
          cwd: SKILL_DIR,
          maxBuffer: 1024 * 1024,
        },
      );
      summary = String(stdout || "").trim();
    }

    if (!summary) {
      await appendEventLog("sent_skipped_empty_summary", {
        key,
        conversationId: event?.context?.conversationId || "",
        messageId: event?.context?.messageId || "",
      });
      return;
    }

    const chatId = resolveTelegramChatId(event, current);
    if (!chatId) {
      throw new Error("telegram chat id unavailable for sidecar delivery");
    }

    const result = await sendTelegramSidecar(chatId, summary);
    if (current.commandType === "memory" && event?.context?.messageId) {
      try {
        await deleteTelegramMessage(chatId, event.context.messageId);
        await appendEventLog("memory_command_deleted_main_reply", {
          key,
          conversationId: event?.context?.conversationId || current?.conversationId || "",
          messageId: String(event.context.messageId),
        });
      } catch (deleteError) {
        const deleteMessage = deleteError instanceof Error ? deleteError.message : String(deleteError);
        await appendEventLog("memory_command_delete_failed", {
          key,
          conversationId: event?.context?.conversationId || current?.conversationId || "",
          messageId: String(event?.context?.messageId || ""),
          error: deleteMessage,
        });
      }
    }
    delete pending[key];
    meta[key] = fingerprint;
    await writeJson(PENDING_PATH, pending);
    await writeJson(META_PATH, meta);
    await appendEventLog("sent_delivered_summary", {
      key,
      conversationId: event?.context?.conversationId || current?.conversationId || "",
      messageId: String(result?.result?.message_id || ""),
      summaryPreview: summary.split("\n").slice(0, 2).join(" | "),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[telegram-memory-sidecar] observe failed: ${message}`);
    await appendEventLog("sent_failed", {
      key,
      conversationId: event?.context?.conversationId || "",
      messageId: event?.context?.messageId || "",
      error: message,
    });
  }
}

const handler = async (event) => {
  if (!isTelegramEvent(event)) return;

  if (event.action === "preprocessed") {
    await handlePreprocessed(event);
    return;
  }

  if (event.action === "sent") {
    await handleSent(event);
  }
};

module.exports = handler;
module.exports.default = handler;
