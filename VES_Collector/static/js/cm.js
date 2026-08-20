import { safeFetch } from './api.js';

function el(id){ return document.getElementById(id); }

async function loadSessions(){
    try{
        const data = await safeFetch('/api/cm/sessions');
        const sel = el('cmDeviceSelect');
        sel.innerHTML = '';
        const devices = data.connected_devices || [];
        if(devices.length === 0){
            sel.innerHTML = '<option value="">No Session Active</option>';
            el('cmStatus').textContent = 'Disconnected';
            return null;
        }

        el('cmStatus').textContent = 'Connected';
        sel.innerHTML = devices.map(d => `<option value="${d}">${d}</option>`).join('');
        return devices[0];
    }catch(e){
        console.warn('loadSessions failed', e);
        el('cmStatus').textContent = 'Disconnected';
        return null;
    }
}

async function loadModules(device_id){
    if(!device_id) return;
    try{
        const modules = await safeFetch(`/api/cm/modules?device_id=${encodeURIComponent(device_id)}`);
        // modules is expected as array
        const list = Array.isArray(modules) ? modules : (modules.modules || modules);
        const select = el('cmModuleSelect');
        const container = el('cmModuleList');
        select.innerHTML = '<option value="">All Modules (Full Config)</option>';
        container.innerHTML = '';

        if(!list || list.length === 0){
            container.innerHTML = '<div style="padding:1rem;text-align:center;color:var(--text-muted);">No modules found for this device.</div>';
            el('cmModuleCount').textContent = '0 Loaded';
            return;
        }

        const unique = [];
        const seen = new Set();
        for(const m of list){
            const name = m.name || m.module || m.identifier || '';
            if(!name || seen.has(name)) continue;
            seen.add(name);
            unique.push(m);
        }

        el('cmModuleCount').textContent = `${unique.length} Loaded`;

        select.innerHTML += unique.map(m=>{
            const nm = m.name || m.module || '';
            const rev = m.revision || m.rev || '';
            return `<option value="${nm}">${nm}${rev? ' @ '+rev: ''}</option>`;
        }).join('');

        container.innerHTML = unique.map(m=>{
            const nm = m.name || m.module || '';
            const rev = m.revision || m.rev || '';
            return `<div class="cm-module-card" data-module="${nm}">
                <div class="cm-module-info">
                  <div class="cm-module-name">${nm}</div>
                  <div class="cm-module-meta">${rev}</div>
                </div>
                <button class="cm-pin-btn" data-module="${nm}">Pin</button>
            </div>`;
        }).join('');

        // attach click handlers for module cards
        container.querySelectorAll('.cm-module-card').forEach(card=>{
            card.addEventListener('click', async (ev)=>{
                const m = card.getAttribute('data-module');
                el('cmModuleSelect').value = m;
                await getConfigFor(device_id, m, el('cmDatastore').value);
            });
        });

    }catch(err){
        console.warn('loadModules failed', err);
    }
}

async function getConfigFor(device_id, module, datastore='running'){
    if(!device_id) return;
    try{
        const qs = new URLSearchParams({device_id, datastore});
        if(module) qs.set('module', module);
        const res = await safeFetch(`/api/cm/config?${qs.toString()}`);
        const xml = res.config || res || '';
        // display XML in editor
        const tree = el('cmTreeContainer');
        const ta = el('cmConfigOutput');
        ta.value = xml.trim();
        tree.textContent = xml.trim();
        // show tree by default
        tree.style.display = '';
        ta.style.display = 'none';
        el('cmEditorStatePill').textContent = 'Read-Only';
    }catch(e){
        console.warn('getConfigFor failed', e);
    }
}

async function postAction(path, body){
    try{
        const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        if(!res.ok) throw new Error('HTTP '+res.status);
        return await res.json();
    }catch(e){
        console.warn('postAction failed', e);
        throw e;
    }
}

export async function initCM(){
    const deviceSelect = el('cmDeviceSelect');
    const moduleSelect = el('cmModuleSelect');

    async function refreshAll(){
        const d = await loadSessions();
        if(d) await loadModules(d);
    }

    // initial load
    await refreshAll();

    // wire UI
    el('cmRefreshBtn')?.addEventListener('click', async ()=>{ await refreshAll(); });
    el('cmGetConfigBtn')?.addEventListener('click', async ()=>{
        const did = deviceSelect.value;
        const module = moduleSelect.value;
        const ds = el('cmDatastore').value;
        await getConfigFor(did, module, ds);
    });

    el('cmDeviceSelect')?.addEventListener('change', async (e)=>{
        const did = e.target.value;
        await loadModules(did);
    });

    el('cmModuleSelect')?.addEventListener('change', async (e)=>{
        const did = deviceSelect.value;
        const m = e.target.value;
        await getConfigFor(did, m, el('cmDatastore').value);
    });

    el('cmToggleRawModeBtn')?.addEventListener('click', ()=>{
        el('cmTreeContainer').style.display = 'none';
        el('cmConfigOutput').style.display = '';
    });
    el('cmToggleTreeModeBtn')?.addEventListener('click', ()=>{
        el('cmConfigOutput').style.display = 'none';
        el('cmTreeContainer').style.display = '';
    });

    el('cmCommitBtn')?.addEventListener('click', async ()=>{
        const did = deviceSelect.value;
        if(!did) return alert('No device selected');
        const res = await postAction('/api/cm/commit', {device_id: did});
        alert(JSON.stringify(res));
    });

    el('cmDiscardBtn')?.addEventListener('click', async ()=>{
        const did = deviceSelect.value;
        if(!did) return alert('No device selected');
        const res = await postAction('/api/cm/discard', {device_id: did});
        alert(JSON.stringify(res));
    });

    el('cmValidateBtn')?.addEventListener('click', async ()=>{
        const did = deviceSelect.value;
        const ds = el('cmDatastore').value || 'candidate';
        if(!did) return alert('No device selected');
        const res = await postAction('/api/cm/validate', {device_id: did, datastore: ds});
        alert(JSON.stringify(res));
    });

    el('cmSaveConfigBtn')?.addEventListener('click', async ()=>{
        const did = deviceSelect.value;
        const ds = el('cmDatastore').value || 'candidate';
        const cfg = el('cmConfigOutput').value;
        if(!did) return alert('No device selected');
        if(!cfg) return alert('No config to apply');
        const res = await postAction('/api/cm/config', {device_id: did, datastore: ds, config: cfg});
        alert(JSON.stringify(res));
    });
}

// Auto-init when module imported (app.js will call initCM explicitly)
export default initCM;
