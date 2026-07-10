export function timeAgo(iso) {
    if (!iso) return "never";

    const diff = (Date.now() - new Date(iso).getTime()) / 1000;

    if (diff < 5) return "just now";
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;

    return `${Math.floor(diff / 3600)}h ago`;
}

export function liveState(lastSeen) {
    if (!lastSeen)
        return {
            cls: "stale",
            label: "OFFLINE",
            signal: 1
        };

    const diff = (Date.now() - new Date(lastSeen).getTime()) / 1000;

    if (diff < 30)
        return {
            cls: "live",
            label: "LIVE",
            signal: 4
        };

    if (diff < 120)
        return {
            cls: "idle",
            label: "IDLE",
            signal: 2
        };

    return {
        cls: "stale",
        label: "STALE",
        signal: 1
    };
}

export function severityRank(sev) {
    return {
        CRITICAL: 3,
        MAJOR: 2,
        WARNING: 1,
        CLEARED: 0
    }[sev] ?? 0;
}