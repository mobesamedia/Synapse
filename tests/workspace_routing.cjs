const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const context={window:{}};vm.createContext(context);vm.runInContext(fs.readFileSync(path.resolve(__dirname,'../web_roadmap/routing.js'),'utf8'),context);
const {route,hits,path:svg}=context.window.workspaceRouting;
const rect={id:'box',l:88,r:312,t:88,b:212};
for(const [a,v]of [[{x:100,y:150},{x:-1,y:0}],[{x:300,y:150},{x:1,y:0}],[{x:200,y:100},{x:0,y:-1}],[{x:200,y:200},{x:0,y:1}]]){
 for(const b of [{x:500,y:150},{x:-100,y:150},{x:200,y:-100},{x:200,y:400}]){
  const points=route(a,b,v,{x:-1,y:0},[rect],'box',null);
  for(let i=2;i<points.length;i++)assert.equal(hits(points[i-1],points[i],rect),false,JSON.stringify(points));
  assert.ok(!/NaN|Infinity/.test(svg(points,true)));
  const before=points.at(-2);assert.ok(Math.hypot(b.x-before.x,b.y-before.y)>0);
 }
}
const obstacles=[rect,{id:'wall',l:340,r:430,t:10,b:290},{id:'target',l:488,r:712,t:88,b:212}];
const pts=route({x:300,y:150},{x:500,y:150},{x:1,y:0},{x:-1,y:0},obstacles,'box','target');
for(let i=2;i<pts.length-1;i++)for(const r of obstacles)assert.equal(hits(pts[i-1],pts[i],r),false,JSON.stringify(pts));
assert.ok(pts.at(-2).x<500,'target arrow enters from its chosen left side');
console.log('PASS 16 source-port/destination combinations, blocked corridor, target direction, finite rounded paths');
