const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const b=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
const p=await b.newPage({viewport:{width:1100,height:800}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.addInitScript(()=>window.__ROADMAP_DATA__={version:1,active:'test',maps:[{id:'test',name:'Ports',view:{x:0,y:0,scale:1},objects:[{id:'box',kind:'shape',shape:'rect',x:220,y:200,w:220,h:120,rotation:0,html:'Same source port',fill:'#fff',stroke:'#252525',fontSize:20}]}]});
await p.goto(pathToFileURL(path.resolve(__dirname,'../web_roadmap/index.html')).href);await p.locator('#objects > g').click();
const drag=async(a,x,y)=>{await p.mouse.move(a.x+a.width/2,a.y+a.height/2);await p.mouse.down();await p.mouse.move(x,y,{steps:12});await p.mouse.up()};
for(let i=0;i<3;i++){
 const port=await p.locator('[data-anchor=left]').boundingBox();const previous=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].objects.filter(o=>o.kind==='arrow'));
 await drag(port,800,port.y+port.height/2+i*90);
 const arrows=await p.evaluate(()=>__roadmapSnapshot().data.maps[0].objects.filter(o=>o.kind==='arrow'));assert.equal(arrows.length,i+1);assert.deepEqual(arrows.slice(0,-1),previous);assert.equal(arrows.at(-1).a.node,'box');
 const end=await p.locator('[data-end=a]').boundingBox(),newPort=await p.locator('[data-anchor=left]').boundingBox();assert.ok(Math.abs(end.x-newPort.x)>=18,'moving end must not overlap the add port');
 const direction=await p.locator('[data-arrow]').last().evaluate(el=>{const n=el.getTotalLength(),a=el.getPointAtLength(n-1),b=el.getPointAtLength(n);return{x:b.x-a.x,y:b.y-a.y}});assert.ok(direction.x>0,'left port drawn to the right must end pointing right');
}
await p.screenshot({path:path.resolve(__dirname,'../docs/roadmap-ports.png')});assert.deepEqual(errors,[]);console.log('PASS 3 arrows from the same selected source port, old endpoints unchanged, separate end grips, right-facing tips after routing around the source box');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
