// Arrange Nodes regression checks in a temporary browser profile; no real user data.
const {chromium}=require('playwright');const assert=require('node:assert/strict');

// A deliberately unusable map: every node starts on the same spot and the
// branches have very different sizes, which is exactly the case the old
// fixed-spacing layout could not handle.
const PILED={name:'Piled map',nodes:[
  {id:1,text:'Root',parent:null,x:0,y:0},
  {id:2,text:'Branch with many children',parent:1,x:0,y:0},
  {id:3,text:'Leaf branch',parent:1,x:0,y:0},
  {id:4,text:'Third branch',parent:1,x:0,y:0},
  {id:5,text:'Grandchild one',parent:2,x:0,y:0},
  {id:6,text:'Grandchild two',parent:2,x:0,y:0},
  {id:7,text:'Grandchild three',parent:2,x:0,y:0},
  {id:8,text:'Grandchild four',parent:2,x:0,y:0},
  {id:9,text:'Deep node',parent:5,x:0,y:0},
  {id:10,text:'Deeper node',parent:9,x:0,y:0},
  {id:11,text:'Other child',parent:4,x:0,y:0},
]};

const boxes=page=>page.locator('.node').evaluateAll(els=>els.map(el=>{
  const r=el.getBoundingClientRect();
  return {id:el.id,left:r.left,top:r.top,right:r.right,bottom:r.bottom};
}));

function overlaps(list,tolerance=1){
  const hits=[];
  for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){
    const a=list[i],b=list[j];
    if(a.right-b.left>tolerance&&b.right-a.left>tolerance&&
       a.bottom-b.top>tolerance&&b.bottom-a.top>tolerance) hits.push(`${a.id}/${b.id}`);
  }
  return hits;
}

(async()=>{
const b=await chromium.launch({headless:true,...(process.env.SYNAPSE_TEST_CHROME?{executablePath:process.env.SYNAPSE_TEST_CHROME}:{})});
try{
  const c=await b.newContext();
  const p=await c.newPage({viewport:{width:1000,height:800}});
  const errors=[];p.on('pageerror',e=>{errors.push(e.message);console.error('Page error:',e.message)});
  await p.addInitScript(mapData=>{
    if(window===top){
      localStorage.setItem('mindmaps',JSON.stringify({piled:mapData}));
      localStorage.setItem('lastOpenedMindmap','piled');
      localStorage.setItem('mindmaps_saved_at','5000');
    }
  },PILED);
  const url=require('node:url').pathToFileURL(require('node:path').resolve(__dirname,'../index.html')).href;
  await p.goto(url);
  await p.waitForFunction(()=>window.__synapseArrangeNodes);
  await p.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
  assert.equal(await p.locator('.node').count(),PILED.nodes.length);
  assert.ok(overlaps(await boxes(p)).length>0,'fixture should start with overlapping nodes');

  // Every layout must separate all eleven nodes, including the lopsided branches.
  for(const style of ['vertical','horizontal','radial']){
    for(const spacing of ['compact','normal','wide']){
      assert.equal(await p.evaluate(([s,g])=>__synapseArrangeNodes(s,g),[style,spacing]),true);
      const hits=overlaps(await boxes(p));
      assert.deepEqual(hits,[],`${style}/${spacing} produced overlaps: ${hits.join(', ')}`);
    }
  }
  console.log('PASS vertical, horizontal and radial layouts keep every node clear at all spacings');

  // Wider spacing must actually use more room than compact spacing.
  const extent=async(style,spacing)=>{
    await p.evaluate(([s,g])=>__synapseArrangeNodes(s,g),[style,spacing]);
    return p.evaluate(()=>{
      const nodes=JSON.parse(__synapseFlushMindmap().snapshot).piled.nodes;
      const xs=nodes.map(n=>n.x),ys=nodes.map(n=>n.y);
      return (Math.max(...xs)-Math.min(...xs))+(Math.max(...ys)-Math.min(...ys));
    });
  };
  assert.ok(await extent('vertical','wide')>await extent('vertical','compact'));
  assert.ok(await extent('vertical','normal')>await extent('vertical','compact'));
  console.log('PASS spacing choice changes the used area');

  // One arrangement is one undo step, and it is persisted.
  await p.evaluate(()=>__synapseArrangeNodes('vertical','normal'));
  const arranged=await p.evaluate(()=>__synapseFlushMindmap().snapshot);
  await p.locator('#undo-btn').click();
  const undone=await p.evaluate(()=>__synapseFlushMindmap().snapshot);
  assert.notEqual(undone,arranged,'undo must restore the previous positions');
  await p.locator('#redo-btn').click();
  assert.equal(await p.evaluate(()=>__synapseFlushMindmap().snapshot),arranged);
  // Arranging an already tidy map must not add an empty history entry.
  assert.equal(await p.evaluate(()=>__synapseArrangeNodes('vertical','normal')),false);
  await p.locator('#undo-btn').click();
  assert.equal(await p.evaluate(()=>__synapseFlushMindmap().snapshot),undone);
  console.log('PASS undo/redo of one arrangement and no no-op history entry');

  // Modal: choices round-trip through storage and the Delete key is inert.
  await p.locator('#hamburger-btn').click();
  await p.locator('#arrange-btn').click();
  await p.locator('#arrange-options-overlay.visible').waitFor();
  assert.equal(await p.locator('#hamburger-dropdown.open').count(),0);
  await p.locator('#arrange-style-options .learn-option-btn[data-value="radial"]').click();
  await p.locator('#arrange-spacing-options .learn-option-btn[data-value="wide"]').click();
  const nodeCount=await p.locator('.node').count();
  await p.keyboard.press('Delete');
  assert.equal(await p.locator('.node').count(),nodeCount,'Delete must not reach the map while the modal is open');
  await p.locator('#arrange-apply-btn').click();
  await p.locator('#arrange-options-overlay.visible').waitFor({state:'detached'});
  assert.deepEqual(overlaps(await boxes(p)),[]);
  assert.deepEqual(JSON.parse(await p.evaluate(()=>localStorage.getItem('mindmap_arrange_options'))),
    {style:'radial',spacing:'wide'});
  await p.reload();
  await p.waitForFunction(()=>window.__synapseArrangeNodes);
  await p.locator('#hamburger-btn').click();
  await p.locator('#arrange-btn').click();
  await p.locator('#arrange-options-overlay.visible').waitFor();
  assert.equal(await p.locator('#arrange-style-options .learn-option-btn.active').getAttribute('data-value'),'radial');
  assert.equal(await p.locator('#arrange-spacing-options .learn-option-btn.active').getAttribute('data-value'),'wide');
  await p.locator('#arrange-cancel-btn').click();
  await p.locator('#arrange-options-overlay.visible').waitFor({state:'detached'});
  console.log('PASS modal reopens with the remembered layout and spacing');

  // Cyclic and unreachable data must not hang or crash the layout.
  await p.evaluate(()=>{
    localStorage.setItem('mindmaps',JSON.stringify({broken:{name:'Broken',nodes:[
      {id:1,text:'Root',parent:null,x:10,y:10},
      {id:2,text:'A',parent:3,x:10,y:10},
      {id:3,text:'B',parent:2,x:10,y:10},
      {id:4,text:'C',parent:1,x:10,y:10},
    ]}}));
    localStorage.setItem('lastOpenedMindmap','broken');
  });
  await p.reload();
  await p.waitForFunction(()=>window.__synapseArrangeNodes);
  await p.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
  assert.equal(await p.evaluate(()=>__synapseArrangeNodes('vertical','normal')),true);
  assert.deepEqual(overlaps(await boxes(p)),[]);
  console.log('PASS repaired cyclic map arranges without hanging');

  // The sandboxed tutorial map must stay out of the user's storage. A separate
  // context keeps the fixture above from being re-seeded on each navigation.
  const userMap=JSON.stringify({mine:{name:'User map',nodes:[
    {id:1,text:'PRIVATE KEEP',parent:null,x:-300,y:600,width:154,height:60},
    {id:2,text:'User child',parent:1,x:800,y:-500,width:154,height:60}]}});
  const isolated=await b.newContext();
  const practice=await isolated.newPage({viewport:{width:1000,height:800}});
  await practice.addInitScript(stored=>{
    if(window===top){localStorage.setItem('mindmaps',stored);localStorage.setItem('lastOpenedMindmap','mine')}
  },userMap);
  await practice.goto(url+'?practice=1');
  await practice.waitForFunction(()=>window.__synapseArrangeNodes);
  await practice.locator('#mindmap-loading-overlay').waitFor({state:'hidden'});
  assert.equal(await practice.evaluate(()=>__synapseArrangeNodes('radial','compact')),true);
  assert.deepEqual(overlaps(await boxes(practice)),[]);
  assert.equal(await practice.evaluate(()=>localStorage.getItem('mindmap_arrange_options')),null);
  assert.equal(await practice.evaluate(()=>localStorage.getItem('mindmaps')),userMap);
  await isolated.close();
  console.log('PASS practice frame arranges without writing user storage');

  if(process.env.SYNAPSE_TEST_SCREENSHOT){
    await p.evaluate(()=>__synapseArrangeNodes('radial','normal'));
    await p.waitForTimeout(350);
    await p.screenshot({path:process.env.SYNAPSE_TEST_SCREENSHOT});
  }
  assert.deepEqual(errors,[]);
}finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
