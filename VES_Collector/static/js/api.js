export function setConnStatus(up) {
    const el = document.getElementById("connStatus");

    if (up) {
        el.textContent = "CONNECTED";
        el.classList.remove("down");
    } else {
        el.textContent = "DISCONNECTED";
        el.classList.add("down");
    }
}

export async function safeFetch(url) {
    try {
        const res = await fetch(url);

        if (!res.ok) {
            throw new Error("HTTP " + res.status);
        }

        setConnStatus(true);

        return await res.json();

    } catch (err) {
        setConnStatus(false);
        throw err;
    }
}