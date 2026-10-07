/* Local calendar dates, with no UTC conversion or fixed 24 hour arithmetic. */
window.TaskSchedule = (() => {
  const key = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const parse = s => {if(!/^\d{4}-\d{2}-\d{2}$/.test(s||''))return null;const d=new Date(s+'T12:00:00');return key(d)===s?d:null;};
  const next = (task,after) => {
    const mode=task.repeat;
    const days=mode==='weekly'?[(parse(task.repeat_anchor)||after).getDay()]:Array.isArray(task.repeat_days)?task.repeat_days:[];
    for(let i=1;i<=7;i++){const d=new Date(after);d.setDate(d.getDate()+i);if(mode==='daily'||(['weekly','weekdays'].includes(mode)&&days.includes(d.getDay())))return key(d);}
    return null;
  };
  const normalize=(tasks,cleanup,today=key(new Date()))=>tasks.flatMap(original=>{
    if(!original||typeof original!=='object')return [original];
    const t={...original};const completed=parse(t.completed_on);
    if(t.done&&completed&&t.completed_on<=today){
      if(['daily','weekly','weekdays'].includes(t.repeat)){
        const due=next(t,completed);if(due){t.due_on=due;if(due<=today){t.done=false;delete t.completed_on;}}
      }else if(cleanup&&t.completed_on<today)return [];
    }
    return [t];
  });
  return {key,parse,next,normalize,today:()=>key(new Date())};
})();
