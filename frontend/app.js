const $=s=>document.querySelector(s);
const P=[
{id:1,n:'Orion',t:'smart',p:249,c:'#17707a',r:4.8},{id:2,n:'Nova',t:'smart',p:199,c:'#2b3a8c',r:4.6},
{id:3,n:'Pulse',t:'smart',p:149,c:'#a02c52',r:4.4},{id:7,n:'Vega',t:'smart',p:279,c:'#3c3f46',r:4.9,nw:1},
{id:8,n:'Atlas',t:'smart',p:329,c:'#1d5a3a',r:4.7},{id:9,n:'Zenith',t:'smart',p:189,c:'#c0602a',r:4.5},
{id:4,n:'Heritage',t:'classic',p:229,c:'#8a5a2b',r:4.7,g:1},{id:5,n:'Meridian',t:'classic',p:179,c:'#2f3a40',r:4.6},
{id:6,n:'Regent',t:'classic',p:289,c:'#a97c2f',r:4.9,g:1,iv:1},{id:10,n:'Oxford',t:'classic',p:159,c:'#1f3b63',r:4.5},
{id:11,n:'Sovereign',t:'classic',p:349,c:'#5b1f2e',r:4.8,g:1,nw:1},{id:12,n:'Aurora',t:'classic',p:209,c:'#3a6b6b',r:4.6}];
const store={get:(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}},set:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{}}};
let mem={cart:[],user:null};
const cart=()=>store.get('cart',mem.cart),saveCart=c=>{mem.cart=c;store.set('cart',c);nav()};
const user=()=>store.get('user',mem.user);
const usd=n=>'$'+n.toFixed(2);

function watch(p){
 const k='w'+(watch.n=(watch.n||0)+1),gold=!!p.g,ivory=!!p.iv;
 const m1=gold?'#f6dd91':'#f8fafc',m2=gold?'#8c6a24':'#76818a';
 const defs=`<defs><linearGradient id="${k}m" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${m1}"/><stop offset=".45" stop-color="${m2}"/><stop offset=".7" stop-color="${m1}"/><stop offset="1" stop-color="${m2}"/></linearGradient>
 <linearGradient id="${k}s" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".5"/><stop offset=".3" stop-color="#fff" stop-opacity=".2"/><stop offset=".7" stop-color="#000" stop-opacity=".05"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>
 <radialGradient id="${k}d" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#fff" stop-opacity=".3"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></radialGradient>
 <linearGradient id="${k}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".6"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>
 <filter id="${k}b"><feGaussianBlur stdDeviation="4"/></filter></defs>`;
 if(p.t==='smart') return `<svg viewBox="0 0 200 200" role="img" aria-label="${p.n} smartwatch">${defs}
 <rect x="73" y="0" width="54" height="200" fill="${p.c}"/>
 <rect x="73" y="0" width="54" height="200" fill="url(#${k}s)"/>
 <path d="M73 6H127M73 14H127M73 22H127M73 178H127M73 186H127M73 194H127" stroke="#000" stroke-opacity=".22" stroke-width="2"/>
 <rect x="42" y="40" width="124" height="136" rx="34" fill="#000" opacity=".4" filter="url(#${k}b)"/>
 <rect x="162" y="82" width="8" height="30" rx="4" fill="url(#${k}m)"/><rect x="162" y="124" width="5" height="16" rx="2.5" fill="url(#${k}m)"/>
 <rect x="36" y="30" width="128" height="140" rx="36" fill="url(#${k}m)"/>
 <rect x="42" y="36" width="116" height="128" rx="31" fill="#04070b"/>
 <circle cx="100" cy="64" r="11" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="4"/>
 <circle cx="100" cy="64" r="11" fill="none" stroke="${p.c}" stroke-width="4" stroke-linecap="round" stroke-dasharray="44 30"><animateTransform attributeName="transform" type="rotate" from="0 100 64" to="360 100 64" dur="5s" repeatCount="indefinite"/></circle>
 <text class="digi" x="100" y="112" text-anchor="middle" fill="#fff" font-size="34" font-weight="700" font-family="Manrope,sans-serif">--:--</text>
 <text x="100" y="132" text-anchor="middle" fill="#9fb0bd" font-size="9" font-family="Manrope,sans-serif">SAATI ${p.n.toUpperCase()}</text>
 <rect x="64" y="142" width="72" height="8" rx="4" fill="#fff" fill-opacity=".1"/><rect x="64" y="142" width="46" height="8" rx="4" fill="${p.c}"/>
 <path d="M44 66Q44 38 76 38H112L56 164Q44 158 44 140Z" fill="url(#${k}g)" opacity=".5"/></svg>`;
 const dial=ivory?'#f2ede0':p.c,hc=ivory?'#1b1b1b':'#f5f5f5';
 const idx=[...Array(12)].map((_,i)=>`<rect x="98.4" y="42" width="3.2" height="${i%3?7:11}" rx="1" fill="${ivory?'#222':'#f2f2f2'}" transform="rotate(${i*30} 100 100)"/>`).join('');
 const trk=[...Array(60)].map((_,i)=>i%5?`<line x1="100" y1="38.5" x2="100" y2="41" stroke="${ivory?'#222':'#fff'}" stroke-opacity=".6" stroke-width=".8" transform="rotate(${i*6} 100 100)"/>`:'').join('');
 return `<svg viewBox="0 0 200 200" role="img" aria-label="${p.n} classic watch">${defs}
 <rect x="70" y="0" width="60" height="200" fill="${p.c}"/><rect x="70" y="0" width="60" height="200" fill="url(#${k}s)"/>
 <path d="M76 0V200M124 0V200" stroke="#fff" stroke-opacity=".5" stroke-width="1" stroke-dasharray="5 4" fill="none"/>
 <circle cx="104" cy="112" r="70" fill="#000" opacity=".45" filter="url(#${k}b)"/>
 <rect x="66" y="26" width="68" height="22" rx="8" fill="url(#${k}m)"/><rect x="66" y="152" width="68" height="22" rx="8" fill="url(#${k}m)"/>
 <rect x="168" y="93" width="12" height="14" rx="3" fill="url(#${k}m)"/>
 <circle cx="100" cy="100" r="71" fill="url(#${k}m)"/>
 <circle cx="100" cy="100" r="64" fill="#1a1d20"/><circle cx="100" cy="100" r="62" fill="url(#${k}m)"/>
 <circle cx="100" cy="100" r="58" fill="${dial}"/><circle cx="100" cy="100" r="58" fill="url(#${k}d)"/>
 ${trk}${idx}
 <text x="100" y="76" text-anchor="middle" font-size="8" letter-spacing="2.4" fill="${hc}" font-family="Bodoni Moda,serif">SAATI</text>
 <text x="100" y="128" text-anchor="middle" font-size="5" letter-spacing="1.2" fill="${hc}" fill-opacity=".7" font-family="Manrope,sans-serif">AUTOMATIC</text>
 <g filter="drop-shadow(1px 2px 1.5px rgba(0,0,0,.45))">
 <line class="hh" x1="100" y1="106" x2="100" y2="66" stroke="${hc}" stroke-width="5.2" stroke-linecap="round"/>
 <line class="hm" x1="100" y1="108" x2="100" y2="48" stroke="${hc}" stroke-width="3.4" stroke-linecap="round"/>
 <line class="hs" x1="100" y1="116" x2="100" y2="42" stroke="#d9432f" stroke-width="1.5"/></g>
 <circle cx="100" cy="100" r="4.5" fill="#d9432f"/><circle cx="100" cy="100" r="1.6" fill="#222"/>
 <path d="M52 78A52 52 0 0 1 112 46A60 60 0 0 0 52 78Z" fill="#fff" opacity=".35"/>
 <circle cx="100" cy="100" r="58" fill="url(#${k}g)" opacity=".35"/></svg>`;
}
function tick(){ // every watch on the page shows the real current time
 const d=new Date(),s=d.getSeconds(),m=d.getMinutes()+s/60,h=(d.getHours()%12)+m/60;
 const rot=(c,a)=>document.querySelectorAll(c).forEach(e=>e.setAttribute('transform',`rotate(${a} 100 100)`));
 rot('.hs',s*6);rot('.hm',m*6);rot('.hh',h*30);
 const t=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
 document.querySelectorAll('.digi').forEach(e=>e.textContent=t);
}
setInterval(tick,1000);

const API=(window.SAATI_API||'').replace(/\/$/,'');
async function api(path,body){const u=store.get('user',mem.user);
 const r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json',...(u&&u.token?{Authorization:'Bearer '+u.token}:{})},body:JSON.stringify(body)});
 const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||'Something went wrong');return d}
function nav(){
 const u=user(),n=cart().reduce((s,i)=>s+i.q,0),w=store.get('wish',[]).length;
 $('#nav').innerHTML=`<a class="logo" href="#/">SAATI</a><a href="#/products">Watches</a><a href="#/products" id="wl" title="Wishlist">♥ ${w}</a><a href="#/checkout">Cart (<span id="cn">${n}</span>)</a>`+(u?`<a href="#" id="out">Sign out (${u.name})</a>`:'<a href="#/signin">Sign in</a>')+'<button class="mode" id="mode" aria-label="Toggle dark mode">◐</button>';
 const o=$('#out');if(o)o.onclick=e=>{e.preventDefault();mem.user=null;store.set('user',null);nav();location.hash='#/'};
 $('#mode').onclick=()=>{const d=document.documentElement,dark=d.dataset.theme?d.dataset.theme==='dark':matchMedia('(prefers-color-scheme:dark)').matches;d.dataset.theme=dark?'light':'dark'};
}
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>t.classList.remove('show'),2200)}
const SPEC=p=>p.t==='smart'?[['Display',`AMOLED, ${1.3+p.id%3*.1}"`.replace(/(\.\d)\d+/,'$1')],['Battery',`${3+p.id%5} days`],['Water resistance','50 m'],['Sensors','Heart rate, GPS, sleep']]:[['Movement','Automatic'],['Case',`${38+p.id%4} mm ${p.g?'gold-tone':'steel'}`],['Crystal','Sapphire'],['Water resistance','100 m']];
function card(p,i){const w=store.get('wish',[]).includes(p.id);
 return `<div class="card" style="animation-delay:${i*45}ms"><button class="heart ${w?'on':''}" data-wish="${p.id}" aria-label="Save ${p.n} to wishlist">♥</button>${p.nw?'<span class="badge">New</span>':''}<div class="img" data-open="${p.id}" role="button" tabindex="0" aria-label="View ${p.n}">${watch(p)}</div><h3>${p.n}</h3><div>${p.t==='smart'?'Smartwatch':'Classic watch'} · ★ ${p.r}</div><p class="price">${usd(p.p)}</p><button class="btn" data-add="${p.id}">Add to cart</button></div>`}
function openModal(id){const p=P.find(x=>x.id===id);
 $('#modal').innerHTML=`<div class="mb"><div class="mc" role="dialog" aria-modal="true" aria-label="${p.n}"><button class="x" aria-label="Close">×</button><div class="mw">${watch(p)}</div><div><h2>SAATI ${p.n}</h2><p class="price">${usd(p.p)} · ★ ${p.r}</p><ul class="spec">${SPEC(p).map(s=>`<li><span>${s[0]}</span><b>${s[1]}</b></li>`).join('')}</ul><button class="btn" data-add="${p.id}">Add to cart</button></div></div></div>`;tick()}
const closeModal=()=>$('#modal').innerHTML='';
let timer;
const pages={
home(){
 $('#app').innerHTML=`<div class="promo">Use code <b>SAATI10</b> for 10% off. Offer ends in <b id="cd">--:--:--</b></div><main class="wrap hero"><div><h1>Time, worn well.</h1><p>Smart and classic watches with a two-year warranty and free shipping over $300.</p><a class="btn" href="#/products">Shop watches</a> <a class="btn alt" href="#/signin">Sign in</a></div><div class="stage" id="stage"></div></main><section class="wrap"><h2>Best sellers</h2><div class="grid" id="bs">${[...P].sort((a,b)=>b.r-a.r).slice(0,4).map(card).join('')}</div></section>`;
 let i=0;const show=()=>{const p=P[i++%P.length];$('#stage').innerHTML=`<div class="w">${watch(p)}</div><div class="tag">${p.n} · ${usd(p.p)}</div>`;tick()};
 show();timer=setInterval(show,4000);
},
products(){
 $('#app').innerHTML=`<main class="wrap"><h1>Watches</h1><div class="bar"><div class="tabs"><button class="on" data-t="all">All</button><button data-t="smart">Smart</button><button data-t="classic">Classic</button></div><input id="sq" type="search" placeholder="Search watches" aria-label="Search watches"><select id="so" aria-label="Sort"><option value="f">Featured</option><option value="a">Price: low to high</option><option value="d">Price: high to low</option><option value="r">Top rated</option></select></div><p id="cnt"></p><div class="grid" id="grid"></div></main>`;
 let t='all';const draw=()=>{const q=$('#sq').value.toLowerCase(),o=$('#so').value;
  const l=P.filter(p=>(t==='all'||p.t===t)&&p.n.toLowerCase().includes(q));
  if(o==='a')l.sort((a,b)=>a.p-b.p);if(o==='d')l.sort((a,b)=>b.p-a.p);if(o==='r')l.sort((a,b)=>b.r-a.r);
  $('#cnt').textContent=l.length+' watches';
  $('#grid').innerHTML=l.length?l.map(card).join(''):'<p>No watches match your search. Clear it or pick another filter.</p>';tick()};
 document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');t=b.dataset.t;draw()});
 $('#sq').oninput=draw;$('#so').onchange=draw;draw();
},
signin(){
 let up=false;const draw=()=>{$('#app').innerHTML=`<main class="wrap"><form class="form" id="f"><h1>${up?'Create account':'Sign in'}</h1>${up?'<label for="nm">Name</label><input id="nm" required autocomplete="name">':''}<label for="em">Email</label><input id="em" type="email" required autocomplete="email"><label for="pw">Password</label><input id="pw" type="password" minlength="6" required autocomplete="${up?'new-password':'current-password'}"><p class="err" id="err"></p><button class="btn">${up?'Create account':'Sign in'}</button> <a href="#" id="sw">${up?'I have an account':'Create an account'}</a></form></main>`;
  $('#sw').onclick=e=>{e.preventDefault();up=!up;draw()};
  $('#f').onsubmit=async e=>{e.preventDefault();const em=$('#em').value.trim().toLowerCase(),pw=$('#pw').value;
  try{let u;
   if(API){const d=await api(up?'/api/signup':'/api/signin',{name:up?$('#nm').value.trim():undefined,email:em,password:pw});u={name:d.name,email:em,token:d.token}}
   else{const users=store.get('users',{});if(up){if(users[em])throw Error('That email already has an account. Sign in instead.');users[em]={name:$('#nm').value.trim(),pw};store.set('users',users)}else if(!users[em]||users[em].pw!==pw)throw Error('Email or password is incorrect.');u={name:users[em].name,email:em}}
   mem.user=u;store.set('user',u);nav();toast('Welcome, '+u.name);location.hash=cart().length?'#/checkout':'#/products'}
  catch(x){$('#err').textContent=x.message}};
 };draw();
},
checkout(){
 if(!cart().length){$('#app').innerHTML='<main class="wrap form"><h1>Your cart is empty</h1><a class="btn" href="#/products">Browse watches</a></main>';return}
 let promo=false;
 const calc=()=>{const sub=cart().reduce((s,i)=>s+P.find(p=>p.id===i.id).p*i.q,0),disc=promo?sub*.1:0,ship=sub-disc>=300?0:9.99;return{sub,disc,ship,tot:sub-disc+ship}};
 $('#app').innerHTML=`<main class="wrap"><div class="form"><h1>Checkout</h1><div id="lines"></div><div id="sum"></div>
 <label for="pc">Promo code</label><div class="row" style="border:0;padding:0"><input id="pc" placeholder="SAATI10"><button type="button" class="btn alt" id="ap">Apply</button></div>
 <form id="pay"><label for="ad">Shipping address</label><input id="ad" required autocomplete="street-address"><label for="mt">Payment method</label><select id="mt"><option value="card">Credit card (demo)</option><option value="cod">Cash on delivery</option></select>
 <div id="cf"><label for="cc">Card number</label><input id="cc" inputmode="numeric" placeholder="4242 4242 4242 4242" autocomplete="cc-number"></div>
 <p class="err" id="err"></p><button class="btn">Place order</button></form></div></main>`;
 const lines=()=>{const c=calc();
  $('#lines').innerHTML=cart().map(i=>{const p=P.find(x=>x.id===i.id);return `<div class="row"><span>${p.n}</span><span class="qty"><button data-q="${p.id}:-1" aria-label="Remove one ${p.n}">−</button> ${i.q} <button data-q="${p.id}:1" aria-label="Add one ${p.n}">+</button></span><span>${usd(p.p*i.q)}</span></div>`}).join('');
  const left=Math.max(0,300-(c.sub-c.disc));
  $('#sum').innerHTML=`<div class="ship"><i style="width:${Math.min(100,(c.sub-c.disc)/3)}%"></i></div><p>${left?`Add ${usd(left)} more for free shipping`:'You get free shipping'}</p><div class="row"><span>Subtotal</span><span>${usd(c.sub)}</span></div>${promo?`<div class="row ok"><span>Promo SAATI10</span><span>−${usd(c.disc)}</span></div>`:''}<div class="row"><span>Shipping</span><span>${c.ship?usd(c.ship):'Free'}</span></div><div class="row"><b>Total</b><b>${usd(c.tot)}</b></div>`};
 lines();window.relines=()=>cart().length?lines():pages.checkout();
 $('#ap').onclick=()=>{if($('#pc').value.trim().toUpperCase()==='SAATI10'){promo=true;lines();toast('Promo applied: 10% off')}else $('#err').textContent='That code is not valid. Try SAATI10.'};
 $('#cc').oninput=e=>e.target.value=e.target.value.replace(/\D/g,'').slice(0,16).replace(/(.{4})/g,'$1 ').trim();
 $('#mt').onchange=e=>$('#cf').style.display=e.target.value==='card'?'':'none';
 $('#pay').onsubmit=async e=>{e.preventDefault();
  if(!user()){toast('Sign in to place your order');location.hash='#/signin';return}
  if($('#mt').value==='card'&&$('#cc').value.replace(/\s/g,'').length<16)return $('#err').textContent='Enter all 16 digits of your card number.';
  let id='S-'+Date.now().toString(36).toUpperCase();const c=calc(),n=cart().reduce((s,i)=>s+i.q,0);
  if(API){try{const d=await api('/api/checkout',{items:cart(),address:$('#ad').value,method:$('#mt').value,promo:promo?'SAATI10':''});id=d.order_id;c.tot=d.total}catch(x){return $('#err').textContent=x.message}}
  saveCart([]);
  $('#app').innerHTML=`<main class="wrap form"><h1>Order confirmed</h1><p class="ok">Order <b>${id}</b>: ${n} watch${n>1?'es':''}, ${usd(c.tot)}. This is a demo, so no payment was taken.</p><a class="btn" href="#/">Back to home</a></main>`};
}};
document.addEventListener('click',e=>{
 const d=e.target.closest('[data-add],[data-q],[data-wish],[data-open]');
 if(e.target.classList.contains('mb')||e.target.classList.contains('x'))return closeModal();
 if(!d)return;const D=d.dataset;
 if(D.add){const c=cart(),it=c.find(i=>i.id==D.add);it?it.q++:c.push({id:+D.add,q:1});saveCart(c);$('#cn').classList.add('pop');toast(P.find(p=>p.id==D.add).n+' added to cart')}
 if(D.q){const[id,k]=D.q.split(':'),c=cart(),it=c.find(i=>i.id==id);it.q+=+k;saveCart(c.filter(i=>i.q>0));relines()}
 if(D.wish){let w=store.get('wish',[]);const id=+D.wish;w=w.includes(id)?w.filter(x=>x!==id):[...w,id];store.set('wish',w);d.classList.toggle('on');nav();toast(w.includes(id)?'Saved to wishlist':'Removed from wishlist')}
 if(D.open)openModal(+D.open);
});
addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();if(e.key==='Enter'&&e.target.dataset&&e.target.dataset.open)openModal(+e.target.dataset.open)});
setInterval(()=>{const e=$('#cd');if(!e)return;const n=new Date(),m=new Date(n);m.setHours(24,0,0,0);const s=Math.floor((m-n)/1000);e.textContent=[s/3600|0,s/60%60|0,s%60].map(x=>String(x).padStart(2,'0')).join(':')},1000);
function route(){clearInterval(timer);closeModal();const r=(location.hash.replace('#/','')||'home');(pages[r]||pages.home)();nav();tick();scrollTo(0,0)}
addEventListener('hashchange',route);
const msg=['Free shipping over $300','Two-year warranty','30-day returns','Smart and classic collections'];
$('#mq').innerHTML=[...msg,...msg].map(m=>`<span>${m}</span>`).join('').repeat(2);
route();
