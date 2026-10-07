/* Offline, curated Lucide icons. SVG is constructed from allowed geometry only. */
(()=>{
 'use strict';
 const NS='http://www.w3.org/2000/svg',catalog=window.FREE_MAP_ICON_CATALOG;
 const t=s=>(window.workspaceText||String)(s),clone=x=>JSON.parse(JSON.stringify(x));
 const attrs={path:['d'],line:['x1','y1','x2','y2'],polyline:['points'],polygon:['points'],circle:['cx','cy','r'],ellipse:['cx','cy','rx','ry'],rect:['x','y','width','height','rx','ry']};
 function valid(def){
  if(!def||typeof def!=='object'||Array.isArray(def)||Object.keys(def).sort().join(',')!=='name,nodes'||typeof def.name!=='string'||!def.name.length||def.name.length>100||!Array.isArray(def.nodes)||!def.nodes.length||def.nodes.length>64)return false;
  let size=0;
  for(const node of def.nodes){
   if(!Array.isArray(node)||node.length!==2)return false;
   const [tag,values]=node;
   if(!Object.hasOwn(attrs,tag)||!values||typeof values!=='object'||Array.isArray(values)||!Object.keys(values).length)return false;
   for(const [key,value] of Object.entries(values)){
    if(!attrs[tag].includes(key)&&key!=='fill')return false;
    if(typeof value!=='string'||value.length>16000)return false;size+=value.length;
    if(key==='fill'){if(!['none','currentColor'].includes(value))return false;}
    else if(key==='d'){if(!/^[MmLlHhVvCcSsQqTtAaZz0-9eE.,+\s-]{1,16000}$/.test(value))return false;}
    else if(key==='points'){if(!/^[0-9eE.,+\s-]{1,16000}$/.test(value))return false;}
    else if(!value.trim()||!Number.isFinite(Number(value))||Math.abs(Number(value))>10000)return false;
   }
  }
  return size<=32000;
 }
 function validateDocument(doc){
  const definitions=doc.iconAssets===undefined?{}:doc.iconAssets;
  if(!definitions||typeof definitions!=='object'||Array.isArray(definitions)||Object.keys(definitions).length>512)throw Error(t('Invalid icon data.'));
  for(const [key,value]of Object.entries(definitions))if(!/^[a-zA-Z0-9_-]{1,120}$/.test(key)||!valid(value))throw Error(t('Invalid icon data.'));
  for(const obj of doc.objects||[])if(obj?.kind==='icon'&&(typeof obj.icon!=='string'||!Object.hasOwn(definitions,obj.icon)))throw Error(t('Missing icon data.'));
  if(doc.iconLicense!==undefined&&(typeof doc.iconLicense!=='string'||doc.iconLicense.length>16000))throw Error(t('Invalid icon data.'));
 }
 function svg(def,color='currentColor'){
  if(!valid(def))throw Error(t('Invalid icon data.'));
  const root=document.createElementNS(NS,'svg');
  for(const [k,v]of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.8','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'}))root.setAttribute(k,v);
  root.style.color=color;
  for(const [tag,values]of def.nodes){const node=document.createElementNS(NS,tag);for(const [key,value]of Object.entries(values))node.setAttribute(key,value);root.appendChild(node);}
  return root;
 }
 function collect(doc,objects=doc.objects){
  const result=Object.create(null);
  for(const o of objects)if(o.kind==='icon')result[o.icon]=clone(doc.iconAssets[o.icon]);
  return result;
 }
 function portable(doc){
  const result=clone(doc),definitions=collect(doc);
  if(Object.keys(definitions).length){result.iconAssets=definitions;result.iconLicense=doc.iconLicense||catalog.license;}
  else{delete result.iconAssets;delete result.iconLicense;}
  return result;
 }
 const categories={
  'Medicine':['medicine','medical','health','healthcare','clinical'],
  'Science':['science','scientific','research'],
  'Learning':['learning','education','study','studying'],
  'People & Communication':['people','communication','social'],
  'Planning':['planning','organization','organisation','productivity'],
  'Everyday':['everyday','daily','lifestyle'],
  'Symbols':['symbols','symbol','signs']
 };
 const normalize=s=>String(s).toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim();
 function near(a,b){
  if(a.length<4||Math.abs(a.length-b.length)>1)return false;
  let i=0,j=0,errors=0;
  while(i<a.length&&j<b.length){if(a[i]===b[j]){i++;j++;continue;}if(++errors>1)return false;if(a.length>=b.length)i++;if(b.length>=a.length)j++;}
  return errors+(a.length-i)+(b.length-j)<=1;
 }
 const entries=catalog.icons.map(icon=>({...icon,words:normalize([icon.name,...icon.tags,...icon.categories.flatMap(c=>categories[c])].join(' ')).split(' ')}));
 function search(query,category='All'){
  const tokens=normalize(query).split(' ').filter(Boolean).slice(0,12);
  return entries.filter(icon=>category==='All'||icon.categories.includes(category)).map(icon=>{
   let score=0;
   for(const token of tokens){
    const name=normalize(icon.name).split(' '),words=icon.words;
    const hit=name.includes(token)?100:name.some(w=>w.startsWith(token))?70:words.includes(token)?50:words.some(w=>w.startsWith(token))?30:words.some(w=>near(token,w))?10:0;
    if(!hit)return null;score+=hit;
   }
   return {icon,score};
  }).filter(Boolean).sort((a,b)=>b.score-a.score||a.icon.name.localeCompare(b.icon.name)).map(r=>r.icon);
 }
 let dialog,grid,searchInput,category='All',onChoose,focusBefore,color='#429bea',timer;
 function render(){
  const found=search(searchInput.value,category);grid.replaceChildren();
  document.getElementById('icon-result-count').textContent=found.length+' '+t('Icons');
  if(!found.length){const hint=document.createElement('p');hint.className='icon-empty';hint.textContent=t('No icons found. Try another English word.');grid.append(hint);return;}
  const batch=document.createDocumentFragment();
  for(const icon of found){
   const button=document.createElement('button');button.type='button';button.className='icon-choice';button.dataset.icon=icon.id;button.title=icon.name;button.setAttribute('aria-label',icon.name);
   button.append(svg({name:icon.name,nodes:icon.nodes},color));const text=document.createElement('span');text.textContent=icon.name;button.append(text);
   button.onclick=()=>{const callback=onChoose;dialog.close();callback?.(icon,color);};batch.append(button);
  }
  grid.append(batch);
 }
 function build(){
  dialog=document.createElement('dialog');dialog.id='icon-picker';dialog.setAttribute('aria-labelledby','icon-picker-title');
  dialog.innerHTML='<header><h2 id="icon-picker-title"></h2><button id="icon-picker-close" type="button">×</button></header><div class="icon-search-row"><input id="icon-search" type="search" autocomplete="off" maxlength="100"><label class="icon-color-label"><span></span><input id="icon-insert-color" type="color"></label></div><p id="icon-search-hint"></p><div id="icon-categories"></div><div id="icon-result-count" role="status"></div><div id="icon-grid"></div><footer>Lucide · Offline SVG</footer>';
  document.body.append(dialog);
  document.getElementById('icon-picker-title').textContent=t('Icons');
  const close=document.getElementById('icon-picker-close');close.title=t('Close');close.setAttribute('aria-label',t('Close'));close.onclick=()=>dialog.close();
  searchInput=document.getElementById('icon-search');searchInput.placeholder='Search icons…';searchInput.setAttribute('aria-label','Search icons in English');searchInput.setAttribute('aria-describedby','icon-search-hint');
  document.getElementById('icon-search-hint').textContent=t('Search in English, for example heart, medicine or learning.');
  const swatch=document.getElementById('icon-insert-color');swatch.value=color;swatch.setAttribute('aria-label',t('Icon color'));swatch.parentElement.firstElementChild.textContent=t('Color');
  swatch.oninput=()=>{color=swatch.value;for(const s of grid.querySelectorAll('svg'))s.style.color=color;};
  const tabs=document.getElementById('icon-categories');tabs.setAttribute('aria-label',t('Categories'));
  for(const c of ['All',...Object.keys(categories)]){const b=document.createElement('button');b.type='button';b.textContent=c;b.setAttribute('aria-pressed',String(c===category));b.onclick=()=>{category=c;for(const other of tabs.children)other.setAttribute('aria-pressed',String(other===b));render();grid.scrollTop=0;};tabs.append(b);}
  grid=document.getElementById('icon-grid');
  searchInput.oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>{render();grid.scrollTop=0;},70);};
  dialog.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();dialog.close();}});
  dialog.addEventListener('close',()=>{clearTimeout(timer);onChoose=null;if(focusBefore?.isConnected)focusBefore.focus({preventScroll:true});});
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
 }
 function pick(callback,initialColor){if(/^#[0-9a-f]{6}$/i.test(initialColor||''))color=initialColor;if(!dialog)build();document.getElementById('icon-insert-color').value=color;onChoose=callback;focusBefore=document.activeElement;render();dialog.showModal();searchInput.focus();searchInput.select();}
 window.FreeMapIcons={valid,validateDocument,svg,collect,portable,search,pick,license:catalog.license,isOpen:()=>!!dialog?.open};
})();
