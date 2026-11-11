const panel = document.querySelector("[data-live-observations]");
const statusMessage = document.querySelector("#live-status");
const interval = 5000;
const liveText = "Checks for new community reports every 5 seconds while this tab is active.";

function showStatus(message) {
  if (statusMessage.textContent !== message) {
    statusMessage.textContent = message;
  }
}

async function refreshObservations() {
  if (!document.hidden) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), interval);
    try {
      const response = await fetch(panel.dataset.liveObservations, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error("Live observation request failed");
      }

      const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
      const next = parsed.querySelector("#observations");
      if (!next) {
        throw new Error("Live observation response was incomplete");
      }

      const current = panel.firstElementChild;
      if (!current.isEqualNode(next)) {
        current.replaceWith(next);
      }
      showStatus(liveText);
    } catch {
      showStatus("Live updates unavailable. Showing the last loaded report data. Retrying automatically.");
    } finally {
      window.clearTimeout(timeout);
    }
  }
  window.setTimeout(refreshObservations, interval);
}

statusMessage.hidden = false;
showStatus(liveText);
window.setTimeout(refreshObservations, interval);
