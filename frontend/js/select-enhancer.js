/* Accessible custom popup for existing single-select fields.
 * Leaves the original <select> in the DOM as the form's source of truth.
 */
const ROOT_SELECTOR = '#content';
const instances = new WeakMap();

function enhance(native) {
  if (instances.has(native) || native.multiple || native.size > 1 || native.closest('.unn-select-wrap')) return;
  const wrap = document.createElement('span'); wrap.className = 'unn-select-wrap';
  native.parentNode.insertBefore(wrap, native); wrap.append(native);
  native.classList.add('unn-native-select');
  native.tabIndex = -1;
  const trigger = document.createElement('button');
  trigger.type='button'; trigger.className='unn-select-trigger';
  trigger.setAttribute('aria-haspopup','listbox'); trigger.setAttribute('aria-expanded','false');
  const label = document.createElement('span'); label.className='unn-select-label';
  const chevron = document.createElement('span'); chevron.className='unn-select-chevron'; chevron.textContent='⌄';
  trigger.append(label,chevron);
  const menu = document.createElement('div'); menu.className='unn-select-menu'; menu.hidden=true;
  menu.setAttribute('role','listbox');
  wrap.append(trigger,menu);
  let options=[], active=0;
  function sync() {
    const selected=native.selectedOptions[0];
    label.textContent=selected?.textContent || 'Select an option';
    trigger.disabled=native.disabled;
    trigger.title=label.textContent;
    const fresh=[...native.options].map(x=>`${x.value}\u0000${x.textContent}\u0000${x.disabled}`).join('\u0001');
    if (fresh===wrap.dataset.options) return;
    wrap.dataset.options=fresh;
    menu.replaceChildren(); options=[...native.options];
    options.forEach((opt,i)=>{
      const b=document.createElement('button'); b.type='button'; b.className='unn-select-option';
      b.setAttribute('role','option'); b.setAttribute('aria-selected',String(opt.selected));
      b.disabled=opt.disabled; b.textContent=opt.textContent;
      b.addEventListener('click',()=>choose(i));menu.append(b);
    });
  }
  function close(focus=false) {menu.hidden=true;wrap.classList.remove('unn-select-open');trigger.setAttribute('aria-expanded','false'); if(focus) trigger.focus();}
  function open() {
    if(trigger.disabled) return;
    document.querySelectorAll('.unn-select-open').forEach(el=>{if(el!==wrap) el.querySelector('.unn-select-trigger')?.click();});
    sync();menu.hidden=false;wrap.classList.add('unn-select-open');trigger.setAttribute('aria-expanded','true');
    active=Math.max(0,native.selectedIndex);
    focusOption(active);
  }
  function focusOption(i) {
    if(!options.length) return;
    active=(i+options.length)%options.length;
    if(options[active].disabled) { const next=options.findIndex((x,k)=>k>=active&&!x.disabled); if(next>=0)active=next; else return;}
    const btn=menu.children[active];btn?.focus();btn?.scrollIntoView({block:'nearest'});
  }
  function choose(i) {
    if(options[i]?.disabled) return;
    native.selectedIndex=i;
    native.dispatchEvent(new Event('input',{bubbles:true}));
    native.dispatchEvent(new Event('change',{bubbles:true}));
    sync(); [...menu.children].forEach((b,k)=>b.setAttribute('aria-selected',String(k===i)));
    close(true);
  }
  trigger.addEventListener('click',()=>menu.hidden?open():close());
  trigger.addEventListener('keydown',e=>{if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){e.preventDefault();open();}});
  menu.addEventListener('keydown',e=>{
    if(e.key==='Escape'||e.key==='Tab'){close(e.key==='Escape');if(e.key==='Escape')e.preventDefault();}
    else if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();focusOption(active+(e.key==='ArrowDown'?1:-1));}
    else if(e.key==='Home'){e.preventDefault();focusOption(0);}
    else if(e.key==='End'){e.preventDefault();focusOption(options.length-1);}
    else if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(active);}
  });
  native.addEventListener('change',sync);
  const observer=new MutationObserver(sync);observer.observe(native,{childList:true,subtree:true,attributes:true,attributeFilter:['selected','disabled','label']});
  instances.set(native,{sync,observer});sync();
}
export function installSelectEnhancer(){
  const root=document.querySelector(ROOT_SELECTOR);if(!root)return;
  const scan=()=>root.querySelectorAll('select:not([multiple])').forEach(enhance);
  scan();
  new MutationObserver(scan).observe(root,{childList:true,subtree:true});
  document.addEventListener('pointerdown',e=>{
    document.querySelectorAll('.unn-select-open').forEach(w=>{
      if(!w.contains(e.target)) w.querySelector('.unn-select-trigger')?.click();
    });
  });
  // Some forms programmatically update select.value without triggering change.
  document.addEventListener('focusin',e=>{if(e.target.matches?.('.unn-select-trigger'))instances.get(e.target.parentElement.querySelector('select'))?.sync();});
}
