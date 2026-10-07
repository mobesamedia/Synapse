/* Offline diagram editor. Coordinates are document coordinates; view state is separate. */
(()=> {
    'use strict';
    const t = window.workspaceText || (s=>s);
    const $=s=>document.querySelector(s),NS='http://www.w3.org/2000/svg',XHTML='http://www.w3.org/1999/xhtml';
    const clone=x=>JSON.parse(JSON.stringify(x)),uid=()=> 'r'+Date.now().toString(36)+Math.random().toString(36).slice(2,9);
    const SHAPES= {
        rect:t("Rectangle"),square:t("Square"),rounded:t("Rounded"),oval:t("Oval"),circle:t("Circle"),squircle:t("Squircle"),diamond:t("Diamond"),triangle:t("Triangle")
    };
    const workspace=$('#workspace'),scene=$('#scene'),world=$('#world'),layer=$('#objects'),selection=$('#selection');
    let data=window.__ROADMAP_DATA__|| {
        version:1,active:null,maps:[]
    },selected=new Set(),mode='auto',space=false,gesture=null,edit=null,revision=0,savedRevision=0,timer=null,frame=0,clipboard=null,clipboardIcons={},clipboardLicense='',undo=[],redo=[],recent=[],readOnly=!!window.__ROADMAP_ERROR__;
    let view= {
        x:120,y:100,scale:1
    },lastClick=null;
    let objectIndex=new Map(),rendering=false;
    const shapeCache=new Map(),arrowCache=new Map();
    let renderedMapId=null;
    const doc=()=>data.maps.find(m=>m.id===data.active),objects=()=>doc()?.objects||[],find=id=>rendering?objectIndex.get(id):objects().find(o=>o.id===id);
    function el(tag,attrs= {
    },parent) {
        const e=document.createElementNS(NS,tag);
        for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);
        if(parent)parent.append(e);
        return e
    }
    function message(text,sticky=false) {
        $('#message').textContent=text;
        $('#message').hidden=false;
        clearTimeout(message.timer);
        if(!sticky)message.timer=setTimeout(()=>$('#message').hidden=true,5000)
    }
    function safeHTML(raw) {
        const t=document.createElement('template');
        t.innerHTML=String(raw||'');
        const allowed=new Set(['B','STRONG','I','EM','U','S','STRIKE','SPAN','DIV','P','BR','FONT']);
        const props=['font-weight','font-style','text-decoration','text-decoration-line','color','background-color','text-align','font-size'];
        const walk=(src,dst)=> {
            for(const n of src.childNodes) {
                if(n.nodeType===3) {
                    dst.append(document.createTextNode(n.textContent));
                    continue
                }
                if(n.nodeType!==1)continue;
                if(['SCRIPT','STYLE','IFRAME','OBJECT','IMG','SVG'].includes(n.tagName))continue;
                const out=document.createElement(allowed.has(n.tagName)?(n.tagName==='FONT'?'span':n.tagName.toLowerCase()):'span');
                for(const prop of props) {
                    const val=n.style?.getPropertyValue(prop);
                    if(val&&!/url\(|expression|var\(/i.test(val))out.style.setProperty(prop,val)
                }
                if(n.tagName==='FONT'&&/^#[0-9a-f]{3,8}$/i.test(n.getAttribute('color')||''))out.style.color=n.getAttribute('color');
                walk(n,out);
                dst.append(out)
            }
        };
        const out=document.createElement('div');
        walk(t.content,out);
        return out.innerHTML
    }
    function normalize(input) {
        if(!input||input.version!==1||!Array.isArray(input.maps))throw Error(t("Invalid FreeMap file."));
        const ids=new Set();
        for(const m of input.maps) {
            if(!m||typeof m.id!=='string'||!/^[-\w]{1,100}$/.test(m.id)||ids.has(m.id)||typeof m.name!=='string'||!Array.isArray(m.objects))throw Error(t("Invalid FreeMap."));
            window.FreeMapIcons.validateDocument(m);
            ids.add(m.id);
            if(!m.view||!['x','y','scale'].every(k=>Number.isFinite(m.view[k]))||m.view.scale<.05||m.view.scale>4)m.view= {
                x:120,y:100,scale:1
            };
            const os=new Set();
            for(const o of m.objects) {
                if(!o||typeof o.id!=='string'||!/^[-\w]{1,100}$/.test(o.id)||os.has(o.id)||!['shape','text','arrow','image','icon'].includes(o.kind))throw Error(t("Invalid object."));
                os.add(o.id);
                if(o.ankiLinks!==undefined&&!window.workspaceValidLinks(o.ankiLinks))throw Error(t('Invalid Anki link.'));
                if(o.image&&!/^[a-f0-9]{64}\.(png|jpg)$/.test(o.image))throw Error(t('Could not load image.'));
                if(o.kind==='image'&&!o.image)throw Error(t('Could not load image.'));
                o.stroke=/^#[0-9a-f]{6}$/i.test(o.stroke)?o.stroke:'#252525';
                o.fill=o.fill==='none'?'none':/^#[0-9a-f]{6}$/i.test(o.fill)?o.fill:'#ffffff';
                if(o.kind!=='arrow') {
                    for(const k of ['x','y','w','h','rotation'])if(!Number.isFinite(o[k])||Math.abs(o[k])>1e7)throw Error(t("Invalid position."));
                    if(o.w<1||o.h<1)throw Error(t("Invalid size."));
                    o.html=safeHTML(o.html);
                    o.shape=SHAPES[o.shape]?o.shape:'rect';
                    o.fontSize=Math.max(8,Math.min(96,Number(o.fontSize)||20))
                }
                else {
                    for(const k of ['a','b']) {
                        if(!o[k]||(!o[k].node&&(!Number.isFinite(o[k].x)||!Number.isFinite(o[k].y)||Math.abs(o[k].x)>1e7||Math.abs(o[k].y)>1e7)))throw Error(t("Invalid arrow."))
                    }
                    o.route=['rounded','angle','curve','straight'].includes(o.route)?o.route:'rounded';
                    o.tip=['triangle','open','dot','none'].includes(o.tip)?o.tip:'triangle';
                    o.dash=['solid','dashed','dotted'].includes(o.dash)?o.dash:'solid';
                    o.label=String(o.label||'');
                    o.labelSize=Math.max(8,Math.min(72,Number(o.labelSize)||14))
                }
            }
            for(const o of m.objects.filter(o=>o.kind==='arrow'))for(const k of ['a','b'])if(o[k].node&&(!m.objects.some(n=>n.id===o[k].node&&n.kind!=='arrow')||!['top','right','bottom','left'].includes(o[k].side)))throw Error(t("Invalid connection."));
        }
        if(!ids.has(input.active))input.active=input.maps[0]?.id||null;
        return input
    }
    try {
        data=normalize(data)
    }
    catch(e) {
        readOnly=true;
        data={version:1,active:null,maps:[]};
        message(e.message,true)
    }
    window.addEventListener('error', event => { if(event.error) stopAfterError(event.error); });
    window.addEventListener('unhandledrejection', event => stopAfterError(event.reason));
    function stopAfterError(error) {
        readOnly=true;
        if(edit)edit.box.contentEditable='false';
        clearTimeout(timer);
        $('#save-status').textContent=t('Save failed');
        message(t('Editing paused after an error. Keep this window open and export your changes.')+' '+String(error?.message||error),true);
        console.error('[Roadmap]',error);
    }
    function snapshot() {
        if(edit) {
            const o=find(edit.id);
            if(o)o.html=safeHTML(edit.box.innerHTML)
        }
        clearTimeout(timer);
        return {
            revision,data:clone(data)
        }
    }
    window.__roadmapSnapshot=()=>readOnly?null:snapshot();
    window.__roadmapSaved=(ok,rev)=> {
        if(ok) {
            savedRevision=Math.max(savedRevision,rev||0);
            $('#save-status').textContent=revision===savedRevision?t("Saved"):t("Saving...");
            if(revision>savedRevision)scheduleSave()
        }
        else {
            $('#save-status').textContent=t("Save failed");
            message(t("Save failed. Your changes remain open. Please retry or export."),true)
        }
    };
    function scheduleSave() {
        if(readOnly)return;
        clearTimeout(timer);
        timer=setTimeout(()=> {
            if(window.__ROADMAP_HOSTED__)window.__synapseMindmapCommand('roadmap-save');
            else $('#save-status').textContent=t("Preview · use Export")
        },500)
    }
    function changed() {
        if(readOnly)return;
        window.workspaceCheckSize?.(objects(), data.active);
        revision++;
        $('#save-status').textContent=t("Saving...");
        scheduleSave();
        updateHistory()
    }
    function checkpoint() {
        if(!doc()||readOnly)return;
        const s=JSON.stringify(doc());
        if(undo.at(-1)!==s)undo.push(s);
        redo=[];
        window.workspaceTrimHistory(undo,redo);
        updateHistory()
    }
    function updateHistory() {
        $('#undo').disabled=!undo.length;
        $('#redo').disabled=!redo.length
    }
    function travel(from,to) {
        if(readOnly)return;
        finishEdit();
        if(!from.length)return;
        to.push(JSON.stringify(doc()));
        const restored=JSON.parse(from.pop());
        window.workspaceTrimHistory(undo,redo);
        data.maps[data.maps.findIndex(m=>m.id===data.active)]=restored;
        selected.clear();
        changed();
        render();
        updateHistory()
    }
    function selectMap(id) {
        finishEdit();
        data.active=id;
        selected.clear();
        undo=[];
        redo=[];
        view=clone(doc()?.view|| {
            x:120,y:100,scale:1
        });
        list();
        render();
        changed()
    }
    function createMap(name=t("New FreeMap")) {
        finishEdit();
        const m= {
            id:uid(),name,objects:[],view: {
                x:120,y:100,scale:1
            }
        };
        data.maps.push(m);
        selectMap(m.id)
    }
    function createTutorial() {
        finishEdit();
        const tutorial=window.createRoadmapTutorial(t);
        tutorial.id=uid();
        normalize({version:1,active:tutorial.id,maps:[tutorial]});
        data.maps.push(tutorial);
        selectMap(tutorial.id);
        fit(true,160);
    }
    function list() {
        const s=$('#map-select');
        s.replaceChildren();
        for(const m of data.maps) {
            const o=document.createElement('option');
            o.value=m.id;
            o.textContent=m.name;
            s.append(o)
        }
        s.value=data.active||''
    }
    function localPoint(e) {
        const r=workspace.getBoundingClientRect();
        return {
            x:(e.clientX-r.left-view.x)/view.scale,y:(e.clientY-r.top-view.y)/view.scale
        }
    }
    function rotatePoint(x,y,cx,cy,angle) {
        const r=angle*Math.PI/180,c=Math.cos(r),s=Math.sin(r);
        return {
            x:cx+(x-cx)*c-(y-cy)*s,y:cy+(x-cx)*s+(y-cy)*c
        }
    }
    function anchor(o,side) {
        let x=o.x+o.w/2,y=o.y+o.h/2;
        if(side==='top')y=o.y;
        if(side==='bottom')y=o.y+o.h;
        if(side==='left')x=o.x;
        if(side==='right')x=o.x+o.w;
        if(o.shape==='triangle'&&['left','right'].includes(side))x=o.x+o.w*(side==='left'?.25:.75);
        return rotatePoint(x,y,o.x+o.w/2,o.y+o.h/2,o.rotation)
    }
    function endpoint(e) {
        return e.node&&find(e.node)?anchor(find(e.node),e.side): {
            x:e.x||0,y:e.y||0
        }
    }
    function snap(p,exclude) {
        const candidates=objects().filter(o=>o.kind!=='arrow'&&o.id!==exclude);
        for(const o of [...candidates].reverse()) {
            const local=rotatePoint(p.x,p.y,o.x+o.w/2,o.y+o.h/2,-o.rotation);
            if(local.x>=o.x&&local.x<=o.x+o.w&&local.y>=o.y&&local.y<=o.y+o.h){
                const side=['top','right','bottom','left'].sort((a,b)=>{const x=anchor(o,a),y=anchor(o,b);return Math.hypot(p.x-x.x,p.y-x.y)-Math.hypot(p.x-y.x,p.y-y.y);})[0];
                return {node:o.id,side};
            }
        }
        let best=null,d=18/view.scale;
        for(const o of candidates)for(const side of ['top','right','bottom','left']){
            const q=anchor(o,side),distance=Math.hypot(p.x-q.x,p.y-q.y);
            if(distance<d){best={node:o.id,side};d=distance;}
        }
        return best||p;
    }
    function vector(e,fallback) {
        if(e.node) {
            const o=find(e.node);
            if(o) {
                const p=anchor(o,e.side),c= {
                    x:o.x+o.w/2,y:o.y+o.h/2
                },len=Math.hypot(p.x-c.x,p.y-c.y)||1;
                return {
                    x:(p.x-c.x)/len,y:(p.y-c.y)/len
                }
            }
        }
        return fallback
    }
    let obstacleKey='', obstacles=[], routeCache=new Map();
    function updateObstacles() {
        const shapes=objects().filter(o=>o.kind!=='arrow');
        const key=JSON.stringify(shapes.map(o=>[o.id,o.x,o.y,o.w,o.h,o.rotation]));
        if(key===obstacleKey)return;
        obstacleKey=key;routeCache.clear();
        obstacles=shapes.map(o=>{
            const corners=[[o.x,o.y],[o.x+o.w,o.y],[o.x,o.y+o.h],[o.x+o.w,o.y+o.h]].map(([x,y])=>rotatePoint(x,y,o.x+o.w/2,o.y+o.h/2,o.rotation));
            return {id:o.id,l:Math.min(...corners.map(p=>p.x))-12,r:Math.max(...corners.map(p=>p.x))+12,t:Math.min(...corners.map(p=>p.y))-12,b:Math.max(...corners.map(p=>p.y))+12};
        });
    }
    function arrowPath(o) {
        const key=JSON.stringify([o.a,o.b,o.route]);
        const cached=routeCache.get(o.id);if(cached?.key===key)return cached.path;
        const a=endpoint(o.a),b=endpoint(o.b),dx=b.x-a.x,dy=b.y-a.y;
        const direction={x:Math.abs(dx)>=Math.abs(dy)?Math.sign(dx)||1:0,y:Math.abs(dx)<Math.abs(dy)?Math.sign(dy)||1:0};
        const v=vector(o.a,direction),w=vector(o.b,{x:-direction.x,y:-direction.y});
        const direct=window.workspaceRouting.clear([a,b],obstacles.filter(r=>r.id!==o.a.node&&r.id!==o.b.node));
        // Straight is honored only if it exits and enters the connected sides correctly.
        let d;
        if(o.route==='straight'&&direct&&(!o.a.node||dx*v.x+dy*v.y>0)&&(!o.b.node||dx*w.x+dy*w.y<0))d=`M${a.x},${a.y} L${b.x},${b.y}`;
        else if(o.route==='curve') {
            const distance=Math.max(30,Math.min(150,Math.hypot(dx,dy)*.4)),c={x:a.x+v.x*distance,y:a.y+v.y*distance},e={x:b.x+w.x*distance,y:b.y+w.y*distance};
            const samples=Array.from({length:33},(_,i)=>{const t=i/32,u=1-t;return{x:u*u*u*a.x+3*u*u*t*c.x+3*u*t*t*e.x+t*t*t*b.x,y:u*u*u*a.y+3*u*u*t*c.y+3*u*t*t*e.y+t*t*t*b.y};});
            const bodies=obstacles.map(r=>r.id===o.a.node||r.id===o.b.node?{...r,l:r.l+12,r:r.r-12,t:r.t+12,b:r.b-12}:r);
            if(window.workspaceRouting.clear(samples,bodies))d=`M${a.x},${a.y} C${c.x},${c.y} ${e.x},${e.y} ${b.x},${b.y}`;
            else d=window.workspaceRouting.path(window.workspaceRouting.route(a,b,v,w,obstacles,o.a.node,o.b.node),true);
        }
        else d=window.workspaceRouting.path(window.workspaceRouting.route(a,b,v,w,obstacles,o.a.node,o.b.node),o.route!=='angle');
        routeCache.set(o.id,{key,path:d});return d;
    }
    function textArea(o) {
        let x=10,y=8,w=o.w-20,h=o.h-16;
        if(['circle','oval'].includes(o.shape)) {
            x=o.w*.16;
            y=o.h*.16;
            w=o.w*.68;
            h=o.h*.68
        }
        else if(o.shape==='diamond') {
            x=o.w*.27;
            y=o.h*.27;
            w=o.w*.46;
            h=o.h*.46
        }
        else if(o.shape==='triangle') {
            x=o.w*.27;
            y=o.h*.48;
            w=o.w*.46;
            h=o.h*.38
        }
        else if(o.shape==='squircle') {
            x=o.w*.15;
            y=o.h*.15;
            w=o.w*.7;
            h=o.h*.7
        }
        if(o.kind==='text') {
            x=2;
            y=2;
            w=o.w-4;
            h=o.h-4
        }
        return {
            x,y,w:Math.max(2,w),h:Math.max(2,h)
        }
    }
    // Free text has no shape fill: its default ink follows the canvas, not
    // the stored shape stroke. Explicit user text colors remain authoritative.
    const darkText=o=>document.documentElement.classList.contains('dark') &&
        o.kind==='text' && !/(?:^|[;\s"'])color\s*:/i.test(o.html||'');
    const darkDefault=o=>document.documentElement.classList.contains('dark') && o.customStyle!==true && o.fill==='#ffffff' && o.stroke==='#252525' && !/(?:^|[;\s"'])color\s*:/i.test(o.html||'');
    new MutationObserver(()=>{shapeCache.clear();arrowCache.clear();layer.replaceChildren();$('#defs').replaceChildren();drawSoon();}).observe(document.documentElement,{attributes:true,attributeFilter:['class']});
    function editAnkiLinks(o) {
        if(readOnly)return;
        finishEdit();
        const mapId=data.active;
        const text=document.createElement('div');text.innerHTML=safeHTML(o.html);
        window.workspacePickLinks(o.ankiLinks,text.textContent,links=>{
            if(readOnly||data.active!==mapId||!objects().includes(o))return;
            if(JSON.stringify(o.ankiLinks||[])===JSON.stringify(links))return;
            mutate(()=>{if(links.length)o.ankiLinks=links;else delete o.ankiLinks;});
        });
    }
    function addLinkBadge(o,g) {
        const button=window.workspaceLinkBadge?.(o.ankiLinks,()=>editAnkiLinks(o));
        if(!button)return;
        const holder=el('foreignObject',{x:Math.max(0,(o.w-90)/2),y:o.h+5,width:90,height:32},g);
        holder.style.textAlign='center';
        holder.append(button);
    }
    function renderShape(o) {
        const g=el('g', {
            'data-id':o.id,transform:`translate(${o.x} ${o.y}) rotate(${o.rotation} ${o.w/2} ${o.h/2})`,class:'object-hit'
        },layer);
        addLinkBadge(o,g);
        if(o.kind==='icon') {
            el('rect',{width:o.w,height:o.h,fill:'transparent'},g);
            const svg=window.FreeMapIcons.svg(doc().iconAssets[o.icon],o.stroke||'#429bea');
            svg.setAttribute('width',o.w);svg.setAttribute('height',o.h);
            svg.setAttribute('pointer-events','none');g.append(svg);
            return g;
        }
        if(o.kind==='image') {
            el('rect',{width:o.w,height:o.h,fill:'#fff',stroke:o.stroke||'#ccc'},g);
            el('image',{href:window.workspaceImageURL(o.image),width:o.w,height:o.h,preserveAspectRatio:'xMidYMid meet','pointer-events':'none'},g);
            return g;
        }
        let shape;
        if(o.kind==='text')shape=el('rect', {
            width:o.w,height:o.h,fill:'transparent'
        },g);
        else {
            const style= {
                fill:darkDefault(o)?'#2c2c2c':o.fill||'#fff',stroke:darkDefault(o)?'#555555':o.stroke||'#252525','stroke-width':2
            };
            if(['circle','oval'].includes(o.shape))shape=el('ellipse', {
                cx:o.w/2,cy:o.h/2,rx:o.w/2,ry:o.h/2,...style
            },g);
            else if(o.shape==='diamond')shape=el('polygon', {
                points:`${o.w/2},0 ${o.w},${o.h/2} ${o.w/2},${o.h} 0,${o.h/2}`,...style
            },g);
            else if(o.shape==='triangle')shape=el('polygon', {
                points:`${o.w/2},0 ${o.w},${o.h} 0,${o.h}`,...style
            },g);
            else shape=el('rect', {
                width:o.w,height:o.h,rx:o.shape==='rounded'?Math.min(18,o.h*.2):o.shape==='squircle'?Math.min(o.w,o.h)*.32:0,...style
            },g)
        }
        const a=textArea(o),fo=el('foreignObject', {
            x:a.x,y:a.y,width:a.w,height:a.h
        },g),box=document.createElementNS(XHTML,'div');
        box.className='shape-text';
        box.style.color=(darkDefault(o)||darkText(o))?'#ffffff':'#303030';
        box.style.fontSize=(o.fontSize||20)+'px';
        const text=document.createElementNS(XHTML,'div');
        text.innerHTML=safeHTML(o.html);
        box.append(text);
        fo.append(box);
        const explicit=[...text.querySelectorAll('[style]')].filter(n=>/px$/.test(n.style.fontSize)).map(n=>[n,parseFloat(n.style.fontSize)]);
        let size=o.fontSize||20;
        while(size>8&&(text.scrollHeight>a.h+.5||text.scrollWidth>a.w+.5)) {
            size--;
            box.style.fontSize=size+'px';
            for(const [n,preferred]of explicit)n.style.fontSize=Math.max(8,preferred*size/(o.fontSize||20))+'px'
        }
        text.style.webkitLineClamp=String(Math.max(1,Math.floor(a.h/(size*1.25))));
        return g
    }
    function renderArrow(o) {
        const g=el('g', {
            'data-id':o.id
        },layer),d=arrowPath(o),color=document.documentElement.classList.contains('dark')&&o.stroke==='#252525'&&!o.customStyle?'#c7c7c7':o.stroke||'#252525';
        const marker=el('marker', {
            id:'tip-'+o.id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'
        },$('#defs'));
        if(o.tip==='open')el('path', {
            d:'M1 1 L9 5 L1 9',fill:'none',stroke:color,'stroke-width':1.5
        },marker);
        else if(o.tip==='dot')el('circle', {
            cx:5,cy:5,r:3.5,fill:color
        },marker);
        else el('path', {
            d:'M0 0 L10 5 L0 10 Z',fill:color
        },marker);
        el('path', {
            d,fill:'none',stroke:'transparent','stroke-width':14/view.scale,'data-arrow':o.id
        },g);
        const path=el('path', {
            d,fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':o.dash==='dashed'?'9 6':o.dash==='dotted'?'2 5':'none','stroke-linecap':'round','pointer-events':'none',...(o.tip!=='none'? {
                'marker-end':`url(#tip-${o.id})`
            }
            : {
            })
        },g);
        if(o.label) {
            const p=path.getPointAtLength(path.getTotalLength()/2),size=o.labelSize||14;
            const t=el('text', {
                x:p.x,y:p.y,'text-anchor':'middle','dominant-baseline':'central','font-size':size,class:'arrow-label'
            },g);
            t.textContent=o.label;
            const b=t.getBBox(),r=el('rect', {
                x:b.x-5,y:b.y-3,width:b.width+10,height:b.height+6,rx:4,fill:'#202020'
            },g);
            g.insertBefore(r,t)
        }
        return g
    }
    function drawSelection() {
        selection.replaceChildren();
        const r=6/view.scale;
        for(const id of selected) {
            const o=find(id);
            if(!o)continue;
            if(o.kind==='arrow') {
                const path=el('path', {
                    d:arrowPath(o),fill:'none',stroke:'#429bea','stroke-width':5/view.scale,opacity:.35,'pointer-events':'none'
                },selection);
                for(const end of ['a','b']) {
                    const actual=endpoint(o[end]),direction=vector(o[end],{x:0,y:0});
                    const p=o[end].node?{x:actual.x+direction.x*20/view.scale,y:actual.y+direction.y*20/view.scale}:actual;
                    el('line',{x1:actual.x,y1:actual.y,x2:p.x,y2:p.y,stroke:'#429bea','stroke-width':1/view.scale,'pointer-events':'none'},selection);
                    el('rect', {
                        x:p.x-r,y:p.y-r,width:2*r,height:2*r,rx:1/view.scale,class:'handle','data-end':end,'data-id':id
                    },selection)
                }
                const p=path.getPointAtLength(path.getTotalLength()/2);
                for(const [action,text,offset,title]of [['remove','−',-15,t('Delete')],['label','T',15,t('Label arrow')]]){
                    const cx=p.x+offset/view.scale,cy=p.y-28/view.scale;
                    const button=el('g',{['data-'+action]:id,cursor:'pointer',role:'button',tabindex:0,'aria-label':title},selection);
                    el('title',{},button).textContent=title;
                    el('circle',{cx,cy,r:12/view.scale,fill:'var(--workspace-button)',stroke:'var(--primary-color)','stroke-width':1/view.scale},button);
                    el('text',{x:cx,y:cy,'text-anchor':'middle','dominant-baseline':'central','font-size':14/view.scale,'font-family':'system-ui',fill:'var(--workspace-text)','pointer-events':'none'},button).textContent=text;
                    button.addEventListener('keydown',event=>{event.stopPropagation();if(event.key==='Enter'||event.key===' '){event.preventDefault();if(action==='label')editArrowLabel(o);else{selected=new Set([id]);removeSelected();}}});
                }
                continue
            }
            const g=el('g', {
                transform:`translate(${o.x} ${o.y}) rotate(${o.rotation} ${o.w/2} ${o.h/2})`
            },selection);
            el('rect', {
                width:o.w,height:o.h,fill:'none',stroke:'#429bea','stroke-width':1/view.scale,'pointer-events':'none'
            },g);
            for(const [key,x,y]of [['nw',0,0],['ne',o.w,0],['se',o.w,o.h],['sw',0,o.h]])el('rect', {
                x:x-r/1.5,y:y-r/1.5,width:r*1.33,height:r*1.33,class:'handle','data-resize':key,'data-id':id
            },g);
            el('path', {
                d:`M${o.w/2} 0 V${-25/view.scale}`,stroke:'#429bea','stroke-width':1/view.scale
            },g);
            el('circle', {
                cx:o.w/2,cy:-25/view.scale,r,class:'handle rotation','data-rotate':id
            },g);
            for(const side of ['top','right','bottom','left']) {
                const p=anchor(o,side);
                el('circle', {
                    cx:p.x,cy:p.y,r,class:'anchor','data-anchor':side,'data-id':id
                },selection)
            }
        }
        const attached=new Set();
        for(const id of selected){const o=find(id);if(o?.kind==='arrow')for(const end of [o.a,o.b])if(end.node)attached.add(end.node);}
        for(const id of attached){const o=find(id);if(!o||selected.has(id))continue;for(const side of ['top','right','bottom','left']){const p=anchor(o,side);el('circle',{cx:p.x,cy:p.y,r,class:'anchor','data-anchor':side,'data-id':id},selection);}}
        if(gesture?.type==='endpoint')for(const o of objects().filter(o=>o.kind!=='arrow'))for(const side of ['top','right','bottom','left']) {
            const p=anchor(o,side);
            el('circle', {
                cx:p.x,cy:p.y,r,class:'anchor','data-anchor':side,'data-id':o.id
            },selection)
        }
        if(gesture?.type==='marquee') {
            const a=gesture.start,b=gesture.last;
            el('rect', {
                x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(a.x-b.x),height:Math.abs(a.y-b.y),fill:'#429bea18',stroke:'#429bea','stroke-width':1/view.scale
            },selection)
        }
    }
    function render() {
        if(edit)return;
        cancelAnimationFrame(frame);
        frame=0;
        world.setAttribute('transform',`translate(${view.x} ${view.y}) scale(${view.scale})`);
        window.__workspaceGrid(workspace, view);
        $('#zoom-label').textContent=Math.round(view.scale*100)+'%';
        objectIndex=new Map(objects().map(o=>[o.id,o]));
        updateObstacles();
        rendering=true;
        if(renderedMapId!==data.active) {
            layer.replaceChildren();
            $('#defs').replaceChildren();
            shapeCache.clear();
            arrowCache.clear();
            renderedMapId=data.active;
        }
        const live=new Set();
        let position=0;
        for(const o of objects()) {
            live.add(o.id);
            let element;
            if(o.kind==='arrow') {
                const signature=JSON.stringify({path:arrowPath(o),stroke:o.stroke,customStyle:o.customStyle,tip:o.tip,dash:o.dash,label:o.label,labelSize:o.labelSize});
                let cached=arrowCache.get(o.id);
                if(!cached||cached.signature!==signature) {
                    if(cached)cached.element.remove();
                    document.getElementById('tip-'+o.id)?.remove();
                    cached={signature,element:renderArrow(o)};
                    arrowCache.set(o.id,cached);
                }
                element=cached.element;
                element.firstChild.setAttribute('stroke-width',14/view.scale);
            }
            else {
                const signature=JSON.stringify( {
                    kind:o.kind,icon:o.icon,iconAsset:o.kind==='icon'?doc().iconAssets[o.icon]:null,image:o.image,shape:o.shape,w:o.w,h:o.h,html:o.html,fontSize:o.fontSize,fill:o.fill,stroke:o.stroke,customStyle:o.customStyle,ankiLinks:o.ankiLinks
                });
                let cached=shapeCache.get(o.id);
                if(!cached||cached.signature!==signature) {
                    if(cached)cached.element.remove();
                    cached= {
                        signature,element:renderShape(o)
                    };
                    shapeCache.set(o.id,cached)
                }
                element=cached.element;
                element.setAttribute('transform',`translate(${o.x} ${o.y}) rotate(${o.rotation} ${o.w/2} ${o.h/2})`)
            }
            if(layer.children[position]!==element)layer.insertBefore(element,layer.children[position]||null);
            position++
        }
        for(const child of [...layer.children])if(!live.has(child.dataset.id))child.remove();
        for(const [id,cached]of shapeCache)if(!live.has(id)) {
            cached.element.remove();
            shapeCache.delete(id)
        }
        for(const [id,cached]of arrowCache)if(!live.has(id)) {
            cached.element.remove();
            document.getElementById('tip-'+id)?.remove();
            arrowCache.delete(id);
        }
        drawSelection();
        rendering=false;
        $('#empty-hint').hidden=!!objects().length;
        toolbar();
    }
    function drawSoon() {
        if(!frame)frame=requestAnimationFrame(render)
    }
    function add(kind,point) {
        if(readOnly)return;
        finishEdit();
        if(!doc())createMap();
        checkpoint();
        const p=point|| {
            x:(workspace.clientWidth/2-view.x)/view.scale,y:(workspace.clientHeight/2-view.y)/view.scale
        };
        const o= {
            id:uid(),kind:kind==='text'?'text':'shape',shape:SHAPES[kind]?kind:'rect',x:p.x-90,y:p.y-50,w:['square','circle'].includes(kind)?120:180,h:['square','circle'].includes(kind)?120:100,rotation:0,html:'',fontSize:20,fill:'#ffffff',stroke:'#252525'
        };
        objects().push(o);
        selected=new Set([o.id]);
        setMode(mode==='select'?'select':'auto');
        changed();
        render();
        if(kind==='text')startEdit(o.id)
    }
    function mergeIconAssets(batch,definitions,licenseText) {
        const icons=batch.filter(o=>o.kind==='icon');
        if(!icons.length)return;
        const assets=Object.assign(Object.create(null),doc().iconAssets||{}),rename=new Map();
        for(const o of icons){
            if(rename.has(o.icon)){o.icon=rename.get(o.icon);continue;}
            const original=o.icon,definition=definitions[original];
            if(!window.FreeMapIcons.valid(definition))throw Error(t('Invalid icon data.'));
            let key=original;
            if(Object.hasOwn(assets,key)&&JSON.stringify(assets[key])!==JSON.stringify(definition))key='icon-'+uid();
            assets[key]=clone(definition);rename.set(original,key);o.icon=key;
        }
        if(Object.keys(assets).length>512)throw Error(t('Too many different icons in this map.'));
        const previous=doc().iconLicense||'';
        const combined=licenseText&&!previous.includes(licenseText)?[previous,licenseText].filter(Boolean).join('\n\n'):previous;
        if(combined.length>16000)throw Error(t('Invalid icon data.'));
        doc().iconAssets=assets;doc().iconLicense=combined;
    }
    function pickIcon(replace=null) {
        if(readOnly)return;
        finishEdit();
        const mapId=data.active;
        $('#add-menu').open=false;
        window.FreeMapIcons.pick((icon,color)=>{
            if(readOnly||mapId!==data.active||(replace&&!objects().includes(replace)))return;
            if(!doc())createMap();
            mutate(()=>{
                const definition={name:icon.name,nodes:icon.nodes};
                const item={id:uid(),kind:'icon',icon:icon.id,x:(workspace.clientWidth/2-view.x)/view.scale-48,y:(workspace.clientHeight/2-view.y)/view.scale-48,w:96,h:96,rotation:0,stroke:color,fill:'none',customStyle:true,shape:'square',html:'',fontSize:20};
                mergeIconAssets([item],{[icon.id]:definition},window.FreeMapIcons.license);
                if(replace){replace.icon=item.icon;replace.stroke=color;}
                else{objects().push(item);selected=new Set([item.id]);}
            });
        },replace?.stroke);
    }
    $('#add-icon').onclick=()=>pickIcon();
    function setMode(m) {
        finishEdit();
        mode=m;
        workspace.className=m;
        document.querySelectorAll('[data-mode]').forEach(b=>{ b.classList.toggle('active',b.dataset.mode===m); b.setAttribute('aria-pressed',String(b.dataset.mode===m)); });
        $('#add-menu').open=false
    }
    function bounds() {
        let pts=[];
        for(const o of objects()) {
            if(o.kind==='arrow') {
                const a=endpoint(o.a),b=endpoint(o.b);
                pts.push(a,b);
                const element=layer.querySelector(`[data-id="${o.id}"]`);
                if(element) {
                    const r=element.getBBox();
                    pts.push( {
                        x:r.x,y:r.y
                    }, {
                        x:r.x+r.width,y:r.y+r.height
                    })
                }
            }
            else for(const [x,y]of [[o.x,o.y],[o.x+o.w,o.y],[o.x+o.w,o.y+o.h],[o.x,o.y+o.h]])pts.push(rotatePoint(x,y,o.x+o.w/2,o.y+o.h/2,o.rotation))
        }
        if(!pts.length)return null;
        return {
            left:Math.min(...pts.map(p=>p.x)),right:Math.max(...pts.map(p=>p.x)),top:Math.min(...pts.map(p=>p.y)),bottom:Math.max(...pts.map(p=>p.y))
        }
    }
    function fit(rescale,bottomPadding=60) {
        finishEdit();
        const b=bounds();
        if(!b)return;
        const w=workspace.clientWidth,h=workspace.clientHeight;
        if(rescale)view.scale=Math.max(.05,Math.min(2,(w-130)/Math.max(1,b.right-b.left),(h-60-bottomPadding)/Math.max(1,b.bottom-b.top)));
        view.x=w/2-(b.left+b.right)/2*view.scale+20;
        view.y=(h+60-bottomPadding)/2-(b.top+b.bottom)/2*view.scale;
        saveView();
        render()
    }
    function zoom(f,cx=workspace.clientWidth/2,cy=workspace.clientHeight/2) {
        finishEdit();
        const next=Math.max(.05,Math.min(4,view.scale*f)),x=(cx-view.x)/view.scale,y=(cy-view.y)/view.scale;
        view.x=cx-x*next;
        view.y=cy-y*next;
        view.scale=next;
        saveView();
        render()
    }
    function saveView() {
        if(doc()) {
            doc().view=clone(view);
            changed()
        }
    }
    function removeSelected() {
        if(readOnly||!selected.size)return;
        finishEdit();
        checkpoint();
        const removing=new Set(selected);
        for(const o of objects())if(o.kind==='arrow')for(const k of ['a','b'])if(removing.has(o[k].node))o[k]=endpoint(o[k]);
        doc().objects=objects().filter(o=>!removing.has(o.id));
        selected.clear();
        changed();
        render()
    }
    function copy() {
        finishEdit();
        if(!selected.size)return;
        const ids=new Set(selected);
        for(const o of objects())if(o.kind==='arrow'&&ids.has(o.a.node)&&ids.has(o.b.node))ids.add(o.id);
        clipboard=clone(objects().filter(o=>ids.has(o.id)));
        clipboardIcons=window.FreeMapIcons.collect(doc(),clipboard);
        clipboardLicense=doc().iconLicense||'';
        for(const o of clipboard)if(o.kind==='arrow')for(const k of ['a','b'])if(o[k].node&&!ids.has(o[k].node))o[k]=endpoint(o[k]);
    }
    function paste() {
        if(!clipboard?.length)return;
        const images=[...objects(),...clipboard].filter(o=>o.image);
        if(images.length>40||images.reduce((s,o)=>s+(o.imageWidth||1600)*(o.imageHeight||1600),0)>24000000){message(t('Image budget exceeded (40 images / 24 megapixels).'));return;}
        finishEdit();
        checkpoint();
        const mapping=new Map(clipboard.map(o=>[o.id,uid()])),batch=clone(clipboard);
        mergeIconAssets(batch,clipboardIcons,clipboardLicense);
        for(const o of batch) {
            o.id=mapping.get(o.id);
            if(o.kind==='arrow') {
                for(const k of ['a','b'])if(o[k].node)o[k].node=mapping.get(o[k].node);
                else {
                    o[k].x+=25;
                    o[k].y+=25
                }
            }
            else {
                o.x+=25;
                o.y+=25
            }
        }
        objects().push(...batch);
        selected=new Set(batch.map(o=>o.id));
        clipboard=clone(batch);
        clipboardIcons=window.FreeMapIcons.collect(doc(),batch);
        clipboardLicense=doc().iconLicense||'';
        changed();
        render()
    }
    function duplicate() {
        copy();
        paste()
    }
    function mutate(fn) {
        if(readOnly)return;
        finishEdit();
        checkpoint();
        fn();
        changed();
        render()
    }
    function actionButton(parent,label,title,fn) {
        const b=document.createElement('button');
        b.textContent=label;
        b.title=title||label;
        b.onclick=fn;
        parent.append(b);
        return b
    }
    function selectControl(parent,title,values,value,fn) {
        const s=document.createElement('select');
        s.title=title;
        s.setAttribute('aria-label',title);
        for(const [key,label]of Object.entries(values)) {
            const o=document.createElement('option');
            o.value=key;
            o.textContent=label;
            s.append(o)
        }
        s.value=value;
        s.onchange=()=>fn(s.value);
        parent.append(s);
        return s
    }
    function colorControl(parent,title,value,fn) {
        const l=document.createElement('label');
        l.append(document.createTextNode(title));
        const c=document.createElement('input');
        c.type='color';
        c.value=/^#[\da-f]{6}$/i.test(value)?value:'#ffffff';
        c.title=title;
        c.onchange=()=>fn(c.value);
        l.append(c);
        parent.append(l)
    }
    function rememberStyle(o) {
        o.customStyle=true;
        recent=[ {
            stroke:o.stroke,fill:o.fill,customStyle:true
        },...recent.filter(s=>s.stroke!==o.stroke||s.fill!==o.fill)].slice(0,6)
    }
    let lastLabelEdit=null,labelEditing=null;
    const labelDialog=$('#arrow-label-dialog'),labelInput=$('#arrow-label-input'),labelSize=$('#arrow-label-size');
    function labelPreview(){const text=$('#arrow-label-preview-text');text.textContent=labelInput.value||t('Arrow label');text.style.fontSize=Math.min(32,+labelSize.value||14)+'px';text.style.opacity=labelInput.value?'1':'.5';}
    function editArrowLabel(o) {
        if(readOnly||!o||labelDialog.open)return;
        finishEdit();
        labelEditing={object:o,mapId:data.active,focus:document.activeElement};
        labelInput.value=o.label||'';
        labelSize.replaceChildren();
        for(const size of [...new Set([8,10,12,14,16,18,20,24,28,32,40,48,56,64,72,o.labelSize||14])].sort((a,b)=>a-b))labelSize.add(new Option(size+' px',size));
        labelSize.value=String(o.labelSize||14);labelPreview();
        labelDialog.showModal();labelInput.focus();labelInput.select();
        lastLabelEdit={id:o.id,time:Date.now()};
    }
    labelInput.addEventListener('input',labelPreview);labelSize.addEventListener('change',labelPreview);
    $('#arrow-label-close').onclick=$('#arrow-label-cancel').onclick=()=>labelDialog.close();
    labelDialog.addEventListener('click',event=>{if(event.target===labelDialog){const r=labelDialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)labelDialog.close();}});
    $('#arrow-label-form').onsubmit=event=>{
        event.preventDefault();const state=labelEditing;
        if(state&&!readOnly&&data.active===state.mapId&&objects().includes(state.object)){
            const label=labelInput.value,size=Math.max(8,Math.min(72,+labelSize.value||14));
            if(label!==state.object.label||size!==state.object.labelSize)mutate(()=>{state.object.label=label;state.object.labelSize=size;});
        }
        labelDialog.close();
    };
    labelDialog.addEventListener('close',()=>{const state=labelEditing;labelEditing=null;if(state){lastLabelEdit={id:state.object.id,time:Date.now()};if(state.focus?.isConnected)state.focus.focus();}});
    function toolbar() {
        const bar=$('#object-toolbar');
        bar.replaceChildren();
        bar.hidden=!selected.size||!!gesture||!!edit;
        if(bar.hidden)return;
        const o=find([...selected][0]);
        if(!o)return;
        const p=o.kind==='arrow'?endpoint(o.a): {
            x:o.x,y:o.y
        };
        bar.style.left=Math.max(8,Math.min(workspace.clientWidth-240,p.x*view.scale+view.x))+'px';
        bar.style.top=Math.max(8,Math.min(workspace.clientHeight-80,p.y*view.scale+view.y-64))+'px';
        if(selected.size===1&&!['arrow','image','icon'].includes(o.kind)) {
            if(o.kind==='shape')selectControl(bar,t("Shape"),SHAPES,o.shape,v=>mutate(()=> {
                o.shape=v;
                if(['square','circle'].includes(v)) {
                    o.w=o.h=Math.max(o.w,o.h)
                }
            }));
            actionButton(bar,'T',t("Edit text"),()=>startEdit(o.id));
            const details=document.createElement('details'),summary=document.createElement('summary');
            summary.textContent='◐';
            summary.title=t("Border and fill");
            details.append(summary);
            const pop=document.createElement('div');
            pop.className='popover';
            colorControl(pop,t("Border"),o.stroke,v=>mutate(()=> {
                o.stroke=v;
                rememberStyle(o)
            }));
            colorControl(pop,t("Fill"),o.fill,v=>mutate(()=> {
                o.fill=v;
                rememberStyle(o)
            }));
            actionButton(pop,t("No fill"),t("Transparent fill"),()=>mutate(()=> {
                o.fill='none';
                rememberStyle(o)
            }));
            const label=document.createElement('p');
            label.textContent=t("Recently used");
            pop.append(label);
            const row=document.createElement('div');
            row.className='recent-styles';
            for(const s of recent) {
                const b=actionButton(row,'',t("Apply style"),()=>mutate(()=>Object.assign(o,s)));
                b.style.background=s.fill==='none'?'transparent':s.fill;
                b.style.borderColor=s.stroke
            }
            pop.append(row);
            details.append(pop);
            bar.append(details)
        }
        if(selected.size===1&&o.kind==='icon') {
            actionButton(bar,t('Change icon'),t('Change icon'),()=>pickIcon(o));
            colorControl(bar,t('Color'),o.stroke,value=>mutate(()=>{o.stroke=value;o.customStyle=true;}));
        }
        if(selected.size===1&&o.kind==='arrow') {
            selectControl(bar,t("Arrow route"), {
                rounded:t("Rounded corners"),angle:t("Right angles"),curve:t("Curved"),straight:t("Straight")
            },o.route,v=>mutate(()=>o.route=v));
            colorControl(bar,t("Color"),o.stroke,v=>mutate(()=>{o.stroke=v;o.customStyle=true;}));
            const d=document.createElement('details'),s=document.createElement('summary');
            s.textContent=t("Style");
            d.append(s);
            const p=document.createElement('div');
            p.className='popover';
            selectControl(p,t("Arrowhead"), {
                triangle:t("Triangle"),open:t("Open"),dot:t("Dot"),none:t("None")
            },o.tip||'triangle',v=>mutate(()=>o.tip=v));
            selectControl(p,t('Line'), {
                solid:t("Solid"),dashed:t("Dashed"),dotted:t("Dotted")
            },o.dash||'solid',v=>mutate(()=>o.dash=v));
            actionButton(bar,t("Label"),t("Label arrow"),()=>editArrowLabel(o));
            const l=document.createElement('label');
            l.textContent=t("Font size ");
            const n=document.createElement('input');
            n.type='number';
            n.min=8;
            n.max=72;
            n.value=o.labelSize||14;
            n.style.width='55px';
            n.onchange=()=>mutate(()=>o.labelSize=Math.max(8,Math.min(72,+n.value||14)));
            l.append(n);
            p.append(l);
            d.append(p);
            bar.append(d)
        }
        if(selected.size===1&&o.kind!=='arrow')actionButton(bar,t('Link Card'),t('Link Card'),()=>editAnkiLinks(o));
        const details=document.createElement('details'),summary=document.createElement('summary');
        summary.textContent='•••';
        summary.title=t("Object actions");
        details.append(summary);
        const menu=document.createElement('div');
        menu.className='popover';
        for(const [label,fn]of [[t("Bring forward"),()=>reorder(1)],[t("Bring to front"),()=>reorder(Infinity)],[t("Send backward"),()=>reorder(-1)],[t("Send to back"),()=>reorder(-Infinity)],[t("Copy"),copy],[t("Duplicate"),duplicate],[t('Delete'),removeSelected]])actionButton(menu,label,label,fn);
        details.append(menu);
        bar.append(details);
        const points=o.kind==='arrow'?[endpoint(o.a),endpoint(o.b)]:[[o.x,o.y],[o.x+o.w,o.y],[o.x+o.w,o.y+o.h],[o.x,o.y+o.h]].map(([x,y])=>rotatePoint(x,y,o.x+o.w/2,o.y+o.h/2,o.rotation));
        const top=Math.min(...points.map(p=>p.y))*view.scale+view.y,bottom=Math.max(...points.map(p=>p.y))*view.scale+view.y;
        bar.style.left=Math.max(8,Math.min(workspace.clientWidth-bar.offsetWidth-8,p.x*view.scale+view.x))+'px';
        const above=top-bar.offsetHeight-45;
        bar.style.top=Math.max(8,Math.min(workspace.clientHeight-bar.offsetHeight-8,above>=8?above:bottom+(o.ankiLinks?.length?45:20)))+'px'
    }
    function reorder(direction) {
        mutate(()=> {
            let arr=objects();
            if(!Number.isFinite(direction)) {
                const chosen=arr.filter(o=>selected.has(o.id)),others=arr.filter(o=>!selected.has(o.id));
                doc().objects=direction>0?[...others,...chosen]:[...chosen,...others]
            }
            else {
                const indices=arr.map((o,i)=>selected.has(o.id)?i:-1).filter(i=>i>=0);
                if(direction>0)indices.reverse();
                for(const i of indices) {
                    const j=i+direction;
                    if(j>=0&&j<arr.length&&!selected.has(arr[j].id))[arr[i],arr[j]]=[arr[j],arr[i]]
                }
            }
        })
    }
    function startEdit(id) {
        if(['image','icon'].includes(find(id)?.kind))return;
        finishEdit();
        const o=find(id);
        if(!o||o.kind==='arrow'||readOnly)return;
        checkpoint();
        selected=new Set([id]);
        render();
        const group=layer.querySelector(`[data-id="${id}"]`);
        group.style.visibility='hidden';
        const overlay=document.createElement('div');
        overlay.className='text-editor-layer';
        overlay.style.cssText=`position:absolute;left:${view.x}px;top:${view.y}px;transform:scale(${view.scale});transform-origin:0 0;z-index:60;`;
        const box=document.createElement('div');
        box.className='shape-text editing';
        box.contentEditable='true';
        box.style.cssText=`position:absolute;left:${o.x}px;top:${o.y}px;width:${o.w}px;height:${o.h}px;transform:rotate(${o.rotation}deg);font-size:${o.fontSize||20}px;`;
        box.style.color=(darkDefault(o)||darkText(o))?'#ffffff':'#303030';
        box.style.background=(darkDefault(o)||darkText(o))?'#2c2c2c':o.fill==='none'?'#ffffff':o.fill;
        box.innerHTML=safeHTML(o.html);
        overlay.append(box);
        workspace.append(overlay);
        edit= {
            id,box,overlay,group,before:o.html,range:null
        };
        $('#object-toolbar').hidden=true;
        $('#text-toolbar').hidden=false;
        $('#text-size').value=o.fontSize||20;
        selection.replaceChildren();
        box.focus();
        const r=document.createRange();
        r.selectNodeContents(box);
        r.collapse(false);
        getSelection().removeAllRanges();
        getSelection().addRange(r);
        box.addEventListener('input',()=> {
            o.html=safeHTML(box.innerHTML);
            changed()
        });
        box.addEventListener('paste',e=> {
            e.preventDefault();
            document.execCommand('insertText',false,e.clipboardData.getData('text/plain'))
        });
        box.addEventListener('pointerdown',e=>e.stopPropagation());
    }
    function finishEdit() {
        if(!edit)return;
        const e=edit,o=find(e.id);
        if(o) {
            o.html=safeHTML(e.box.innerHTML);
            if(o.html!==e.before)changed()
        }
        e.overlay.remove();
        e.group.style.visibility='';
        edit=null;
        $('#text-toolbar').hidden=true;
        render()
    }
    function keepRange() {
        if(!edit)return;
        const s=getSelection();
        if(s.rangeCount&&edit.box.contains(s.anchorNode)&&edit.box.contains(s.focusNode)) {
            edit.range=s.getRangeAt(0).cloneRange();
            for(const button of document.querySelectorAll('[data-format]')) {
                const active=document.queryCommandState(button.dataset.format);
                button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
            }
            const anchor=s.anchorNode.nodeType===1?s.anchorNode:s.anchorNode.parentElement;
            const style=getComputedStyle(anchor);
            if(!document.activeElement?.closest('#text-toolbar')) {
                $('#text-size').value=Math.round(parseFloat(style.fontSize)||find(edit.id).fontSize||20);
                const rgb=style.color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                if(rgb){const hex='#'+rgb.slice(1,4).map(n=>(+n).toString(16).padStart(2,'0')).join('');$('#text-color').value=hex;$('#text-toolbar').style.setProperty('--text-swatch',hex);}
            }
            const align=style.textAlign;
            $('#text-align').value=({left:'justifyLeft',start:'justifyLeft',center:'justifyCenter',right:'justifyRight',end:'justifyRight',justify:'justifyFull'})[align]||'justifyCenter';
        }
    }
    document.addEventListener('selectionchange',keepRange);
    function restoreRange() {
        if(!edit)return;
        edit.box.focus();
        if(edit.range) {
            const s=getSelection();
            s.removeAllRanges();
            s.addRange(edit.range)
        }
    }
    function format(command,value) {
        if(!edit||readOnly)return;
        if(command==='foreColor')find(edit.id).customStyle=true;
        restoreRange();
        document.execCommand('styleWithCSS',false,true);
        document.execCommand(command,false,value);
        find(edit.id).html=safeHTML(edit.box.innerHTML);
        changed();
        keepRange()
    }
    $('#text-toolbar').addEventListener('pointerdown',()=>keepRange());
    $('#text-toolbar').addEventListener('mousedown',e=> {
        if(e.target.closest('button[data-format]'))e.preventDefault()
    });
    document.querySelectorAll('[data-format]').forEach(b=>b.onclick=()=>format(b.dataset.format));
    $('#text-size').onchange=()=> {
        if(!edit)return;
        const size=Math.max(8,Math.min(96,+$('#text-size').value||20));
        restoreRange();
        const sel=getSelection();
        if(sel.rangeCount&&!sel.isCollapsed) {
            document.execCommand('styleWithCSS',false,false);
            document.execCommand('fontSize',false,'7');
            for(const n of edit.box.querySelectorAll('font[size="7"]')) {
                n.removeAttribute('size');
                n.style.fontSize=size+'px'
            }
            document.execCommand('styleWithCSS',false,true);
        }
        else {
            find(edit.id).fontSize=size;
            edit.box.style.fontSize=size+'px'
        }
        find(edit.id).html=safeHTML(edit.box.innerHTML);
        changed();
        keepRange()
    };
    $('#text-align').onchange=e=>format(e.target.value);
    $('#text-color').onchange=e=>{format('foreColor',e.target.value);$('#text-toolbar').style.setProperty('--text-swatch',e.target.value);};
    $('#text-highlight').onchange=e=>{format('hiliteColor',e.target.value);$('#text-toolbar').style.setProperty('--highlight-swatch',e.target.value);};
    $('#text-done').onclick=finishEdit;
    scene.addEventListener('dblclick',e=> {
        const id=e.target.closest('[data-id]')?.dataset.id;
        if(id) {
            if(find(id)?.kind==='arrow') {
                if(lastLabelEdit?.id!==id||Date.now()-lastLabelEdit.time>500)editArrowLabel(find(id));
            }
            else startEdit(id)
        }
    });
    scene.addEventListener('pointerdown',e=> {
        if(readOnly||e.button>1)return;
        const target=e.target;
        finishEdit();
        const p=localPoint(e),node=target.closest('[data-id]'),id=node?.dataset.id;
        if(lastClick?.id!==id)lastClick=null;
        if(target.closest('[data-label]')){e.preventDefault();editArrowLabel(find(target.closest('[data-label]').dataset.label));return;}
        if(target.closest('[data-remove]')) {
            selected=new Set([target.closest('[data-remove]').dataset.remove]);
            removeSelected();
            return
        }
        scene.setPointerCapture(e.pointerId);
        const hitObject=target.closest('[data-id],[data-rotate],[data-remove]');
        if(space||mode==='hand'||e.button===1||(mode==='auto'&&!hitObject&&!e.shiftKey)) {
            workspace.classList.add('panning');
            gesture= {
                type:'pan',start: {
                    x:e.clientX,y:e.clientY
                },view:clone(view),clearOnClick:mode==='auto'&&!hitObject&&!space&&e.button===0
            };
            return
        }
        const rotate=target.closest('[data-rotate]');
        if(rotate) {
            const o=find(rotate.dataset.rotate);
            gesture= {
                type:'rotate',id:o.id,original:clone(o),start:p
            };
            return
        }
        if(target.dataset.resize) {
            gesture= {
                type:'resize',id,corner:target.dataset.resize,original:clone(find(id)),start:p
            };
            return
        }
        if(target.dataset.end) {
            gesture= {
                type:'endpoint',id,end:target.dataset.end,start:p
            };
            return
        }
        if(target.dataset.anchor||mode==='arrow') {
            if(!doc())createMap();
            checkpoint();
            const o= {
                id:uid(),kind:'arrow',a:target.dataset.anchor? {
                    node:id,side:target.dataset.anchor
                }
                :snap(p),b:p,route:'rounded',stroke:'#252525',tip:'triangle',dash:'solid',label:'',labelSize:14
            };
            objects().push(o);
            selected=new Set([o.id]);
            gesture= {
                type:'endpoint',id:o.id,end:'b',start:p,newArrow:true
            };
            drawSoon();
            return
        }
        if(id) {
            if(e.shiftKey) {
                if(selected.has(id))selected.delete(id);
                else selected.add(id)
            }
            else if(!selected.has(id))selected=new Set([id]);
            gesture= {
                type:'move',clicked:id,start:p,originals:clone(objects().filter(o=>selected.has(o.id)))
            };
            render()
        }
        else {
            if(!e.shiftKey)selected.clear();
            gesture= {
                type:'marquee',start:p,last:p,previous:new Set(selected)
            };
            render()
        }
    });
    scene.addEventListener('pointermove',e=> {
        if(!gesture)return;
        const p=localPoint(e),g=gesture;
        const distance=g.type==='pan'?Math.hypot(e.clientX-g.start.x,e.clientY-g.start.y):Math.hypot(p.x-g.start.x,p.y-g.start.y)*view.scale;
        if(distance>2) {
            if(!g.moved&&!g.newArrow&&!['pan','marquee'].includes(g.type)) {
                checkpoint();
                g.recorded=true
            }
            g.moved=true;
            lastClick=null;
        }
        if(!g.moved)return;
        if(g.type==='pan') {
            view.x=g.view.x+e.clientX-g.start.x;
            view.y=g.view.y+e.clientY-g.start.y
        }
        if(g.type==='move') {
            const dx=p.x-g.start.x,dy=p.y-g.start.y;
            for(const original of g.originals) {
                const o=find(original.id);
                if(!o)continue;
                if(o.kind==='arrow') {
                    for(const k of ['a','b'])if(!original[k].node)o[k]= {
                        x:original[k].x+dx,y:original[k].y+dy
                    }
                }
                else {
                    o.x=original.x+dx;
                    o.y=original.y+dy
                }
            }
        }
        if(g.type==='endpoint') {
            const o=find(g.id);
            o[g.end]=snap(p);
        }
        if(g.type==='rotate') {
            const o=find(g.id),a=g.original,c= {
                x:a.x+a.w/2,y:a.y+a.h/2
            };
            o.rotation=a.rotation+(Math.atan2(p.y-c.y,p.x-c.x)-Math.atan2(g.start.y-c.y,g.start.x-c.x))*180/Math.PI;
            if(e.shiftKey)o.rotation=Math.round(o.rotation/15)*15
        }
        if(g.type==='resize') {
            const o=find(g.id),a=g.original,c= {
                x:a.x+a.w/2,y:a.y+a.h/2
            },q=rotatePoint(p.x,p.y,c.x,c.y,-a.rotation),start=rotatePoint(g.start.x,g.start.y,c.x,c.y,-a.rotation),sx=g.corner.includes('e')?1:-1,sy=g.corner.includes('s')?1:-1;
            let w=Math.max(32,a.w+sx*(q.x-start.x)),h=Math.max(26,a.h+sy*(q.y-start.y));
            if(e.shiftKey||['circle','square'].includes(o.shape)) {
                const ratio=a.w/a.h;
                h=w/ratio
            }
            const center=rotatePoint(c.x+sx*(w-a.w)/2,c.y+sy*(h-a.h)/2,c.x,c.y,a.rotation);
            o.w=w;
            o.h=h;
            o.x=center.x-w/2;
            o.y=center.y-h/2
        }
        if(g.type==='marquee') {
            g.last=p;
            const left=Math.min(p.x,g.start.x),right=Math.max(p.x,g.start.x),top=Math.min(p.y,g.start.y),bottom=Math.max(p.y,g.start.y);
            selected=new Set(g.previous);
            for(const o of objects()) {
                const center=o.kind==='arrow'?endpoint(o.a): {
                    x:o.x+o.w/2,y:o.y+o.h/2
                };
                if(center.x>=left&&center.x<=right&&center.y>=top&&center.y<=bottom)selected.add(o.id)
            }
        }
        drawSoon()
    });
    function endGesture(cancel=false) {
        workspace.classList.remove('panning');
        if(!gesture)return;
        const g=gesture;
        gesture=null;
        if(!cancel&&g.type==='move'&&!g.moved) {
            const now=Date.now();
            if(lastClick?.id===g.clicked&&now-lastClick.time<450) {
                lastClick=null;
                const object=find(g.clicked);
                if(object?.kind==='arrow')editArrowLabel(object);else startEdit(g.clicked);
                return
            }
            lastClick= {
                id:g.clicked,time:now
            }
        }
        if(cancel&&(g.recorded||g.newArrow)) {
            if(undo.length) {
                const previous=JSON.parse(undo.pop());
                data.maps[data.maps.findIndex(m=>m.id===data.active)]=previous;
                selected.clear()
            }
        }
        else if(g.newArrow&&!g.moved) {
            doc().objects=objects().filter(o=>o.id!==g.id);
            selected.clear()
        }
        else if(g.type==='pan') {
            if(!cancel&&!g.moved&&g.clearOnClick)selected.clear();
            saveView();
        }
        else if(g.type!=='marquee'&&(g.moved||g.newArrow))changed();
        render()
    }
    scene.addEventListener('pointerup',()=>endGesture());
    scene.addEventListener('pointercancel',()=>endGesture(true));
    scene.addEventListener('lostpointercapture',()=>endGesture());
    workspace.addEventListener('wheel',e=> {
        if(e.target.closest('.popover')||edit)return;
        e.preventDefault();
        const r=workspace.getBoundingClientRect();
        zoom(Math.exp(-e.deltaY*.001),e.clientX-r.left,e.clientY-r.top)
    }, {
        passive:false
    });
    for(const [key,label]of Object.entries(SHAPES)) {
        const b=actionButton($('#shape-palette'),label,label,()=> {
            add(key);
            $('#add-menu').open=false
        });
        const previews={rect:'<rect x="3" y="6" width="22" height="16" rx="1"/>',square:'<rect x="6" y="6" width="16" height="16" rx="1"/>',rounded:'<rect x="3" y="6" width="22" height="16" rx="5"/>',oval:'<ellipse cx="14" cy="14" rx="11" ry="8"/>',circle:'<circle cx="14" cy="14" r="9"/>',squircle:'<rect x="5" y="5" width="18" height="18" rx="7"/>',diamond:'<path d="M14 3 25 14 14 25 3 14Z"/>',triangle:'<path d="m14 4 11 20H3Z"/>'};
        const title=document.createElement('span');title.textContent=label;
        b.replaceChildren();
        const preview=document.createElementNS(NS,'svg');preview.setAttribute('viewBox','0 0 28 28');preview.setAttribute('aria-hidden','true');preview.innerHTML=previews[key];b.append(preview,title);
        b.draggable=true;
        b.dataset.shape=key;
        b.addEventListener('dragstart',e=> {
            e.dataTransfer.setData('application/x-synapse-shape',key);
            e.dataTransfer.effectAllowed='copy'
        })
    }
    workspace.addEventListener('dragover',e=> {
        if([...e.dataTransfer.types].includes('application/x-synapse-shape'))e.preventDefault()
    });
    workspace.addEventListener('drop',e=> {
        const shape=e.dataTransfer.getData('application/x-synapse-shape');
        if(SHAPES[shape]) {
            e.preventDefault();
            add(shape,localPoint(e));
            $('#add-menu').open=false
        }
    });
    document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=> {
        add(b.dataset.add);
        $('#add-menu').open=false
    });
    document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{setMode(b.dataset.mode);$('#add-menu').open=false;});
    $('#add-image').onclick=()=> {
        if(readOnly)return;
        const active=data.active;
        $('#add-menu').open=false;
        window.workspacePickImage(image=>{
            if(data.active!==active)return;
            if(!window.workspaceCanAddImage(objects(),image)) {message(t('Image budget exceeded (40 images / 24 megapixels).'));return;}
            mutate(()=>{const width=Math.min(320,image.width),height=width*image.height/image.width;
                const o={id:uid(),kind:'image',image:image.image,imageWidth:image.width,imageHeight:image.height,x:(workspace.clientWidth/2-view.x)/view.scale-width/2,y:(workspace.clientHeight/2-view.y)/view.scale-height/2,w:width,h:height,rotation:0,stroke:'#cccccc',html:'',shape:'rect',fontSize:20};objects().push(o);selected=new Set([o.id]);});
        });
    };
    window.__workspaceDocument=()=>{finishEdit();return doc()?window.FreeMapIcons.portable(doc()):null;};
    window.__workspaceImported=payload=>{
        if(readOnly)return;
        try{const imported=normalize(payload);for(const m of imported.maps){m.id=uid();m.name+=' · '+t('Import');data.maps.push(m);}if(imported.maps.length)selectMap(imported.maps[0].id);message(t('FreeMap imported.'));}catch(e){message(e.message);}
    };
    $('#new-map').onclick=()=> {
        if(readOnly)return;
        const name=prompt(t("New FreeMap name"),t("New FreeMap"));
        if(name?.trim())createMap(name.trim())
    };
    $('#map-select').onchange=e=>selectMap(e.target.value);
    $('#undo').onclick=()=>travel(undo,redo);
    $('#redo').onclick=()=>travel(redo,undo);
    $('#zoom-in').onclick=()=>zoom(1.2);
    $('#zoom-out').onclick=()=>zoom(1/1.2);
    $('#fit').onclick=()=>fit(true);
    $('#center').onclick=()=>fit(false);
    window.__workspaceCenterView=()=>fit(false);
    function exportMap() {
        finishEdit();
        if(!doc())return;
        if(window.__ROADMAP_HOSTED__) {
            window.__synapseMindmapCommand('roadmap-export');
            return;
        }
        if(objects().some(o=>o.image)){message(t('Images require Anki.'));return;}
        const blob=new Blob([JSON.stringify( {
            version:1,active:data.active,maps:[window.FreeMapIcons.portable(doc())]
        },null,2)], {
            type:'application/json'
        }),url=URL.createObjectURL(blob),a=document.createElement('a');
        a.href=url;
        a.download=(doc().name.replace(/[^\p{L}\p{N} _-]/gu,'_')||'FreeMap')+'.json';
        a.click();
        setTimeout(()=>URL.revokeObjectURL(url),1000)
    }
    document.querySelectorAll('[data-doc]').forEach(b=>b.onclick=()=> {
        const action=b.dataset.doc;
        $('#document-menu').open=false;
        if(action==='export') {
            exportMap();
            return
        }
        if(readOnly)return;
        finishEdit();
        if(action==='import') {
            if(window.__ROADMAP_HOSTED__){window.__synapseMindmapCommand('workspace-import');return;}
            $('#import-file').click();
            return
        }
        if(action==='tutorial'){createTutorial();return;}
        if(!doc())return;
        if(action==='rename') {
            const name=prompt(t("FreeMap name"),doc().name);
            if(name?.trim()) {
                checkpoint();
                doc().name=name.trim();
                list();
                changed()
            }
        }
        if(action==='duplicate') {
            const m=clone(doc());
            m.id=uid();
            m.name+=' · '+t('Copy');
            data.maps.push(m);
            selectMap(m.id)
        }
        if(action==='delete'&&confirm(t("Delete this FreeMap?"))) {
            data.maps=data.maps.filter(m=>m.id!==data.active);
            if(!data.maps.length)createMap();
            else selectMap(data.maps[0].id)
        }
    });
    $('#import-file').onchange=async e=> {
        const f=e.target.files[0];
        if(!f)return;
        try {
            if(f.size>20*1024*1024)throw Error(t("The file is larger than 20 MB."));
            const imported=normalize(JSON.parse(await f.text()));
            if(imported.maps.some(m=>m.objects.some(o=>o.image)))throw Error(t('Images require Anki.'));
            for(const m of imported.maps) {
                m.id=uid();
                m.name+=' · Import';
                data.maps.push(m)
            }
            if(imported.maps.length)selectMap(imported.maps[0].id);
            message(t("FreeMap imported."))
        }
        catch(err) {
            message(err.message)
        }
        e.target.value=''
    };
    document.addEventListener('keydown',e=> {
        if(labelDialog.open||window.FreeMapIcons.isOpen())return;
        const typing=e.target.closest('input,select,textarea,[contenteditable="true"]');
        if(typing) {
            if(e.key==='Escape') {
                finishEdit();
                e.preventDefault()
            }
            return
        }
        if(readOnly)return;
        const mod=e.ctrlKey||e.metaKey;
        if(mod&&e.key.toLowerCase()==='k'&&selected.size===1){const object=find([...selected][0]);if(object&&object.kind!=='arrow'){e.preventDefault();editAnkiLinks(object);}return;}
        if(e.code==='Space') {
            space=true;
            e.preventDefault();
            return
        }
        if(e.key==='Escape') {
            endGesture(true);
            selected.clear();
            setMode('auto');
            document.querySelectorAll('details[open]').forEach(d=>d.open=false);
            render();
            return
        }
        if(mod) {
            const key=e.key.toLowerCase();
            if(key==='z') {
                e.preventDefault();
                e.shiftKey?travel(redo,undo):travel(undo,redo)
            }
            if(key==='y') {
                e.preventDefault();
                travel(redo,undo)
            }
            if(key==='c') {
                e.preventDefault();
                copy()
            }
            if(key==='x') {
                e.preventDefault();
                copy();
                removeSelected()
            }
            if(key==='v') {
                e.preventDefault();
                paste()
            }
            if(key==='a') {
                e.preventDefault();
                selected=new Set(objects().map(o=>o.id));
                render()
            }
            if(key==='s') {
                e.preventDefault();
                scheduleSave()
            }
            return
        }
        if(e.key==='Delete'||e.key==='Backspace') {
            e.preventDefault();
            removeSelected()
        }
        if(e.key.toLowerCase()==='a')setMode('auto');
        if(e.key.toLowerCase()==='v')setMode('select');
        if(e.key.toLowerCase()==='h')setMode('hand');
        if(e.key==='Enter'&&selected.size===1)startEdit([...selected][0]);
    });
    document.addEventListener('keyup',e=> {
        if(e.code==='Space')space=false
    });
    window.addEventListener('blur',()=> {
        space=false;
        endGesture()
    });
    document.addEventListener('pointerdown',e=> {
        if(edit&&!e.target.closest('#text-toolbar')&&!edit.box.contains(e.target))finishEdit();
        document.querySelectorAll('details[open]').forEach(d=> {
            if(!d.contains(e.target))d.open=false
        })
    });
    new ResizeObserver(()=>drawSoon()).observe(workspace);
    if(window.__SYNAPSE_MM_DARK__)document.documentElement.classList.add('dark');
    if(window.__SYNAPSE_MM_ACCENT__)document.documentElement.style.setProperty('--primary-color',window.__SYNAPSE_MM_ACCENT__);
    if(!data.maps.length&&!readOnly&&window.__ROADMAP_FIRST_RUN__===true) {
        createTutorial();
    }
    else if(!data.maps.length&&!readOnly)createMap();
    else {
        view=clone(doc()?.view||view);
        list();
        render()
    }
    setMode('auto');
    updateHistory();
    window.workspaceCheckSize?.(objects(), data.active);
    if(readOnly) {
        message(window.__ROADMAP_ERROR__||t("Could not load file."),true);
        $('#new-map').disabled=true;
        $('#map-select').disabled=true
    }
    else $('#save-status').textContent=window.__ROADMAP_HOSTED__?(revision>savedRevision?t("Saving..."):t("Saved")):t("Preview");
})();
