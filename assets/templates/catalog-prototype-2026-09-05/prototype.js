(() => {
  const data = window.catalogSnapshot;
  const query = document.getElementById('query');
  const stateFilter = document.getElementById('state-filter');
  const results = document.getElementById('results');
  const count = document.getElementById('result-count');
  const detail = document.getElementById('detail');
  const help = document.getElementById('status-help');
  const labels = { live:'Live catalog entry', beta:'Beta', unavailable:'Unavailable' };
  let branch = 'all';
  let opener;
  const esc = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  document.getElementById('branches').innerHTML = data.branches.map((b,i) => `<button class="branch-choice" type="button" data-branch="${esc(b.slug)}" aria-pressed="false"><span>${String(i+1).padStart(2,'0')}</span>${esc(b.name)}</button>`).join('');
  function syncUrl(replace = false) {
    const url = new URL(location.href);
    if (query.value) url.searchParams.set('q', query.value); else url.searchParams.delete('q');
    if (branch !== 'all') url.searchParams.set('branch',branch); else url.searchParams.delete('branch');
    if (stateFilter.value !== 'all') url.searchParams.set('state',stateFilter.value); else url.searchParams.delete('state');
    try { history[replace ? 'replaceState':'pushState']({},'',url); } catch (_) {}
  }
  function render(write = true) {
    const terms = query.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const entries = data.entries.filter(e => (branch === 'all' || e.branch === branch) && (stateFilter.value === 'all' || stateFilter.value === e.state) && terms.every(t => [e.title,e.description,e.branchLabel].join(' ').toLowerCase().includes(t)));
    count.textContent = `${entries.length} ${entries.length === 1 ? 'Tool-ette' : 'Tool-ettes'}${branch === 'all' ? ' across the Toolbox' : ' in '+ data.branches.find(b=>b.slug===branch).name}`;
    document.querySelectorAll('[data-branch]').forEach(b => { const active = b.dataset.branch===branch; b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active)); });
    results.innerHTML = entries.length ? entries.map(e => `<article class="tool-card"><div class="card-top"><span class="tool-number">${esc(e.number)}</span><span class="state ${esc(e.state)}">${labels[e.state]}</span></div><h3>${esc(e.title)}</h3><p>${esc(e.description)}</p><button type="button" data-detail="${esc(e.url)}" aria-label="Read ${esc(e.title)} details">Read the detail <span aria-hidden="true">↗</span></button></article>`).join('') : '<p class="empty">No catalog entries match these filters. Try another task or reset the filters.</p>';
    if (write) syncUrl(true);
  }
  document.querySelectorAll('[data-branch]').forEach(b=>b.addEventListener('click',()=>{branch=b.dataset.branch;render();}));
  query.addEventListener('input',()=>render());
  stateFilter.addEventListener('change',()=>render());
  document.querySelector('.search-row').addEventListener('submit',e=>e.preventDefault());
  document.querySelector('.search-row').addEventListener('reset',()=>{setTimeout(()=>render(),0);});
  document.getElementById('reset-filters').addEventListener('click',()=>{query.value='';stateFilter.value='all';branch='all';render();query.focus();});
  const statusText = state => state === 'unavailable' ? 'This concept can be explored in the catalog. Its ChatGPT destination is currently unavailable, so this detail offers another internal route.' : state === 'beta' ? 'The catalog marks this Tool-ette as beta. A reviewed destination exists, but the external experience is not presented as finished or behavior-verified.' : 'This is the one currently live Tool-ette catalog page. The live label describes publication state; external GPT behavior requires separate verification.';
  results.addEventListener('click', event => {
    const button=event.target.closest('[data-detail]'); if(!button)return;
    const entry=data.entries.find(e=>e.url===button.dataset.detail); opener=button;
    document.getElementById('detail-body').innerHTML=`<p class="eyebrow">${esc(entry.branchLabel)} / ${esc(entry.number)}</p><span class="state ${entry.state}">${labels[entry.state]}</span><h2 id="detail-title">${esc(entry.title)}</h2><p class="detail-description">${esc(entry.description)}</p><div class="detail-context"><h3>Before you choose</h3><p>${statusText(entry.state)}</p></div><p class="small-note">When a tool opens outside this catalog, check that service’s access and privacy settings before sharing personal information.</p><div class="detail-options"><a class="primary" href="https://glee-fully.tools${esc(entry.url)}" target="_blank" rel="noopener noreferrer">Read the current catalog page ↗</a><button type="button" id="explore-branch">Explore this branch</button></div>`;
    if (entry.url.includes('05d-scheduling-wizard')) {
      document.querySelector('#detail-body .detail-context').insertAdjacentHTML('beforebegin','<div class="detail-context"><h3>What to bring</h3><p>A task list, upcoming bill dates, events, and the time available in your week.</p><h3>Intended next output</h3><p>A calendar-ready plan to review yourself. This is a concept pattern from the current catalog; calendar integration, reminders, and exports are not verified.</p></div>');
    }
    document.getElementById('explore-branch').addEventListener('click',()=>{branch=entry.branch;stateFilter.value='all';query.value='';opener=null;detail.close();render();const heading=document.getElementById('catalog-title');heading.tabIndex=-1;heading.focus();heading.scrollIntoView();});
    detail.showModal();
  });
  detail.addEventListener('close',()=>opener?.focus());
  [detail,help].forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}}));
  document.getElementById('show-status-help').addEventListener('click',()=>help.showModal());
  document.getElementById('open-guide').addEventListener('click',()=>help.showModal());
  document.getElementById('theme-toggle').addEventListener('click',event=>{const dark=document.documentElement.dataset.theme!=='dark';document.documentElement.dataset.theme=dark?'dark':'light';event.currentTarget.setAttribute('aria-pressed',String(dark));event.currentTarget.textContent=dark?'Light mode':'Dark mode';});
  const params = new URL(location.href).searchParams;
  query.value=params.get('q')||'';branch=data.branches.some(b=>b.slug===params.get('branch'))?params.get('branch'):'all';stateFilter.value=['live','beta','unavailable'].includes(params.get('state'))?params.get('state'):'all';
  render(false);
})();
