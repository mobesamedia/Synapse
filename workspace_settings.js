function (cfg) {
    if (document.getElementById('synapse-workspace-settings')) return;
    const previous = document.activeElement;
    const dialog = document.createElement('dialog');
    dialog.id = 'synapse-workspace-settings';
    dialog.setAttribute('aria-labelledby', 'sp-workspace-title');
    const c = cfg.colors;
    dialog.style.cssText = `position:fixed;inset:10px 10px auto;margin:0 auto;padding:0;width:calc(100% - 20px);max-width:560px;max-height:calc(100% - 20px);overflow:hidden;border:1px solid ${c.grey_light};border-radius:14px;background:${c.bg};color:${c.text};box-shadow:0 12px 40px #0003;font:13px -apple-system,BlinkMacSystemFont,sans-serif;box-sizing:border-box`;
    const style = document.createElement('style');
    style.textContent = '#synapse-workspace-settings::backdrop{background:#0005}#synapse-workspace-settings button:focus-visible,#synapse-workspace-settings input:focus-visible{outline:2px solid currentColor;outline-offset:3px}';
    dialog.append(style);
    const title = document.createElement('h2'); title.id='sp-workspace-title'; title.textContent=cfg.title; title.style.cssText='font-size:13px;font-weight:650;margin:0';
    const info = document.createElement('p'); info.textContent=cfg.description;info.style.cssText=`color:${c.text_muted || c.text};line-height:1.5;margin:0 0 18px`;
    const header=document.createElement('div');
    header.style.cssText=`display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid ${c.grey_light};background:${c.surface};flex-shrink:0`;
    const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label',cfg.close || 'Close');
    close.style.cssText=`border:0;background:transparent;color:${c.text_muted};width:28px;height:28px;font-size:22px;cursor:pointer;border-radius:6px;padding:0;line-height:1`;
    close.onclick=()=>{if(!busy)dialog.close();};header.append(title,close);
    const body=document.createElement('div');body.style.cssText='padding:12px;overflow-y:auto;min-height:0;scrollbar-width:thin';
    const card=document.createElement('div');card.style.cssText=`padding:12px;border-radius:10px;background:${c.surface};border:1px solid ${c.grey_light}`;
    info.style.cssText=`color:${c.text_muted};line-height:1.5;font-size:12px;margin:0 0 12px`;
    card.append(info);body.append(card);dialog.append(header,body);
    const checks={};
    for (const [key, value] of Object.entries(cfg.values)) {
        const row=document.createElement('label');row.style.cssText=`display:flex;align-items:center;justify-content:space-between;padding:8px 0;margin:4px 0;font-size:12px;cursor:pointer`;
        const label=document.createElement('span'); label.textContent=cfg.labels[key];
        const check=document.createElement('input');check.type='checkbox';check.checked=value;check.style.cssText=`width:17px;height:17px;accent-color:${c.blue_accent}`;checks[key]=check;
        row.append(label,check);card.append(row);
    }
    const error=document.createElement('p');error.setAttribute('role','alert');error.style.cssText='font-size:12px;line-height:1.4';body.append(error);
    const actions=document.createElement('div');actions.style.cssText='display:flex;gap:8px;justify-content:flex-end;margin-top:18px';
    function button(text, primary){const b=document.createElement('button');b.type='button';b.textContent=text;b.style.cssText=`border:0;border-radius:9px;padding:9px 16px;cursor:pointer;font:inherit;background:${primary?c.blue_accent:c.grey_light};color:${primary?'white':c.text}`;actions.append(b);return b;}
    const cancel=button(cfg.cancel,false),save=button(cfg.save,true);
    const valid=()=>Object.values(checks).some(el=>el.checked);
    const update=()=>{save.disabled=!valid();save.style.opacity=save.disabled?'.4':'1';};
    Object.values(checks).forEach(el=>el.addEventListener('change',update));
    let busy=false;
    cancel.onclick=()=>dialog.close();
    dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
    dialog.addEventListener('close',()=>{dialog.remove();delete window.synapseWorkspaceSettingsError;previous?.focus();});
    window.synapseWorkspaceSettingsError=message=>{busy=false;cancel.disabled=false;close.disabled=false;Object.values(checks).forEach(el=>el.disabled=false);error.textContent=message;update();};
    save.onclick=()=>{
        if(busy||!valid())return;
        busy=true;save.disabled=true;cancel.disabled=true;close.disabled=true;Object.values(checks).forEach(el=>el.disabled=true);
        const data=Object.fromEntries(Object.entries(checks).map(([k,v])=>[k,v.checked]));
        const cmd='settings-save:'+encodeURIComponent(JSON.stringify(data));
        if(cfg.group==='maps')window.__synapseMindmapCommand(cmd);
        else window.pycmd('notion_mini:'+cmd);
    };
    body.append(actions);document.body.append(dialog);dialog.showModal();dialog.style.display='flex';dialog.style.flexDirection='column';update();
    dialog.addEventListener('click',event=>{if(event.target!==dialog||busy)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
}
