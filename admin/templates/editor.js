import { Editor } from 'https://esm.sh/@tiptap/core@2.10.0';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.10.0';
import Image from 'https://esm.sh/@tiptap/extension-image@2.10.0';
import Link from 'https://esm.sh/@tiptap/extension-link@2.10.0';
import Placeholder from 'https://esm.sh/@tiptap/extension-placeholder@2.10.0';

const turndown = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced', bulletListMarker: '-' });
turndown.addRule('strikethrough', { filter: ['del', 's'], replacement: function (c) { return '~~' + c + '~~'; } });

let currentSlug = null;
let dirty = false;
let saving = false;

const editor = new Editor({
  element: document.getElementById('editor'),
  extensions: [
    StarterKit,
    Image,
    Link.configure({ openOnClick: false }),
    Placeholder.configure({ placeholder: 'Start writing... paste images to upload them.' }),
  ],
  content: '',
  onUpdate: function () { dirty = true; },
});

const $ = function (id) { return document.getElementById(id); };
const titleEl = $('title');
const draftEl = $('draft');
const saveBtn = $('saveBtn');
const listEl = $('postList');
const toastEl = $('toast');

function toast(msg, err) {
  toastEl.textContent = msg;
  toastEl.className = 'toast show' + (err ? ' err' : '');
  setTimeout(function () { toastEl.className = 'toast'; }, 3000);
}

async function api(path, opts) {
  opts = opts || {};
  const res = await fetch(path, {
    method: opts.method || 'GET',
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    headers: Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {}),
    credentials: 'same-origin',
  });
  if (res.status === 401) { window.location.href = '/auth/login'; return null; }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || j.error || msg; } catch (e) {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function uploadImage(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: fd, credentials: 'same-origin' });
  if (res.status === 401) { window.location.href = '/auth/login'; return null; }
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = j.detail || j.error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return (await res.json()).url;
}

// Paste image -> upload -> insert
editor.view.dom.addEventListener('paste', async function (e) {
  const items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (it.type && it.type.indexOf('image/') === 0) {
      e.preventDefault();
      const file = it.getAsFile();
      if (!file) return;
      try {
        const url = await uploadImage(file);
        editor.chain().focus().setImage({ src: url }).run();
        toast('Image uploaded');
      } catch (err) {
        toast('Image upload failed: ' + err.message, true);
      }
      return;
    }
  }
});

// Toolbar
document.getElementById('toolbar').addEventListener('click', async function (e) {
  const btn = e.target.closest('button[data-cmd]');
  if (!btn) return;
  const cmd = btn.dataset.cmd;
  const ch = editor.chain().focus();
  if (cmd === 'h1' || cmd === 'h2' || cmd === 'h3') ch.toggleHeading({ level: parseInt(cmd[1], 10) }).run();
  else if (cmd === 'bold') ch.toggleBold().run();
  else if (cmd === 'italic') ch.toggleItalic().run();
  else if (cmd === 'code') ch.toggleCode().run();
  else if (cmd === 'bulletList') ch.toggleBulletList().run();
  else if (cmd === 'orderedList') ch.toggleOrderedList().run();
  else if (cmd === 'blockquote') ch.toggleBlockquote().run();
  else if (cmd === 'link') {
    const url = prompt('Link URL:');
    if (url) ch.setLink({ href: url }).run();
  } else if (cmd === 'image') {
    $('filePicker').click();
  }
  updateToolbar();
});

$('filePicker').addEventListener('change', async function (e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  try {
    const url = await uploadImage(file);
    editor.chain().focus().setImage({ src: url }).run();
    toast('Image uploaded');
  } catch (err) {
    toast('Image upload failed: ' + err.message, true);
  }
  e.target.value = '';
});

function updateToolbar() {
  document.querySelectorAll('#toolbar button[data-cmd]').forEach(function (btn) {
    const cmd = btn.dataset.cmd;
    let active = false;
    if (cmd === 'h1') active = editor.isActive('heading', { level: 1 });
    else if (cmd === 'h2') active = editor.isActive('heading', { level: 2 });
    else if (cmd === 'h3') active = editor.isActive('heading', { level: 3 });
    else active = editor.isActive(cmd);
    btn.classList.toggle('active', active);
  });
}
editor.on('selectionUpdate', updateToolbar);
editor.on('transaction', updateToolbar);

// Sidebar list
async function loadList() {
  let posts;
  try { posts = await api('/api/posts'); } catch (err) { toast(err.message, true); return; }
  if (!posts) return;
  listEl.innerHTML = '';
  posts.forEach(function (p) {
    const li = document.createElement('li');
    li.dataset.slug = p.slug;
    if (p.slug === currentSlug) li.classList.add('active');
    const t = document.createElement('span');
    t.className = 't';
    t.textContent = p.title;
    li.appendChild(t);
    if (p.draft) {
      const d = document.createElement('span');
      d.className = 'draft';
      d.textContent = 'draft';
      li.appendChild(d);
    }
    const del = document.createElement('span');
    del.className = 'del';
    del.textContent = 'x';
    del.title = 'Delete';
    del.addEventListener('click', async function (ev) {
      ev.stopPropagation();
      if (!confirm('Delete "' + p.title + '"? This commits + pushes.')) return;
      try { await api('/api/posts/' + encodeURIComponent(p.slug), { method: 'DELETE' }); }
      catch (err) { toast(err.message, true); return; }
      if (currentSlug === p.slug) newPost();
      loadList();
      toast('Deleted');
    });
    li.appendChild(del);
    li.addEventListener('click', function () { openPost(p.slug); });
    listEl.appendChild(li);
  });
}

async function openPost(slug) {
  let p;
  try { p = await api('/api/posts/' + encodeURIComponent(slug)); } catch (err) { toast(err.message, true); return; }
  if (!p) return;
  currentSlug = slug;
  titleEl.value = p.title;
  draftEl.checked = !!p.draft;
  const html = marked.parse(p.markdown || '');
  editor.commands.setContent(html, false);
  dirty = false;
  saveBtn.textContent = p.draft ? 'Save draft' : 'Save';
  loadList();
}

function newPost() {
  currentSlug = null;
  titleEl.value = '';
  draftEl.checked = false;
  editor.commands.clearContent();
  dirty = false;
  saveBtn.textContent = 'Publish';
  loadList();
}

$('newBtn').addEventListener('click', newPost);

saveBtn.addEventListener('click', async function () {
  if (saving) return;
  const title = titleEl.value.trim();
  if (!title) { toast('Title is required', true); return; }
  saving = true;
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  const markdown = turndown.turndown(editor.getHTML());
  const draft = draftEl.checked;
  const body = { title: title, draft: draft, markdown: markdown };
  try {
    let res;
    if (currentSlug) {
      res = await api('/api/posts/' + encodeURIComponent(currentSlug), { method: 'PUT', body: body });
    } else {
      res = await api('/api/posts', { method: 'POST', body: body });
    }
    if (res && res.slug) {
      currentSlug = res.slug;
      saveBtn.textContent = draft ? 'Save draft' : 'Save';
      dirty = false;
      toast(draft ? 'Draft saved & pushed' : 'Published & pushed');
      loadList();
    }
  } catch (err) {
    toast(err.message, true);
  } finally {
    saving = false;
    saveBtn.disabled = false;
    if (currentSlug) saveBtn.textContent = draftEl.checked ? 'Save draft' : 'Save';
    else saveBtn.textContent = 'Publish';
  }
});

// User box + logout
(async function () {
  let me;
  try { me = await api('/api/me'); } catch (e) { return; }
  if (!me) return;
  const box = $('userBox');
  if (me.picture) {
    const img = document.createElement('img');
    img.src = me.picture;
    img.alt = '';
    box.appendChild(img);
  }
  const who = document.createElement('span');
  who.className = 'who';
  who.textContent = me.email;
  box.appendChild(who);
  const a = document.createElement('a');
  a.href = '#';
  a.textContent = 'Logout';
  a.addEventListener('click', function (e) {
    e.preventDefault();
    fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' })
      .then(function () { window.location.href = '/auth/login'; });
  });
  box.appendChild(a);
})();

loadList();
