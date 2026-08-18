// ═══════════════════════════════════════════════════════
// GOOGLE DRIVE SYNC MODULE — Finanzas Personales
// Bidirectional sync with conflict detection
// ═══════════════════════════════════════════════════════

const GD_SCOPE='https://www.googleapis.com/auth/drive.file';
const SYNC_FILE='finanzas-data.json';
const SYNC_FOLDER='Finanzas';
const BACKUP_FOLDER='backups';
const SYNC_DEBOUNCE=5000;
const MAX_RETRIES=3;
const BACKUP_EVERY_N=10;
const MAX_BACKUPS=30;

let gdTokenClient=null,gdToken=null,gdTokenExpiry=0;
let syncInProgress=false,syncDebounce=null;
let syncFileId=null,syncFolderId=null;

// ═══════ CLIENT ID MANAGEMENT ═══════

const DEFAULT_GD_CLIENT_ID='965651146742-3i5s8l107rquqjfh3qbitit8s3hsji05.apps.googleusercontent.com';
function getGdClientId(){return localStorage.getItem('gd_client_id')||DEFAULT_GD_CLIENT_ID}
function setGdClientId(id){localStorage.setItem('gd_client_id',id.trim())}
function isGdConfigured(){return!!getGdClientId()}

// ═══════ AUTH ═══════

function initGoogleAuth(){
  if(!isGdConfigured()||typeof google==='undefined')return;
  try{
    gdTokenClient=google.accounts.oauth2.initTokenClient({
      client_id:getGdClientId(),
      scope:GD_SCOPE,
      callback:handleAuthResponse
    });
  }catch(e){console.warn('GIS init failed:',e)}
  const saved=localStorage.getItem('gd_token');
  const exp=parseInt(localStorage.getItem('gd_token_expiry')||'0');
  if(saved&&exp>Date.now()){gdToken=saved;gdTokenExpiry=exp;updateSyncUI()}
}

function handleAuthResponse(resp){
  if(resp.error){
    console.error('Auth error:',resp.error);
    updateSyncStatus('error','Error de autenticación');
    return;
  }
  gdToken=resp.access_token;
  gdTokenExpiry=Date.now()+(resp.expires_in*1000)-60000;
  localStorage.setItem('gd_token',gdToken);
  localStorage.setItem('gd_token_expiry',String(gdTokenExpiry));
  updateSyncUI();
  syncIfNeeded();
}

function gdSignIn(){
  if(!isGdConfigured()){openModal('gd-setup-modal');return}
  if(!gdTokenClient)initGoogleAuth();
  if(!gdTokenClient){toast('Google no cargado. Comprueba tu conexión.');return}
  gdTokenClient.requestAccessToken({prompt:''});
}

function gdSignOut(){
  if(gdToken&&typeof google!=='undefined'){
    try{google.accounts.oauth2.revoke(gdToken)}catch(e){}
  }
  gdToken=null;gdTokenExpiry=0;syncFileId=null;syncFolderId=null;
  localStorage.removeItem('gd_token');
  localStorage.removeItem('gd_token_expiry');
  updateSyncUI();
  toast('Google Drive desconectado');
}

function isGdConnected(){return!!gdToken&&gdTokenExpiry>Date.now()}

async function getValidToken(){
  if(isGdConnected())return gdToken;
  if(!gdTokenClient)return null;
  return new Promise(resolve=>{
    const orig=gdTokenClient.callback;
    gdTokenClient.callback=resp=>{
      gdTokenClient.callback=orig;
      handleAuthResponse(resp);
      resolve(resp.error?null:gdToken);
    };
    gdTokenClient.requestAccessToken({prompt:''});
  });
}

// ═══════ DRIVE API HELPERS ═══════

async function gdFetch(url,opts={}){
  const token=await getValidToken();
  if(!token)throw new Error('NO_AUTH');
  const headers={'Authorization':`Bearer ${token}`,...(opts.headers||{})};
  let resp=await fetch(url,{...opts,headers});
  if(resp.status===401){
    gdToken=null;gdTokenExpiry=0;
    const t2=await getValidToken();
    if(!t2)throw new Error('NO_AUTH');
    headers.Authorization=`Bearer ${t2}`;
    resp=await fetch(url,{...opts,headers});
  }
  return resp;
}

async function gdFindFile(name,parentId){
  let q=`name='${name}' and trashed=false`;
  if(parentId)q+=` and '${parentId}' in parents`;
  const r=await gdFetch(`https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(q)}&fields=files(id,name,headRevisionId,modifiedTime)&spaces=drive`);
  const d=await r.json();
  return d.files&&d.files.length>0?d.files[0]:null;
}

async function gdReadFile(fileId){
  const[metaR,contentR]=await Promise.all([
    gdFetch(`https://www.googleapis.com/drive/v3/files/${fileId}?fields=id,headRevisionId,modifiedTime`),
    gdFetch(`https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`)
  ]);
  const meta=await metaR.json();
  const content=await contentR.json();
  return{content,revisionId:meta.headRevisionId};
}

async function gdWriteFile(fileId,content,expectedRevisionId){
  if(expectedRevisionId){
    const chk=await gdFetch(`https://www.googleapis.com/drive/v3/files/${fileId}?fields=headRevisionId`);
    const m=await chk.json();
    if(m.headRevisionId!==expectedRevisionId)throw new Error('REVISION_CONFLICT');
  }
  const r=await gdFetch(`https://www.googleapis.com/upload/drive/v3/files/${fileId}?uploadType=media&fields=id,headRevisionId`,{
    method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(content)
  });
  if(!r.ok)throw new Error(`WRITE_FAIL:${r.status}`);
  return r.json();
}

async function gdCreateFile(name,content,parentId){
  const meta={name,mimeType:'application/json'};
  if(parentId)meta.parents=[parentId];
  const boundary='fb_'+Date.now();
  const body=`--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${JSON.stringify(meta)}\r\n--${boundary}\r\nContent-Type: application/json\r\n\r\n${JSON.stringify(content)}\r\n--${boundary}--`;
  const r=await gdFetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,headRevisionId',{
    method:'POST',
    headers:{'Content-Type':`multipart/related; boundary=${boundary}`},
    body
  });
  if(!r.ok)throw new Error(`CREATE_FAIL:${r.status}`);
  return r.json();
}

async function gdFindOrCreateFolder(name,parentId){
  let q=`name='${name}' and mimeType='application/vnd.google-apps.folder' and trashed=false`;
  if(parentId)q+=` and '${parentId}' in parents`;
  const r=await gdFetch(`https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(q)}&fields=files(id)`);
  const d=await r.json();
  if(d.files&&d.files.length>0)return d.files[0].id;
  const meta={name,mimeType:'application/vnd.google-apps.folder'};
  if(parentId)meta.parents=[parentId];
  const cr=await gdFetch('https://www.googleapis.com/drive/v3/files',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(meta)
  });
  return(await cr.json()).id;
}

// ═══════ MERGE ALGORITHM ═══════

function syncDeepEqual(a,b){
  if(a===b)return true;
  if(a==null||b==null)return false;
  if(typeof a!==typeof b)return false;
  if(typeof a!=='object')return false;
  const ka=Object.keys(a).filter(k=>k!=='updated_at');
  const kb=Object.keys(b).filter(k=>k!=='updated_at');
  if(ka.length!==kb.length)return false;
  return ka.every(k=>syncDeepEqual(a[k],b[k]));
}

function mergeStore(local,remote,storeName){
  const lMap=new Map(local.map(r=>[r.id,r]));
  const rMap=new Map(remote.map(r=>[r.id,r]));
  const allIds=new Set([...lMap.keys(),...rMap.keys()]);
  const merged=[],conflicts=[];
  for(const id of allIds){
    const l=lMap.get(id),r=rMap.get(id);
    if(l&&!r){merged.push(l);continue}
    if(!l&&r){merged.push(r);continue}
    const lt=l.updated_at||'2000-01-01T00:00:00.000Z';
    const rt=r.updated_at||'2000-01-01T00:00:00.000Z';
    if(lt===rt){merged.push(l);continue}
    if(syncDeepEqual(l,r)){merged.push(lt>rt?l:r);continue}
    conflicts.push({store:storeName,id,local_version:l,remote_version:r,detected_at:new Date().toISOString()});
    merged.push(lt>rt?l:r);
  }
  return{merged,conflicts};
}

// ═══════ VALIDATION ═══════

function validateSyncData(data){
  const err=[];
  if(!data||data.app!=='finanzas-personales')err.push('Formato no reconocido');
  for(const s of['transactions','values','budgets','goals']){
    const recs=data[s];if(!Array.isArray(recs))continue;
    const ids=new Set();
    for(const r of recs){
      if(!r.id){err.push(`Sin ID en ${s}`);continue}
      if(ids.has(r.id))err.push(`ID duplicado en ${s}: ${r.id}`);
      ids.add(r.id);
    }
  }
  if(Array.isArray(data.transactions)){
    for(const tx of data.transactions){
      if(tx.deleted)continue;
      if(!['gasto','ingreso','inversion'].includes(tx.type))err.push(`Tipo invalido: ${tx.id}`);
      if(typeof tx.amount!=='number'||!isFinite(tx.amount))err.push(`Importe invalido: ${tx.id}`);
    }
  }
  return err;
}

// ═══════ IDB ATOMIC WRITE ═══════

function writeStoreAtomic(storeName,records){
  return new Promise((resolve,reject)=>{
    const tx=DB.transaction(storeName,'readwrite');
    const st=tx.objectStore(storeName);
    st.clear();
    for(const r of records)st.put(r);
    tx.oncomplete=()=>resolve();
    tx.onerror=()=>reject(tx.error);
    tx.onabort=()=>reject(new Error('Transaction aborted'));
  });
}

async function writeAllToIDB(data){
  const map=[
    ['transactions',data.transactions],
    ['values',data.values],
    ['budget',data.budgets],
    ['goals',data.goals]
  ];
  for(const[name,recs]of map){
    if(Array.isArray(recs))await writeStoreAtomic(name,recs);
  }
  if(data.config)await dbPut('config',data.config);
}

// ═══════ SYNC ENGINE ═══════

async function gatherSyncData(){
  const now=new Date().toISOString();
  const stamp=r=>{
    if(!r.updated_at)r.updated_at=now;
    if(r.deleted===undefined)r.deleted=false;
    return r;
  };
  const txs=(await dbAll('transactions')).map(stamp);
  const vals=(await dbAll('values')).map(stamp);
  const budgets=(await dbAll('budget')).map(stamp);
  const goals=(await dbAll('goals')).map(stamp);
  return{
    app:'finanzas-personales',version:'2.1',sync_version:1,
    last_sync:now,
    config:{id:'main',updated_at:now,...CONFIG},
    transactions:txs,values:vals,budgets,goals,
    _conflicts:[]
  };
}

async function performSync(manual=false){
  if(syncInProgress){if(manual)toast('Sincronización en progreso...');return}
  if(!isGdConnected()){if(manual)toast('Conecta Google Drive primero');return}
  if(!navigator.onLine){if(manual)toast('Sin conexión');return}

  syncInProgress=true;
  updateSyncStatus('syncing');

  try{
    const localData=await gatherSyncData();
    if(!syncFolderId)syncFolderId=await gdFindOrCreateFolder(SYNC_FOLDER);

    const existing=syncFileId?{id:syncFileId}:await gdFindFile(SYNC_FILE,syncFolderId);

    if(!existing){
      const errs=validateSyncData(localData);
      if(errs.length>0)throw new Error(errs.join(', '));
      const created=await gdCreateFile(SYNC_FILE,localData,syncFolderId);
      syncFileId=created.id;
      await writeAllToIDB(localData);
      updateSyncStatus('synced');
      localStorage.setItem('last_sync_time',new Date().toISOString());
      if(manual)toast('Primera sincronización completada');
      return;
    }
    syncFileId=existing.id;

    let attempts=0;
    while(attempts<MAX_RETRIES){
      attempts++;
      const remote=await gdReadFile(syncFileId);
      const rd=remote.content;
      const rev=remote.revisionId;

      const txR=mergeStore(localData.transactions,rd.transactions||[],'transactions');
      const valR=mergeStore(localData.values,rd.values||[],'values');
      const budR=mergeStore(localData.budgets,rd.budgets||[],'budgets');
      const goalR=mergeStore(localData.goals,rd.goals||[],'goals');

      let mergedCfg=localData.config,cfgConflict=null;
      if(rd.config){
        const lt=localData.config.updated_at||'2000-01-01T00:00:00.000Z';
        const rt=rd.config.updated_at||'2000-01-01T00:00:00.000Z';
        if(lt!==rt&&!syncDeepEqual(localData.config,rd.config)){
          cfgConflict={store:'config',id:'main',local_version:localData.config,remote_version:rd.config,detected_at:new Date().toISOString()};
          mergedCfg=lt>rt?localData.config:rd.config;
        }else if(rt>lt){mergedCfg=rd.config}
      }

      const allConflicts=[
        ...txR.conflicts,...valR.conflicts,...budR.conflicts,...goalR.conflicts,
        ...(rd._conflicts||[]),
        ...(cfgConflict?[cfgConflict]:[])
      ];

      const merged={
        app:'finanzas-personales',version:'2.1',sync_version:1,
        last_sync:new Date().toISOString(),
        config:mergedCfg,
        transactions:txR.merged,values:valR.merged,
        budgets:budR.merged,goals:goalR.merged,
        _conflicts:allConflicts
      };

      const errs=validateSyncData(merged);
      if(errs.length>0)throw new Error(errs.join(', '));

      try{
        await gdWriteFile(syncFileId,merged,rev);
        await writeAllToIDB(merged);

        if(mergedCfg){
          const{id,updated_at,deleted,...cf}=mergedCfg;
          Object.assign(CONFIG,cf);
        }
        await maybeBackup(merged);

        updateSyncStatus(allConflicts.length>0?'conflicts':'synced',allConflicts.length);
        localStorage.setItem('last_sync_time',new Date().toISOString());
        if(manual)toast(allConflicts.length>0?`Sincronizado con ${allConflicts.length} conflicto${allConflicts.length>1?'s':''}` :'Sincronizado correctamente');
        refreshCurrentView();
        return;
      }catch(e){
        if(e.message==='REVISION_CONFLICT'&&attempts<MAX_RETRIES)continue;
        throw e;
      }
    }
    throw new Error('No se pudo sincronizar tras varios intentos');
  }catch(e){
    console.error('Sync error:',e);
    if(e.message==='NO_AUTH'){
      updateSyncStatus('error','Sesión expirada');
      if(manual)toast('Sesión expirada. Reconecta Google Drive.');
    }else{
      updateSyncStatus('error',e.message);
      if(manual)toast('Error de sync: '+e.message);
    }
  }finally{
    syncInProgress=false;
  }
}

// ═══════ BACKUPS ═══════

async function maybeBackup(data){
  const cnt=parseInt(localStorage.getItem('sync_count')||'0')+1;
  localStorage.setItem('sync_count',String(cnt));
  const last=localStorage.getItem('last_backup_time');
  const weekAgo=Date.now()-7*24*60*60*1000;
  if(cnt%BACKUP_EVERY_N!==0&&last&&new Date(last).getTime()>weekAgo)return;
  try{
    const bfId=await gdFindOrCreateFolder(BACKUP_FOLDER,syncFolderId);
    const date=new Date().toISOString().split('T')[0];
    const name=`finanzas-backup-${date}.json`;
    const ex=await gdFindFile(name,bfId);
    if(!ex)await gdCreateFile(name,data,bfId);
    localStorage.setItem('last_backup_time',new Date().toISOString());
  }catch(e){console.warn('Backup failed:',e)}
}

// ═══════ SYNC TRIGGERS ═══════

function scheduleSyncAfterWrite(){
  if(!isGdConnected())return;
  if(syncDebounce)clearTimeout(syncDebounce);
  syncDebounce=setTimeout(()=>performSync(false),SYNC_DEBOUNCE);
  updateSyncStatus('pending');
}

function syncIfNeeded(){
  if(!isGdConnected()||!navigator.onLine)return;
  performSync(false);
}

function manualSync(){performSync(true)}

// ═══════ SYNC UI ═══════

function updateSyncStatus(status,detail){
  const el=document.getElementById('sync-status');
  if(!el)return;
  const cfg={
    synced:{icon:'●',color:'var(--positive)',text:'Sincronizado'},
    syncing:{icon:'↻',color:'var(--text2)',text:'Sincronizando...'},
    pending:{icon:'●',color:'#f59e0b',text:'Pendiente'},
    error:{icon:'●',color:'var(--negative)',text:'Error'},
    offline:{icon:'●',color:'var(--text3)',text:'Sin conexión'},
    conflicts:{icon:'⚠',color:'#f59e0b',text:`${detail} conflicto${detail>1?'s':''}`}
  }[status]||{icon:'',color:'var(--text3)',text:''};
  el.innerHTML=`<span style="color:${cfg.color};font-size:8px;margin-right:4px">${cfg.icon}</span><span style="font-size:11px;color:${cfg.color};font-weight:500">${cfg.text}</span>`;
  el.style.display='flex';
}

function updateSyncUI(){
  const on=isGdConnected();
  const ids=['gd-connect-item','gd-sync-item','gd-disconnect-item','sync-status'];
  const show=[!on,on,on,on];
  ids.forEach((id,i)=>{const el=document.getElementById(id);if(el)el.style.display=show[i]?'flex':'none'});

  const footer=document.querySelector('#screen-settings p');
  if(footer){
    if(on){
      const ls=localStorage.getItem('last_sync_time');
      footer.innerHTML=`Fivvo v2.1 — Sincronizado con Google Drive.<br>Último sync: ${ls?timeSince(new Date(ls)):'nunca'}`;
    }else{
      footer.innerHTML='Fivvo v2.1 — Tus datos viven en este dispositivo.<br>Conecta Google Drive para sincronizar.';
    }
  }
}

function timeSince(d){
  const s=Math.floor((Date.now()-d.getTime())/1000);
  if(s<60)return'hace un momento';
  const m=Math.floor(s/60);if(m<60)return`hace ${m} min`;
  const h=Math.floor(m/60);if(h<24)return`hace ${h}h`;
  return`hace ${Math.floor(h/24)} día${Math.floor(h/24)>1?'s':''}`;
}

function refreshCurrentView(){
  const r={dashboard:typeof renderDashboard==='function'?renderDashboard:null,
    history:typeof renderHistory==='function'?renderHistory:null,
    cartera:typeof renderCartera==='function'?renderCartera:null,
    plan:typeof renderPlan==='function'?renderPlan:null};
  if(r[currentScreen])r[currentScreen]();
}

// ═══════ CONFLICT RESOLUTION ═══════

async function showConflicts(){
  if(!syncFileId){toast('Sincroniza primero');return}
  try{
    const remote=await gdReadFile(syncFileId);
    const conflicts=remote.content._conflicts||[];
    if(conflicts.length===0){toast('No hay conflictos pendientes');return}
    renderConflictList(conflicts,remote.content,remote.revisionId);
    openModal('conflict-modal');
  }catch(e){toast('Error al cargar conflictos')}
}

function conflictDesc(c){
  if(c.store==='transactions'){
    const d=v=>`${v.type} · ${fmtC(v.amount)} · ${v.category||v.tipo_inv||''} · ${fmtD(v.date)}`;
    return{local:d(c.local_version),remote:d(c.remote_version)};
  }
  if(c.store==='goals'){
    return{local:`${c.local_version.name} · Meta: ${fmtC(c.local_version.target)}`,
           remote:`${c.remote_version.name} · Meta: ${fmtC(c.remote_version.target)}`};
  }
  return{local:JSON.stringify(c.local_version).slice(0,80),remote:JSON.stringify(c.remote_version).slice(0,80)};
}

function renderConflictList(conflicts,syncData,revisionId){
  const el=document.getElementById('conflict-list');
  if(!el)return;
  if(conflicts.length===0){el.innerHTML='<div class="tx-empty">No hay conflictos pendientes</div>';return}
  const storeLabels={transactions:'Transacción',values:'Valores',budgets:'Presupuesto',goals:'Objetivo',config:'Configuración'};
  let html='';
  conflicts.forEach((c,i)=>{
    const desc=conflictDesc(c);
    const label=storeLabels[c.store]||c.store;
    const bothBtn=c.store==='transactions'?`<button class="btn-sm btn-secondary" style="font-size:12px;padding:8px 14px" onclick="resolveConflict(${i},'both')">Ambos</button>`:'';
    html+=`<div style="background:var(--bg);border-radius:var(--r-sm);padding:14px;margin-bottom:10px">
      <div style="font-weight:600;font-size:14px;margin-bottom:8px">${label} #${i+1}</div>
      <div style="font-size:12px;margin-bottom:6px"><span style="font-weight:600;color:var(--positive)">Este dispositivo:</span><br><span style="color:var(--text2)">${desc.local}</span></div>
      <div style="font-size:12px;margin-bottom:10px"><span style="font-weight:600;color:var(--invest)">Otro dispositivo:</span><br><span style="color:var(--text2)">${desc.remote}</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn-sm btn-primary" style="font-size:12px;padding:8px 14px" onclick="resolveConflict(${i},'local')">Mantener este</button>
        <button class="btn-sm btn-secondary" style="font-size:12px;padding:8px 14px" onclick="resolveConflict(${i},'remote')">Mantener otro</button>
        ${bothBtn}
      </div>
    </div>`;
  });
  el.innerHTML=html;
  el._syncData=syncData;
  el._revisionId=revisionId;
}

async function resolveConflict(idx,choice){
  const el=document.getElementById('conflict-list');
  const sd=el._syncData,rev=el._revisionId;
  const c=sd._conflicts[idx];
  if(!c)return;
  const now=new Date().toISOString();
  const sKey=c.store==='budgets'?'budgets':c.store;

  if(choice==='local'||choice==='remote'){
    const ver=choice==='local'?c.local_version:c.remote_version;
    const recs=sd[sKey];
    if(Array.isArray(recs)){
      const ri=recs.findIndex(r=>r.id===c.id);
      const resolved={...ver,updated_at:now};
      if(ri>=0)recs[ri]=resolved;else recs.push(resolved);
    }
  }else if(choice==='both'){
    const recs=sd[sKey];
    if(Array.isArray(recs)){
      recs.push({...c.local_version,id:uuid(),updated_at:now});
    }
  }
  sd._conflicts.splice(idx,1);
  sd.last_sync=now;

  try{
    const result=await gdWriteFile(syncFileId,sd,rev);
    await writeAllToIDB(sd);
    el._syncData=sd;
    el._revisionId=result.headRevisionId;
    renderConflictList(sd._conflicts,sd,result.headRevisionId);
    toast('Conflicto resuelto');
    updateSyncStatus(sd._conflicts.length>0?'conflicts':'synced',sd._conflicts.length);
    refreshCurrentView();
  }catch(e){toast('Error al resolver conflicto')}
}

// ═══════ SETUP ═══════

function saveGdSetup(){
  const inp=document.getElementById('gd-client-id-input');
  const cid=inp?inp.value.trim():'';
  if(!cid){toast('Introduce el Client ID');return}
  setGdClientId(cid);
  closeModal('gd-setup-modal');
  initGoogleAuth();
  toast('Client ID guardado');
  setTimeout(()=>gdSignIn(),500);
}

// ═══════ DATA MODEL MIGRATION ═══════

async function migrateDataModel(){
  if(localStorage.getItem('model_migrated_v2'))return;
  const now=new Date().toISOString();
  const stores=['transactions','values','budget','goals'];
  for(const s of stores){
    const all=await dbAll(s);
    let changed=false;
    for(const r of all){
      if(!r.updated_at){r.updated_at=now;changed=true}
      if(r.deleted===undefined){r.deleted=false;changed=true}
    }
    if(changed){
      for(const r of all)await dbPut(s,r);
    }
  }
  const cfg=await dbGet('config','main');
  if(cfg&&!cfg.updated_at){
    cfg.updated_at=now;
    await dbPut('config',cfg);
  }
  localStorage.setItem('model_migrated_v2','1');
}

// ═══════ INIT SYNC ═══════

function initSync(){
  window.addEventListener('online',()=>{updateSyncUI();syncIfNeeded()});
  window.addEventListener('offline',()=>updateSyncStatus('offline'));
  if(typeof google!=='undefined'&&isGdConfigured()){
    initGoogleAuth();
  }else if(isGdConfigured()){
    const poll=setInterval(()=>{
      if(typeof google!=='undefined'){clearInterval(poll);initGoogleAuth()}
    },500);
    setTimeout(()=>clearInterval(poll),10000);
  }
  updateSyncUI();
  if(!navigator.onLine)updateSyncStatus('offline');
}
