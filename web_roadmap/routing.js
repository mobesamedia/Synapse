/* Orthogonal obstacle routing with bounded work and a geometry cache in the editor. */
(() => {
    const EPS=.01, equal=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)<EPS;
    const clean=points=>{
        const out=[];
        for(const p of points){if(out.length&&equal(p,out.at(-1)))continue;out.push(p);while(out.length>=3){const[a,b,c]=out.slice(-3);if(Math.abs((b.x-a.x)*(c.y-b.y)-(b.y-a.y)*(c.x-b.x))>EPS||(b.x-a.x)*(c.x-b.x)+(b.y-a.y)*(c.y-b.y)<0)break;out.splice(out.length-2,1);}}
        return out;
    };
    // Segment/AABB intersection, including diagonal escape segments for rotated boxes.
    const hits=(a,b,r)=>{
        let lo=0,hi=1;const dx=b.x-a.x,dy=b.y-a.y;
        for(const [p,q]of [[-dx,a.x-r.l],[dx,r.r-a.x],[-dy,a.y-r.t],[dy,r.b-a.y]]){
            if(Math.abs(p)<EPS){if(q<=EPS)return false;}else {const v=q/p;if(p<0)lo=Math.max(lo,v);else hi=Math.min(hi,v);if(lo>=hi-EPS)return false;}
        }
        return hi>EPS&&lo<1-EPS;
    };
    const clear=(points,rects)=>points.every((p,i)=>!i||!rects.some(r=>hits(points[i-1],p,r)));
    const length=ps=>ps.reduce((sum,p,i)=>sum+(i?Math.hypot(p.x-ps[i-1].x,p.y-ps[i-1].y):0),0)+ps.length*8;
    const escape=(p,v,r)=>{
        if(!r)return {x:p.x+v.x*24,y:p.y+v.y*24};
        let distances=[];
        if(v.x>EPS)distances.push((r.r-p.x)/v.x);if(v.x<-EPS)distances.push((r.l-p.x)/v.x);
        if(v.y>EPS)distances.push((r.b-p.y)/v.y);if(v.y<-EPS)distances.push((r.t-p.y)/v.y);
        const d=Math.max(24,Math.min(...distances.filter(d=>d>=0))+8);
        return {x:p.x+v.x*d,y:p.y+v.y*d};
    };
    function route(a,b,v,w,rects,source,target){
        const p=escape(a,v,rects.find(r=>r.id===source)),q=escape(b,w,rects.find(r=>r.id===target));
        // Exit/entry stubs deliberately cross their own box padding; all middle segments avoid it.
        const candidates=[[p,{x:q.x,y:p.y},q],[p,{x:p.x,y:q.y},q]];
        let possible=candidates.filter(ps=>clear(ps,rects));
        if(!possible.length){
            let bounds={l:Math.min(p.x,q.x),r:Math.max(p.x,q.x),t:Math.min(p.y,q.y),b:Math.max(p.y,q.y)};
            let blocked=rects.filter(r=>candidates.some(ps=>ps.some((e,i)=>i&&hits(ps[i-1],e,r))));
            for(let attempt=0;attempt<rects.length+1;attempt++){
                for(const r of blocked){bounds.l=Math.min(bounds.l,r.l-8);bounds.r=Math.max(bounds.r,r.r+8);bounds.t=Math.min(bounds.t,r.t-8);bounds.b=Math.max(bounds.b,r.b+8);}
                const trials=[
                    [p,{x:p.x,y:bounds.t},{x:q.x,y:bounds.t},q],
                    [p,{x:p.x,y:bounds.b},{x:q.x,y:bounds.b},q],
                    [p,{x:bounds.l,y:p.y},{x:bounds.l,y:q.y},q],
                    [p,{x:bounds.r,y:p.y},{x:bounds.r,y:q.y},q],
                    ...[bounds.l,bounds.r].flatMap(x=>[bounds.t,bounds.b].flatMap(y=>[
                        [p,{x,y:p.y},{x,y},{x:q.x,y},q],
                        [p,{x:p.x,y},{x,y},{x,y:q.y},q]
                    ]))
                ];
                possible=trials.filter(ps=>clear(ps,rects));
                if(possible.length)break;
                const next=rects.filter(r=>trials.some(ps=>ps.some((e,i)=>i&&hits(ps[i-1],e,r))));
                if(next.every(r=>blocked.includes(r)))break;
                blocked=next;
            }
        }
        // In overlapping/enclosed boxes no collision-free route necessarily exists.
        const middle=(possible.length?possible:candidates).sort((x,y)=>length(x)-length(y))[0];
        return clean([a,...middle,b]);
    }
    function path(points,rounded){
        let d=`M${points[0].x},${points[0].y}`;
        for(let i=1;i<points.length-1;i++){
            const a=points[i-1],p=points[i],b=points[i+1],l1=Math.hypot(p.x-a.x,p.y-a.y),l2=Math.hypot(b.x-p.x,b.y-p.y),r=rounded?Math.min(8,l1/2,l2/2):0;
            if(!r){d+=` L${p.x},${p.y}`;continue;}
            d+=` L${p.x+(a.x-p.x)*r/l1},${p.y+(a.y-p.y)*r/l1} Q${p.x},${p.y} ${p.x+(b.x-p.x)*r/l2},${p.y+(b.y-p.y)*r/l2}`;
        }
        const last=points.at(-1);return d+` L${last.x},${last.y}`;
    }
    window.workspaceRouting={route,path,hits,clear};
})();
