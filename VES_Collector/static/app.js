async function loadEvents() {
    const res = await fetch("/api/events");
    const data = await res.json();

    const table = document.getElementById("events");
    table.innerHTML = "";

    data.reverse().forEach(event => {

        const severity = (event.priority || "normal").toLowerCase();

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <span class="badge ${event.domain}">
                    ${event.domain}
                </span>
            </td>

            <td>${event.eventId || "-"}</td>

            <td>${event.eventName || "-"}</td>

            <td>${event.sourceName || "-"}</td>

            <td class="${severity}">
                ${event.priority || "-"}
            </td>

            <td>${event.receivedAt || "-"}</td>
        `;

        table.appendChild(row);
    });
}

loadEvents();
setInterval(loadEvents, 2000);

loadEvents();
setInterval(loadEvents, 2000); // refresh every 2 seconds