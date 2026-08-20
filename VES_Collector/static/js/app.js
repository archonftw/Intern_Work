import * as State from "./state.js";
import { safeFetch } from "./api.js";
import { timeAgo, liveState, severityRank } from "./utils.js";
import initCM from "./cm.js";

window.safeFetch = safeFetch;
window.timeAgo = timeAgo;
window.liveState = liveState;
window.severityRank = severityRank;

console.log("Modules loaded.");

// Initialize CM UI integration
initCM().catch(err=>{ console.warn('CM init failed', err); });