// UI related helpers

function showPanel(panelId) {
    const panels = document.querySelectorAll(".view-panel");

    panels.forEach(panel => {
        panel.style.display = "none";
    });

    const target = document.getElementById(panelId);

    if (target) {
        target.style.display = "block";
    }
}


function setActiveTab(tabElement) {

    const tabs = document.querySelectorAll(".nav-tab");

    tabs.forEach(tab => {
        tab.classList.remove("active");
    });

    if (tabElement) {
        tabElement.classList.add("active");
    }
}


function updateText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function clearElement(id) {

    const element = document.getElementById(id);

    if (element) {
        element.innerHTML = "";
    }
}


function toggleElement(id, visible) {

    const element = document.getElementById(id);

    if (!element) return;

    element.style.display = visible ? "" : "none";
}


function createBadge(text, type="default") {

    const span = document.createElement("span");

    span.className = `badge ${type}`;
    span.textContent = text;

    return span;
}