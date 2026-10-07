/* Deck Overview controls share the existing settings save/cancel transaction. */
(function(){
 let model=null;
 window.renderDeckOverviewSettings=function(data){
  const root=document.getElementById('deckOverviewOptions');root.replaceChildren();model=data;
  if(!data)return;
  const groups={};
  for(const [id,title] of [['appearance',data.labels.appearance],['indicator',data.labels.indicator]]){
   const section=document.createElement('div');section.className='group';
   const heading=document.createElement('h2');heading.className='deck-option-heading';heading.textContent=title;section.append(heading);groups[id]=section;root.append(section);
  }
  for(const field of data.fields){
   const row=document.createElement('div');row.className='row';
   const copy=document.createElement('div');copy.className='rl';const label=document.createElement('label');label.className='rt';label.htmlFor=field.key;label.textContent=field.label;copy.append(label);row.append(copy);
   const controls=document.createElement('div');controls.className='rc';let input;
   if(field.type==='choice'){
    input=document.createElement('select');input.className='field';
    for(const choice of field.choices)input.add(new Option(choice.label,String(choice.value)));
    input.value=String(data.config[field.key]);controls.append(input);
   }else if(field.type==='color'){
    input=document.createElement('input');input.type='color';input.value=data.config[field.key];input.className='deck-color';controls.append(input);
   }else if(field.type==='boolean'){
    const wrap=document.createElement('label');wrap.className='switch';input=document.createElement('input');input.type='checkbox';input.checked=!!data.config[field.key];const slider=document.createElement('span');slider.className='slider';wrap.append(input,slider);controls.append(wrap);
   }else{
    input=document.createElement('input');input.type='number';input.className='deck-number';input.min=field.key.endsWith('green')?'1':'0';input.max=field.key.endsWith('green')?'100':'99';input.step='1';input.value=data.config[field.key];controls.append(input);
   }
   input.id=field.key;input.dataset.deckType=field.type;input.setAttribute('aria-label',field.label);input.addEventListener('change',update);input.addEventListener('input',update);
   row.append(controls);groups[field.key.endsWith('green')||field.key.endsWith('orange')||field.key.endsWith('indicators_all')?'indicator':'appearance'].append(row);
  }
  const periodHelp=document.createElement('p');periodHelp.className='deck-settings-hint';periodHelp.textContent=data.labels.periodHelp;groups.appearance.append(periodHelp);
  const help=document.createElement('details');help.className='deck-settings-help';
  const summary=document.createElement('summary');summary.textContent='ⓘ '+data.labels.help;
  const hint=document.createElement('p');hint.textContent=data.labels.hint;help.append(summary,hint);groups.indicator.append(help);
  const note=document.createElement('p');note.className='deck-settings-hint';note.textContent=data.labels.indicatorHelp;groups.indicator.append(note);
  enhanceSelects();
  const master=document.querySelector('[data-key="deck_overview_enabled"]');
  if(master)master.addEventListener('change',update);
  update();
 };
 window.collectDeckOverviewSettings=function(){
  const result={};document.querySelectorAll('[data-deck-type]').forEach(input=>{
   result[input.id]=input.type==='checkbox'?input.checked:input.type==='number'||input.id.endsWith('retention_days')?Number(input.value):input.value;
  });
  return result;
 };
 window.validateDeckOverviewSettings=function(){
  const green=document.getElementById('deck_overview_green'),orange=document.getElementById('deck_overview_orange');if(!green)return true;
  green.setCustomValidity(Number(green.value)<=Number(orange.value)?model.labels.validation:'');
  const valid=green.checkValidity()&&orange.checkValidity();if(!valid){gotoPage('deck');green.reportValidity();orange.reportValidity();}return valid;
 };
 function update(){
  if(!model)return;
  const root=document.getElementById('deckOverviewOptions');
  const master=document.querySelector('[data-key="deck_overview_enabled"]');
  const disabled=master ? !master.checked : false;
  root.classList.toggle('deck-disabled',disabled);root.inert=disabled;
  root.querySelectorAll('input,select,button').forEach(input=>input.disabled=disabled);
  const color=document.getElementById('deck_overview_title_color');
  if(color){const custom=document.getElementById('deck_overview_title_color_mode').value==='custom';color.closest('.row').hidden=!custom;color.disabled=disabled||!custom;}
  document.getElementById('deck_overview_green').setCustomValidity('');
  if(disabled)closeDD();
 }
})();
