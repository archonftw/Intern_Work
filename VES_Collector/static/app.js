async function loadEvents() {
    const res = await fetch("/api/events");
    const data = await res.json();

    const table = document.getElementById("events");
    table.innerHTML = "";

    data.reverse().forEach(event => {
        const row = document.createElement("tr");

        const severity = event.priority?.toLowerCase();

        row.innerHTML = `
            <td>${event.domain}</td>
            <td>${event.eventId}</td>
            <td>${event.eventName}</td>
            <td>${event.sourceName}</td>
            <td class="${severity}">${event.priority}</td>
            <td>${event.receivedAt}</td>
        `;

        table.appendChild(row);
    });
}

loadEvents();
setInterval(loadEvents, 2000); // refresh every 2 seconds