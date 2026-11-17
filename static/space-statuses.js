const spaceGrid = document.querySelector("[data-space-statuses]");
const summaries = Array.from(spaceGrid.querySelectorAll("[data-space-id]"));
const message = document.querySelector("#space-update-message");
const refreshInterval = 5000;

async function refreshSpaceStatuses() {
  if (!document.hidden) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), refreshInterval);
    try {
      const response = await fetch(spaceGrid.dataset.spaceStatuses, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("Space statuses unavailable");
      const statuses = await response.json();
      for (const summary of summaries) {
        const report = statuses[summary.dataset.spaceId];
        const label = report ? `${report.crowd} · ${report.noise}` : "No reports yet";
        const timing = report ? `Reported ${report.age.toLowerCase()}` : "Current conditions unknown";
        const detail = report?.stale ? `${timing} · May be outdated` : timing;
        const heading = summary.querySelector("strong");
        const note = summary.querySelector("span");
        if (heading.textContent !== label) heading.textContent = label;
        if (note.textContent !== detail) note.textContent = detail;
        summary.toggleAttribute("data-stale", Boolean(report?.stale));
      }
      message.hidden = true;
    } catch {
      if (message.hidden) {
        message.textContent = "Live reports unavailable. Retrying automatically.";
        message.hidden = false;
      }
    } finally {
      window.clearTimeout(timeout);
    }
  }
  window.setTimeout(refreshSpaceStatuses, refreshInterval);
}

refreshSpaceStatuses();
