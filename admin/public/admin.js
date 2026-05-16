const state = {
  module: 'video',
  status: '',
  q: '',
  limit: 24,
  offset: 0,
  total: 0,
  selectedId: null,
  detail: null,
  jsonField: 'scores',
  selectedPerson: null
};

const WORK_FIELDS = [
  'module',
  'submodule',
  'schema_type',
  'title',
  'title_original',
  'year',
  'country',
  'language',
  'total_time',
  'studio',
  'status',
  'introduction',
  'story'
];

const JSON_FIELDS = [
  ['scores', '评分'],
  ['images', '图片'],
  ['external_source', '外部来源'],
  ['release_dates', '上映日期'],
  ['videos', '视频'],
  ['comments', '评论'],
  ['related', '关联作品'],
  ['quotes', '名言'],
  ['other_titles', '别名'],
  ['soundtrack', '原声'],
  ['characters', '角色']
];

const BOOK_FIELDS = [
  'title',
  'title_original',
  'isbn',
  'year',
  'country',
  'language',
  'word_count',
  'publisher',
  'series_id',
  'series_order',
  'status',
  'summary'
];

const BOOK_JSON_FIELDS = [
  ['scores', '评分'],
  ['images', '封面'],
  ['external_source', '外部来源'],
  ['quotes', '名句'],
  ['excerpts', '摘录'],
  ['reviews', '书评'],
  ['related', '关联书籍'],
  ['other_titles', '别名']
];

const DEPARTMENTS = [
  ['direction', '导演'],
  ['writing', '编剧'],
  ['cast', '演员'],
  ['production', '制片'],
  ['music', '音乐'],
  ['original_work', '原作'],
  ['other', '其他']
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

init();

function init() {
  initTheme();
  bindChrome();
  loadSummary();
  loadWorks();
}

function initTheme() {
  const key = 'treasure-theme';
  const root = document.documentElement;
  const saved = localStorage.getItem(key);
  root.dataset.theme = saved || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-theme-toggle]');
    if (!button) return;
    root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem(key, root.dataset.theme);
  });
}

function bindChrome() {
  $$('[data-module]').forEach((button) => {
    button.addEventListener('click', () => {
      state.module = button.dataset.module || '';
      state.offset = 0;
      $$('[data-module]').forEach((item) => item.classList.toggle('is-active', item === button));
      loadWorks();
    });
  });
  $('[data-search]').addEventListener('input', debounce((event) => {
    state.q = event.target.value.trim();
    state.offset = 0;
    loadWorks();
  }, 220));
  $('[data-status]').addEventListener('change', (event) => {
    state.status = event.target.value;
    state.offset = 0;
    loadWorks();
  });
  $('[data-prev]').addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadWorks();
  });
  $('[data-next]').addEventListener('click', () => {
    if (state.offset + state.limit < state.total) {
      state.offset += state.limit;
      loadWorks();
    }
  });
  $('[data-new-work]').addEventListener('click', renderNewWorkForm);
}

async function loadSummary() {
  const data = await api('/api/summary');
  $('[data-summary]').innerHTML = [
    ['作品', data.works],
    ['电影', data.movies],
    ['人物', data.people],
    ['分类', data.categories],
    ['缺主图', data.missingPoster],
    ['最近更新', data.updatedAt ? data.updatedAt.slice(0, 10) : '-']
  ].map(([label, value]) => `<div class="stat-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('');
}

async function loadWorks() {
  const params = new URLSearchParams({
    limit: state.limit,
    offset: state.offset,
    status: state.status,
    q: state.q
  });
  let data;
  if (state.module === 'book') {
    data = await api(`/api/books?${params}`);
  } else {
    params.set('module', state.module);
    data = await api(`/api/works?${params}`);
  }
  state.total = data.total;
  renderWorkList(data.items);
  $('[data-result-line]').textContent = `共 ${data.total} 条，显示 ${data.total ? data.offset + 1 : 0}-${Math.min(data.offset + data.limit, data.total)} 条`;
  $('[data-page-info]').textContent = `${Math.floor(data.offset / data.limit) + 1} / ${Math.max(1, Math.ceil(data.total / data.limit))}`;
}

function renderWorkList(items) {
  $('[data-work-list]').innerHTML = items.map((work) => {
    const meta = [work.year, work.country, work.people?.directors?.join('/')].filter(Boolean).join(' · ');
    const cats = (work.categories || []).slice(0, 3).map((item) => `<span class="chip">${escapeHtml(item.name)}</span>`).join('');
    return `
      <button class="work-card ${work.id === state.selectedId ? 'is-active' : ''}" type="button" data-work-id="${work.id}" data-kind="${work.recordType || 'work'}">
        <img src="${work.posterUrl}" alt="">
        <span class="work-card__body">
          <strong>${escapeHtml(work.title)}</strong>
          <p>${escapeHtml(work.title_original || work.id)}</p>
          <p>${escapeHtml(meta || '待补充')}</p>
          <span class="chip-row">
            <span class="chip">${escapeHtml(work.status)}</span>
            ${cats}
          </span>
        </span>
      </button>
    `;
  }).join('');

  $$('[data-work-id]').forEach((button) => {
    button.addEventListener('click', () => selectRecord(button.dataset.kind, button.dataset.workId));
  });
}

async function selectRecord(kind, id) {
  if (kind === 'book') {
    await selectBook(id);
  } else {
    await selectWork(id);
  }
}

async function selectWork(id) {
  state.selectedId = id;
  state.detail = await api(`/api/works/${encodeURIComponent(id)}`);
  state.jsonField = 'scores';
  state.selectedPerson = null;
  renderEditor();
  loadWorks();
}

async function selectBook(id) {
  state.selectedId = id;
  state.detail = await api(`/api/books/${encodeURIComponent(id)}`);
  state.jsonField = 'scores';
  state.selectedPerson = null;
  renderBookEditor();
  loadWorks();
}

function renderEditor() {
  const { work } = state.detail;
  $('[data-editor]').innerHTML = `
    <form data-work-form>
      <section class="editor-hero">
        <div class="editor-poster"><img src="${work.posterUrl}" alt=""></div>
        <div class="editor-title">
          <p class="eyebrow">${escapeHtml(work.id)} · ${escapeHtml(work.module)} / ${escapeHtml(work.submodule || '-')}</p>
          <h2>${escapeHtml(work.title)}</h2>
          <p class="form-note">保存后直接写入本地 SQLite。需要刷新前台时，再运行现有导出脚本。</p>
          <div class="editor-actions">
            <button class="button button--primary" type="submit">保存基础信息</button>
            <button class="button button--danger" type="button" data-delete-work>删除作品</button>
          </div>
        </div>
      </section>
      ${renderBasicFields(work)}
    </form>
    ${renderJsonSection(work)}
    ${renderPeopleSection()}
    ${renderCategorySection()}
  `;
  bindEditorEvents();
}

function renderBookEditor() {
  const { book } = state.detail;
  $('[data-editor]').innerHTML = `
    <form data-book-form>
      <section class="editor-hero">
        <div class="editor-poster"><img src="${book.posterUrl}" alt=""></div>
        <div class="editor-title">
          <p class="eyebrow">${escapeHtml(book.id)} · book</p>
          <h2>${escapeHtml(book.title)}</h2>
          <p class="form-note">书籍当前使用独立 books 表。此入口提供基础内容和 JSON 字段维护。</p>
          <div class="editor-actions">
            <button class="button button--primary" type="submit">保存书籍信息</button>
            <button class="button button--danger" type="button" data-delete-book>删除书籍</button>
          </div>
        </div>
      </section>
      ${renderBookFields(book)}
    </form>
    ${renderBookJsonSection(book)}
  `;
  bindBookEditorEvents();
}

function renderBasicFields(work) {
  const fields = [
    ['title', '标题', 'input'],
    ['title_original', '原名', 'input'],
    ['year', '年份', 'number'],
    ['country', '国家/地区', 'input'],
    ['language', '语言', 'input'],
    ['total_time', '片长(分钟)', 'number'],
    ['studio', '制片方', 'input'],
    ['status', '状态', 'select'],
    ['module', '模块', 'select-module'],
    ['submodule', '子模块', 'input'],
    ['schema_type', '内容类型', 'input'],
    ['introduction', '简介', 'textarea'],
    ['story', '剧情/长文', 'textarea']
  ];

  return `
    <section class="editor-section">
      <div class="section-head"><h3>基础信息</h3></div>
      <div class="editor-grid">
        ${fields.map(([name, label, type]) => renderField(name, label, type, work[name])).join('')}
      </div>
    </section>
  `;
}

function renderBookFields(book) {
  const fields = [
    ['title', '书名', 'input'],
    ['title_original', '原名', 'input'],
    ['isbn', 'ISBN', 'input'],
    ['year', '年份', 'number'],
    ['country', '国家/地区', 'input'],
    ['language', '语言', 'input'],
    ['word_count', '字数', 'number'],
    ['publisher', '出版社', 'input'],
    ['series_id', '系列 ID', 'input'],
    ['series_order', '系列顺序', 'number'],
    ['status', '状态', 'select'],
    ['summary', '简介', 'textarea']
  ];
  return `
    <section class="editor-section">
      <div class="section-head"><h3>基础信息</h3></div>
      <div class="editor-grid">
        ${fields.map(([name, label, type]) => renderField(name, label, type, book[name])).join('')}
      </div>
    </section>
  `;
}

function renderField(name, label, type, value) {
  const wide = type === 'textarea' ? ' field--wide' : '';
  if (type === 'textarea') {
    return `<label class="field${wide}"><span>${label}</span><textarea name="${name}">${escapeHtml(value || '')}</textarea></label>`;
  }
  if (type === 'select') {
    return `
      <label class="field"><span>${label}</span>
        <select name="${name}">
          ${['draft', 'published', 'archived'].map((item) => `<option value="${item}" ${item === value ? 'selected' : ''}>${item}</option>`).join('')}
        </select>
      </label>
    `;
  }
  if (type === 'select-module') {
    return `
      <label class="field"><span>${label}</span>
        <select name="${name}">
          ${['video', 'anime', 'book', 'music', 'game'].map((item) => `<option value="${item}" ${item === value ? 'selected' : ''}>${item}</option>`).join('')}
        </select>
      </label>
    `;
  }
  return `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${escapeAttr(value ?? '')}"></label>`;
}

function renderJsonSection(work) {
  const activeValue = formatJson(work[state.jsonField]);
  return `
    <section class="editor-section">
      <div class="section-head">
        <h3>结构化字段</h3>
        <button class="button button--primary" type="button" data-save-json>保存 JSON</button>
      </div>
      <div class="json-tabs">
        ${JSON_FIELDS.map(([field, label]) => `<button class="json-tab ${field === state.jsonField ? 'is-active' : ''}" type="button" data-json-field="${field}">${label}</button>`).join('')}
      </div>
      <textarea class="json-editor" data-json-editor spellcheck="false">${escapeHtml(activeValue)}</textarea>
      <p class="form-note">这些字段会按 JSON 校验后保存。空白表示 NULL。</p>
    </section>
  `;
}

function renderBookJsonSection(book) {
  const active = BOOK_JSON_FIELDS.some(([field]) => field === state.jsonField) ? state.jsonField : 'scores';
  state.jsonField = active;
  return `
    <section class="editor-section">
      <div class="section-head">
        <h3>结构化字段</h3>
        <button class="button button--primary" type="button" data-save-book-json>保存 JSON</button>
      </div>
      <div class="json-tabs">
        ${BOOK_JSON_FIELDS.map(([field, label]) => `<button class="json-tab ${field === state.jsonField ? 'is-active' : ''}" type="button" data-book-json-field="${field}">${label}</button>`).join('')}
      </div>
      <textarea class="json-editor" data-json-editor spellcheck="false">${escapeHtml(formatJson(book[state.jsonField]))}</textarea>
    </section>
  `;
}

function renderPeopleSection() {
  const rows = state.detail.people.map((item) => `
    <div class="relation-row" data-relation-id="${item.id}">
      <img src="${item.avatarUrl}" alt="">
      <div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.name_en || item.public_person_id || '')}</span></div>
      <select data-r-field="department">${DEPARTMENTS.map(([value, label]) => `<option value="${value}" ${item.department === value ? 'selected' : ''}>${label}</option>`).join('')}</select>
      <input data-r-field="role" value="${escapeAttr(item.role || '')}" placeholder="职位">
      <input data-r-field="character" value="${escapeAttr(item.character || '')}" placeholder="角色">
      <button class="icon-button" type="button" data-remove-person>×</button>
    </div>
  `).join('');

  return `
    <section class="editor-section">
      <div class="section-head"><h3>演职员关系</h3><span class="form-note">${state.detail.people.length} 人</span></div>
      <div class="relation-stack">${rows || '<p class="form-note">暂无人物关系。</p>'}</div>
      <div class="relation-add">
        <label><span>检索人物</span><input data-person-search placeholder="姓名 / 英文名 / person_id"></label>
        <label><span>部门</span><select data-add-department>${DEPARTMENTS.map(([value, label]) => `<option value="${value}">${label}</option>`).join('')}</select></label>
        <label><span>职位</span><input data-add-role placeholder="主演/导演"></label>
        <label><span>角色</span><input data-add-character placeholder="角色名"></label>
        <button class="button button--primary" type="button" data-add-person>添加</button>
        <div class="person-results" data-person-results></div>
      </div>
    </section>
  `;
}

function renderCategorySection() {
  const existing = state.detail.categories.map((item) => `
    <span class="category-pill">
      ${escapeHtml(item.group)} · ${escapeHtml(item.name)}
      <button class="icon-button" type="button" data-remove-category="${item.id}">×</button>
    </span>
  `).join('');

  return `
    <section class="editor-section">
      <div class="section-head"><h3>类型与标签</h3></div>
      <div class="category-list">${existing || '<p class="form-note">暂无分类。</p>'}</div>
      <div class="relation-add">
        <label><span>选择分类</span><select data-category-select></select></label>
        <label><span>排序</span><input data-category-order type="number" value="0"></label>
        <button class="button button--primary" type="button" data-add-category>添加分类</button>
      </div>
    </section>
  `;
}

function bindEditorEvents() {
  $('[data-work-form]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(WORK_FIELDS.filter((field) => form.has(field)).map((field) => [field, form.get(field)]));
    await api(`/api/works/${state.selectedId}`, { method: 'PATCH', body: payload });
    toast('基础信息已保存');
    await selectWork(state.selectedId);
    await loadSummary();
  });

  $('[data-delete-work]').addEventListener('click', async () => {
    if (!confirm(`确认删除作品 ${state.selectedId}？这个操作会级联删除关系。`)) return;
    const typed = prompt('请输入作品 ID 以确认删除');
    if (typed !== state.selectedId) return;
    await api(`/api/works/${state.selectedId}?confirm=${encodeURIComponent(state.selectedId)}`, { method: 'DELETE' });
    state.selectedId = null;
    state.detail = null;
    $('[data-editor]').innerHTML = '<div class="empty-editor"><h2>已删除</h2><p>请选择其他作品继续维护。</p></div>';
    await loadWorks();
    await loadSummary();
  });

  $$('[data-json-field]').forEach((button) => {
    button.addEventListener('click', () => {
      state.jsonField = button.dataset.jsonField;
      renderEditor();
    });
  });

  $('[data-save-json]').addEventListener('click', async () => {
    const value = $('[data-json-editor]').value.trim();
    await api(`/api/works/${state.selectedId}`, { method: 'PATCH', body: { [state.jsonField]: value || null } });
    toast(`${state.jsonField} 已保存`);
    await selectWork(state.selectedId);
  });

  $$('[data-relation-id]').forEach((row) => {
    row.addEventListener('change', debounce(async () => {
      const payload = {};
      $$('[data-r-field]', row).forEach((field) => payload[field.dataset.rField] = field.value);
      await api(`/api/work-people/${row.dataset.relationId}`, { method: 'PATCH', body: payload });
      toast('人物关系已保存');
    }, 260));
  });

  $$('[data-remove-person]').forEach((button) => {
    button.addEventListener('click', async () => {
      const row = button.closest('[data-relation-id]');
      await api(`/api/work-people/${row.dataset.relationId}`, { method: 'DELETE' });
      toast('人物关系已移除');
      await selectWork(state.selectedId);
    });
  });

  $('[data-person-search]').addEventListener('input', debounce(searchPersons, 240));
  $('[data-add-person]').addEventListener('click', addSelectedPerson);
  loadCategoryOptions();
  $('[data-add-category]').addEventListener('click', addCategory);
  $$('[data-remove-category]').forEach((button) => {
    button.addEventListener('click', async () => {
      await api(`/api/work-categories/${button.dataset.removeCategory}`, { method: 'DELETE' });
      toast('分类已移除');
      await selectWork(state.selectedId);
    });
  });
}

function bindBookEditorEvents() {
  $('[data-book-form]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(BOOK_FIELDS.filter((field) => form.has(field)).map((field) => [field, form.get(field)]));
    await api(`/api/books/${state.selectedId}`, { method: 'PATCH', body: payload });
    toast('书籍信息已保存');
    await selectBook(state.selectedId);
    await loadSummary();
  });
  $('[data-delete-book]').addEventListener('click', async () => {
    if (!confirm(`确认删除书籍 ${state.selectedId}？`)) return;
    const typed = prompt('请输入书籍 ID 以确认删除');
    if (typed !== state.selectedId) return;
    await api(`/api/books/${state.selectedId}?confirm=${encodeURIComponent(state.selectedId)}`, { method: 'DELETE' });
    state.selectedId = null;
    state.detail = null;
    $('[data-editor]').innerHTML = '<div class="empty-editor"><h2>已删除</h2><p>请选择其他作品继续维护。</p></div>';
    await loadWorks();
    await loadSummary();
  });
  $$('[data-book-json-field]').forEach((button) => {
    button.addEventListener('click', () => {
      state.jsonField = button.dataset.bookJsonField;
      renderBookEditor();
    });
  });
  $('[data-save-book-json]').addEventListener('click', async () => {
    const value = $('[data-json-editor]').value.trim();
    await api(`/api/books/${state.selectedId}`, { method: 'PATCH', body: { [state.jsonField]: value || null } });
    toast(`${state.jsonField} 已保存`);
    await selectBook(state.selectedId);
  });
}

async function searchPersons() {
  const q = $('[data-person-search]').value.trim();
  const box = $('[data-person-results]');
  state.selectedPerson = null;
  if (!q) {
    box.innerHTML = '';
    return;
  }
  const data = await api(`/api/persons?q=${encodeURIComponent(q)}`);
  box.innerHTML = data.items.map((person) => `
    <button class="person-option" type="button" data-person-id="${person.id}">
      <span>${escapeHtml(person.name)} ${person.name_en ? ` / ${escapeHtml(person.name_en)}` : ''}</span>
      <span>${escapeHtml(person.person_id)}</span>
    </button>
  `).join('') || '<p class="form-note">没有找到，可先到数据库或后续人物管理入口新增。</p>';
  $$('[data-person-id]', box).forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedPerson = Number(button.dataset.personId);
      $$('[data-person-id]', box).forEach((item) => item.classList.toggle('is-active', item === button));
      toast('已选择人物');
    });
  });
}

async function addSelectedPerson() {
  if (!state.selectedPerson) {
    toast('请先检索并选择人物');
    return;
  }
  await api(`/api/works/${state.selectedId}/people`, {
    method: 'POST',
    body: {
      person_id: state.selectedPerson,
      department: $('[data-add-department]').value,
      role: $('[data-add-role]').value,
      character: $('[data-add-character]').value
    }
  });
  toast('人物已添加');
  await selectWork(state.selectedId);
}

async function loadCategoryOptions() {
  const data = await api('/api/categories?module=video');
  const select = $('[data-category-select]');
  if (!select) return;
  select.innerHTML = data.items.map((item) => `<option value="${item.id}">${escapeHtml(item.group)} · ${escapeHtml(item.name)}</option>`).join('');
}

async function addCategory() {
  const id = $('[data-category-select]').value;
  if (!id) return;
  await api(`/api/works/${state.selectedId}/categories`, {
    method: 'POST',
    body: { category_id: Number(id), order: Number($('[data-category-order]').value || 0) }
  });
  toast('分类已添加');
  await selectWork(state.selectedId);
}

function renderNewWorkForm() {
  if (state.module === 'book') {
    renderNewBookForm();
    return;
  }
  $('[data-editor]').innerHTML = `
    <section class="editor-section">
      <div class="section-head"><h3>新增作品</h3></div>
      <form data-create-work class="editor-grid">
        ${renderField('id', '作品 ID', 'input', '')}
        ${renderField('title', '标题', 'input', '')}
        ${renderField('title_original', '原名', 'input', '')}
        ${renderField('year', '年份', 'number', '')}
        ${renderField('module', '模块', 'select-module', 'video')}
        ${renderField('submodule', '子模块', 'input', 'movie')}
        ${renderField('schema_type', '内容类型', 'input', 'live_action_movie')}
        ${renderField('status', '状态', 'select', 'draft')}
        <div class="field field--wide"><button class="button button--primary" type="submit">创建作品</button></div>
      </form>
    </section>
  `;
  $('[data-create-work]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    const detail = await api('/api/works', { method: 'POST', body: payload });
    toast('作品已创建');
    state.selectedId = detail.work.id;
    await loadWorks();
    await selectWork(detail.work.id);
    await loadSummary();
  });
}

function renderNewBookForm() {
  $('[data-editor]').innerHTML = `
    <section class="editor-section">
      <div class="section-head"><h3>新增书籍</h3></div>
      <form data-create-book class="editor-grid">
        ${renderField('id', '书籍 ID', 'input', '')}
        ${renderField('title', '书名', 'input', '')}
        ${renderField('title_original', '原名', 'input', '')}
        ${renderField('isbn', 'ISBN', 'input', '')}
        ${renderField('year', '年份', 'number', '')}
        ${renderField('status', '状态', 'select', 'draft')}
        <div class="field field--wide"><button class="button button--primary" type="submit">创建书籍</button></div>
      </form>
    </section>
  `;
  $('[data-create-book]').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    const detail = await api('/api/books', { method: 'POST', body: payload });
    toast('书籍已创建');
    state.selectedId = detail.book.id;
    await loadWorks();
    await selectBook(detail.book.id);
    await loadSummary();
  });
}

async function api(url, options = {}) {
  const init = { method: options.method || 'GET', headers: {} };
  if (options.body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(url, init);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function formatJson(value) {
  if (!value) return '';
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function toast(message) {
  const el = $('[data-toast]');
  el.hidden = false;
  el.textContent = message;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    el.hidden = true;
  }, 2200);
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value);
}
