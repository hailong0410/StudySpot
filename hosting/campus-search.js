const filters = new URLSearchParams(window.location.search);
const query = (filters.get("q") || "").trim().slice(0, 120);
const study = filters.get("study") || "";
const atmosphere = filters.get("atmosphere") || "";
document.querySelector("#q").value = query;
document.querySelector("#study").value = study;
document.querySelector("#atmosphere").value = atmosphere;

let count = 0;
for (const space of document.querySelectorAll(".space")) {
  const nameMatches = space.querySelector("h2").textContent.toLowerCase().includes(query.toLowerCase());
  const styleMatches = !study || study === space.dataset.study || space.dataset.study === "both";
  const atmosphereMatches = !atmosphere || atmosphere === space.dataset.atmosphere;
  space.hidden = !(nameMatches && styleMatches && atmosphereMatches);
  count += Number(!space.hidden);
}

document.querySelector(".count strong").textContent = String(count);
if (!count) {
  const message = document.createElement("p");
  message.className = "empty";
  message.textContent = "No matching spaces. Clear the filters to see all spaces.";
  document.querySelector(".spaces").append(message);
}
