// Safe GitHub webhook transform
// Filters self-triggers and constructs a controlled summary to avoid prompt injection.
//
// Expects payload format from OpenClaw's GitHub preset.
// Returns null to drop event, or an agent action object.

export function transformGitHub(payload, ctx) {
  // Extract sender from various possible nesting locations
  const sender = payload?.sender?.login ?? payload?.payload?.sender?.login;
  const senderType = payload?.sender?.type ?? payload?.payload?.sender?.type;

  // Drop events from this agent to avoid loops
  if (sender === "DockeGumi" || senderType === "Bot") {
    return null;
  }

  // Extract core fields
  const repo = payload?.payload?.repository?.full_name ?? payload?.repository?.full_name ?? "unknown-repo";
  const eventName = payload?.eventName ?? payload?.event ?? "unknown-event";
  const action = payload?.payload?.action ?? payload?.action ?? "";

  // Pull issue/PR/comment info if present
  const issue = payload?.payload?.issue;
  const pr = payload?.payload?.pull_request;
  const comment = payload?.payload?.comment;
  const body = comment?.body ?? payload?.payload?.body ?? "";

  // Build a controlled plain-text summary (no raw markdown/HTML)
  const parts = [`GitHub ${eventName} on ${repo}`];
  if (action) parts.push(`Action: ${action}`);
  if (issue) parts.push(`Issue #${issue.number}: ${issue.title}`);
  if (pr) parts.push(`PR #${pr.number}: ${pr.title}`);
  if (body) {
    // Truncate and sanitize comment excerpt
    const excerpt = body.replace(/\n/g, " ").trim();
    const safeExcerpt = excerpt.length > 200 ? excerpt.slice(0, 200) + "..." : excerpt;
    parts.push(`Comment: ${safeExcerpt}`);
  }

  const summary = parts.join("\n");

  return {
    action: "agent",
    name: "GitHub",
    wakeMode: "now",
    deliver: true,
    channel: "last",
    sessionKey: `hook:github:${repo}`,
    message: summary
  };
}
