/* Shared, reference-only Anki links. User text never becomes executable markup. */
(()=>{
    const t=s=>(window.workspaceText||String)(s);
    const icon='<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m0 12a4 4 0 0 0 6 0l5-5a4 4 0 0 0-6-6l-1 1" transform="translate(2 1) scale(.85)"/></svg>';
    window.workspaceValidLinks=values=>Array.isArray(values)&&values.length<=12&&values.every(l=>
        l&&l.version===1&&['note','card'].includes(l.kind)&&typeof l.noteGuid==='string'&&l.noteGuid.length>0&&l.noteGuid.length<=100&&!/[\x00-\x1f]/.test(l.noteGuid)&&/^[1-9][0-9]{0,18}$/.test(String(l.noteId))&&
        (l.kind==='note'||(/^[1-9][0-9]{0,18}$/.test(String(l.cardId))&&Number.isInteger(l.cardOrd)&&l.cardOrd>=0&&l.cardOrd<=65535)));
    let pending=null;
    const hosted=()=>{if(window.__SYNAPSE_MM_HOSTED__||window.__ROADMAP_HOSTED__)return true;window.__workspaceError(t('Anki links are available inside Anki.'));return false;};
    window.workspacePickLinks=(links,seed,callback)=>{
        if(pending||!hosted())return;
        const requestId=Date.now().toString(36)+Math.random().toString(36).slice(2);
        pending={requestId,callback};
        const sent=window.__synapseMindmapCommand('anki-links:'+encodeURIComponent(JSON.stringify({requestId,links:Array.isArray(links)?links:[],seed:String(seed||'').slice(0,160)})));
        if(sent===false){pending=null;window.__workspaceError(t('Could not open Anki links.'));}
    };
    window.__workspaceLinksPicked=result=>{
        if(!pending||pending.requestId!==result?.requestId)return;
        const callback=pending.callback;pending=null;
        if(Array.isArray(result.links))callback(result.links);
    };
    window.workspaceOpenLink=link=>{if(hosted())window.__synapseMindmapCommand('anki-open:'+encodeURIComponent(JSON.stringify(link)));};
    window.workspaceLinkBadge=(links,manage)=>{
        if(!Array.isArray(links)||!links.length)return null;
        const button=document.createElement('button');button.type='button';button.className='workspace-anki-link';
        button.innerHTML=icon;
        const text=document.createElement('span');text.textContent=links.length>1?'Anki · '+links.length:'Anki';button.append(text);
        button.title=(links.length>1?t('Linked items'):t('Open in Anki'))+'\n'+links.map(l=>String(l.label||'')).join('\n');button.setAttribute('aria-label',button.title);
        for(const type of ['mousedown','pointerdown','dblclick','contextmenu','keydown','keyup'])button.addEventListener(type,e=>e.stopPropagation());
        button.addEventListener('click',e=>{e.stopPropagation();if(links.length===1)window.workspaceOpenLink(links[0]);else manage();});
        return button;
    };
})();
