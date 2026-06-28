function anonId(){let id=localStorage.getItem('fmnc_anon');if(!id){id='a-'+Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem('fmnc_anon',id);}return id;}
const ANON=anonId();
async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.ok?r.json():null;}
document.querySelectorAll('[data-vote]').forEach(b=>b.addEventListener('click',async()=>{
  const id=+b.dataset.id,rating=b.dataset.vote;const res=await post('/api/feedback',{brief_item_id:id,rating,anon_id:ANON});
  if(res){const item=b.closest('.item');item.querySelector('[data-vote=up] span').textContent=res.up;item.querySelector('[data-vote=down] span').textContent=res.down;
    item.querySelectorAll('[data-vote]').forEach(x=>x.classList.remove('act'));b.classList.add('act');}}));
document.querySelectorAll('[data-comment]').forEach(b=>b.addEventListener('click',()=>{const box=document.getElementById('cbox-'+b.dataset.comment);box.style.display=box.style.display==='block'?'none':'block';}));
document.querySelectorAll('[data-send]').forEach(b=>b.addEventListener('click',async()=>{const id=+b.dataset.send;const ta=b.parentElement.querySelector('textarea');if(!ta.value.trim())return;await post('/api/feedback',{brief_item_id:id,rating:'up',anon_id:ANON,comment:ta.value.trim()});ta.value='';b.parentElement.style.display='none';}));
document.querySelectorAll('[data-click]').forEach(a=>a.addEventListener('click',()=>post('/api/event',{brief_item_id:+a.dataset.click,type:'click',anon_id:ANON})));
const seen=new Set();const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){const id=+e.target.dataset.id;if(!seen.has(id)){seen.add(id);post('/api/event',{brief_item_id:id,type:'view',anon_id:ANON});}}}),{threshold:0.5});
document.querySelectorAll('.item').forEach(el=>io.observe(el));
const chips=document.getElementById('chips');if(chips)chips.addEventListener('click',e=>{if(!e.target.dataset.f)return;chips.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));e.target.classList.add('on');const f=e.target.dataset.f;
  document.querySelectorAll('.item').forEach(it=>{it.style.display=(f==='all'||(it.dataset.tags||'').split(',').includes(f))?'':'none';});});
