/* Files live in the Anki profile; documents and undo contain only small references. */
(() => {
    const valid = value => typeof value==='string' && /^[a-f0-9]{64}\.(png|jpg)$/.test(value);
    let pending = null;
    window.workspaceImageURL = value => valid(value) && window.__WORKSPACE_IMAGE_BASE__ ? window.__WORKSPACE_IMAGE_BASE__+value : '';
    window.workspaceCanAddImage = (entries, image, replaced=null) => {
        const existing=entries.filter(o=>o.image && o!==replaced);
        const pixels=existing.reduce((sum,o)=>sum+(o.imageWidth||1600)*(o.imageHeight||1600),0);
        return existing.length<40 && pixels+image.width*image.height<=24000000;
    };
    window.workspacePickImage = callback => {
        if (pending) return;
        if (!window.__SYNAPSE_MM_HOSTED__) { window.__workspaceError(workspaceText('Images require Anki.')); return; }
        pending=callback;
        window.__synapseMindmapCommand('image-add');
    };
    window.__workspaceImageAdded = image => { const callback=pending;pending=null;if(image&&valid(image.image))callback?.(image); };
    window.__workspaceError = text => {
        if (window.__mmToast) window.__mmToast(text,'error',9000);
        else { const e=document.getElementById('message');e.textContent=text;e.hidden=false; }
    };
})();

/* Bound history memory, not the user's document. At most ~16 MB of UTF-16 text. */
window.workspaceTrimHistory=(undo,redo)=>{
    let size=undo.concat(redo).reduce((sum,s)=>sum+s.length,0);
    while(undo.length+redo.length>50||size>8000000){
        const stack=undo.length>=redo.length?undo:redo;
        if(!stack.length)break;
        size-=stack.shift().length;
    }
};
(() => {
    const warned=new Set();
    window.workspaceCheckSize=(entries,id)=>{
        if(!id||warned.has(id))return;
        const pixels=entries.reduce((sum,o)=>sum+(o.image?(o.imageWidth||1600)*(o.imageHeight||1600):0),0);
        const text=entries.reduce((sum,o)=>sum+String(o.html||o.text||'').length,0);
        if(entries.length<2000&&pixels<18000000&&text<2000000)return;
        warned.add(id);
        window.__workspaceError(workspaceText('Large document: editing may slow down. Export a backup and consider splitting it into smaller maps.'));
    };
})();
