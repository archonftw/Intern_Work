// =========================
// Global Application State
// =========================

export let cachedEvents = [];
export let cachedDevices = [];

export let domainChart = null;
export let trendChart = null;
export let modalChart = null;

export let chartInitialized = false;

export let currentView = "overview";

export let explorerSort = {
    key: "receivedAt",
    dir: "desc"
};

export let ackedAlarms = new Set(
    JSON.parse(localStorage.getItem("vesAckedAlarms") || "[]")
);

export let toastedEventIds = new Set();

export let firstLoad = true;

export let selectedAnalyticsDevice = null;

export let selectedMetrics = new Set([
    "CPU_Usage",
    "Memory_Usage"
]);

export const ALL_METRICS = [
    "CPU_Usage",
    "Memory_Usage",
    "Connected_UEs",
    "Throughput_Mbps"
];

export const VIEW_META = {
    overview: {
        title: "Overview",
        subtitle: "Live network event summary"
    },

    alarms: {
        title: "Alarms",
        subtitle: "Correlated fault & threshold conditions"
    },

    devices: {
        title: "Devices",
        subtitle: "All reporting network functions"
    },

    analytics: {
        title: "Analytics",
        subtitle: "Per-device KPI trends over time"
    },

    explorer: {
        title: "Event Explorer",
        subtitle: "Raw event stream, searchable & sortable"
    },

    system: {
        title: "System Health",
        subtitle: "Collector pipeline diagnostics"
    }
};