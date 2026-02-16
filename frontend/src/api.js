const BASE = '/api';

export async function fetchModules(type) {
  const params = type ? `?type=${encodeURIComponent(type)}` : '';
  const res = await fetch(`${BASE}/modules${params}`);
  return res.json();
}

export async function fetchModuleInfo(id, showNc = false) {
  const params = showNc ? '?show_nc=true' : '';
  const res = await fetch(`${BASE}/modules/${encodeURIComponent(id)}${params}`);
  return res.json();
}

export async function fetchBaseSlots(baseId) {
  const res = await fetch(`${BASE}/bases/${encodeURIComponent(baseId)}/slots`);
  return res.json();
}

export async function postCombine(base, slots) {
  const res = await fetch(`${BASE}/combine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base, slots }),
  });
  return res.json();
}
