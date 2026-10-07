/* Shared Mindmap/Roadmap navigation. The existing Mindmap URL stays unchanged. */
(()=> {
    if (new URLSearchParams(location.search).has('tutorial') || window!==top) return;
    const t=window.workspaceText || (s=>s);
    const roadmap=!!document.querySelector('#roadmap-app');
    const icons= {
        mindmap:'<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v5M5 17v-5h14v5"/>',roadmap:'<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M6 9v9h9"/>',window:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/>',settings:'<path d="M9 3h6l.7 2.4 2 .9L20 6l3 5-1.8 1.7.1 2.2 1.7 1.6-3 5-2.4-.6-1.9 1L15 24H9l-.7-3.1-1.9-1L4 21l-3-5 1.8-1.7-.1-2.2L1 10l3-5 2.4.6 1.9-1L9 3Z" transform="translate(2 0) scale(.83)"/><circle cx="12" cy="11" r="3"/>',full:'<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>'
    };
    const svg=k=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${icons[k]}</svg>`;
    const nav=document.createElement('nav');
    nav.id='workspace-nav';
    nav.setAttribute('aria-label',t('Tools'));
    for(const [key,label] of [['mindmap','MindMap'],['roadmap','FreeMap']]) {
        if(window.__WORKSPACE_TOOLS__?.[key]===false)continue;
        const b=document.createElement('button');
        b.innerHTML=svg(key)+label;
        b.className='tool'+((roadmap?'roadmap':'mindmap')===key?' active':'');
        b.onclick=()=> {
            if((roadmap?'roadmap':'mindmap')!==key)window.__synapseMindmapCommand('switch:'+key)
        };
        nav.append(b)
    }
    const spacer=document.createElement('span');
    spacer.className='nav-spacer';
    nav.append(spacer);
    for(const [key,title] of [['settings',t('Settings')],['window',t('Enlarge')],['full',t('Fullscreen')]]) {
        const b=document.createElement('button');
        b.id='workspace-'+key;
        b.title=title;
        b.setAttribute('aria-label',title);
        b.innerHTML=svg(key);
        b.onclick=()=> {
            if(key==='settings')window.__synapseMindmapCommand('settings');
            else if(key==='window')window.__synapseWinToggle();
            else window.__synapseFsToggle()
        };
        nav.append(b)
    }
    document.body.classList.add("workspace-navigation");
    document.body.prepend(nav);
    let fs=false,win=false;
    const oldFs=window.__synapseSetFullscreen, oldWin=window.__synapseSetWindow;
    window.__synapseSetFullscreen=(active,labels)=> {
        fs=active;
        if(oldFs)oldFs(active,labels);
        document.querySelector('#workspace-full').classList.toggle('active',active);
        document.querySelector('#workspace-full').title=active?t('Exit Fullscreen'):t('Fullscreen');
        document.querySelector('#workspace-full').setAttribute('aria-label',document.querySelector('#workspace-full').title)
    };
    window.__synapseSetWindow=(active,labels)=> {
        const changed=win!==active;
        win=active;
        if(oldWin)oldWin(active,labels);
        document.querySelector('#workspace-window').classList.toggle('active',active);
        document.querySelector('#workspace-window').title=active?t('Reduce'):t('Enlarge');
        document.querySelector('#workspace-window').setAttribute('aria-label',document.querySelector('#workspace-window').title);
        if(changed)centerAfterResize();
    };
    let stopCenterWatch=null;
    function centerAfterResize(){
        if(stopCenterWatch)stopCenterWatch();
        let timer;
        const target=document.querySelector(roadmap?'#workspace':'#mindmap-container');
        const center=()=>{clearTimeout(timer);timer=setTimeout(()=>window.__workspaceCenterView?.(),80);};
        const observer=new ResizeObserver(center);
        if(target)observer.observe(target);
        center();
        const end=setTimeout(()=>{observer.disconnect();stopCenterWatch=null;},600);
        stopCenterWatch=()=>{observer.disconnect();clearTimeout(timer);clearTimeout(end);};
    }
    window.__synapseFsToggle=()=> {
        window.__synapseMindmapCommand(fs?'exitfullscreen':'fullscreen')
    };
    window.__synapseWinToggle=()=> {
        window.__synapseMindmapCommand(win?'exitwindow':'window')
    };
})();
