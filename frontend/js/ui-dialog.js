/** Accessible themed confirmation dialog. Resolves true on confirmation. */
export function confirmAction({ title = 'Confirm action', message = 'Continue?', confirmText = 'Confirm', danger = false } = {}) {
  return new Promise(resolve => {
    const prior = document.activeElement;
    const overlay = document.createElement('div');
    overlay.className = 'unn-confirm-overlay';
    const dialog = document.createElement('section');
    dialog.className = 'unn-confirm'; dialog.setAttribute('role','dialog'); dialog.setAttribute('aria-modal','true');
    const h = document.createElement('h2'); h.textContent = title; h.id = 'unn-confirm-heading';
    dialog.setAttribute('aria-labelledby',h.id);
    const p = document.createElement('p'); p.textContent = message;
    const actions = document.createElement('div'); actions.className = 'unn-confirm-actions';
    const cancel = document.createElement('button'); cancel.type='button'; cancel.className='unn-confirm-cancel'; cancel.textContent='Keep';
    const accept = document.createElement('button'); accept.type='button'; accept.className = danger ? 'unn-confirm-danger' : 'unn-confirm-accept'; accept.textContent=confirmText;
    actions.append(cancel,accept);dialog.append(h,p,actions);overlay.append(dialog);
    function finish(value){ document.removeEventListener('keydown',keys);overlay.remove();prior?.focus?.();resolve(value); }
    function keys(e){if(e.key==='Escape'){e.preventDefault();finish(false);}if(e.key==='Tab'){const pair=[cancel,accept];const next=pair.indexOf(document.activeElement);if(e.shiftKey&&next===0){e.preventDefault();accept.focus();}else if(!e.shiftKey&&next===1){e.preventDefault();cancel.focus();}}}
    cancel.addEventListener('click',()=>finish(false));accept.addEventListener('click',()=>finish(true));
    overlay.addEventListener('click',e=>{if(e.target===overlay)finish(false);});
    document.addEventListener('keydown',keys);document.body.append(overlay);cancel.focus();
  });
}
