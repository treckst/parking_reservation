// Controller dependencies are injectable; the browser uses native storage and fetch.
export class ChatController {
  constructor({storage, request, id, render, delay = ms => new Promise(r => setTimeout(r, ms))}) {
    Object.assign(this, {storage, request, id, render, delay});
    this.data = JSON.parse(storage.getItem('parking-chat') || 'null') || {};
    this.data.tab_id ||= this.id();
    this.messages = []; this.draft = this.data.draft || ''; this.epoch = 0;
    this.state = 'idle'; this.error = ''; this.retryable = false;
  }
  save() {
    this.storage.setItem('parking-chat', JSON.stringify({...this.data, draft:this.draft}));
    this.render(this);
  }
  async start(detach = false) {
    if (detach || !this.data.thread_id) return this.newChat();
    const epoch = this.epoch;
    try {
      const conversation = await this.request(`/api/threads/${this.data.thread_id}/conversation`);
      if (epoch !== this.epoch) return;
      this.messages = conversation.messages;
      if (this.data.pending) {
        this.state = 'recovering'; this.save();
        await this.recover(epoch);
      } else this.save();
    } catch { this.error = 'Conversation unavailable. Please try again later.'; this.save(); }
  }
  async newChat() {
    const epoch = ++this.epoch;
    this.state = 'pending'; this.error = ''; this.retryable = false;
    const tab_id = this.data.tab_id || this.id();
    this.data = {tab_id}; this.messages = []; this.draft = ''; this.save();
    try {
      const thread = await this.request('/api/threads', {method:'POST'});
      if (epoch !== this.epoch) return;
      this.data = {thread_id:thread.thread_id, tab_id};
      this.state = 'idle'; this.save();
    } catch { if (epoch === this.epoch) {this.error = 'Unable to start chat. Please try New chat again.'; this.save();} }
  }
  edit(text) { this.draft = text; this.save(); }
  async send() {
    if (['pending','recovering'].includes(this.state) || !this.data.thread_id || !this.draft.trim()) return;
    const message = this.draft;
    this.draft = ''; this.error = ''; this.retryable = false;
    this.data.pending = {request_id:this.id(), message};
    this.messages.push({role:'user', text:message, request_id:this.data.pending.request_id});
    this.state = 'pending'; this.save();
    await this.submit(this.epoch);
  }
  async submit(epoch) {
    try {
      const result = await this.request('/api/chat', {method:'POST', body:JSON.stringify({
        thread_id:this.data.thread_id, ...this.data.pending,
      })});
      if (epoch !== this.epoch) return;
      if (!this.accept(result)) await this.recover(epoch);
    } catch {
      if (epoch !== this.epoch) return;
      // Lost POST acknowledgements recover through GET; never submit blindly again.
      this.state = 'recovering'; this.save(); await this.recover(epoch);
    }
  }
  accept(result) {
    if (!this.data.pending || result.request_id !== this.data.pending.request_id || result.thread_id !== this.data.thread_id) return false;
    if (result.status === 'completed') {
      if (!this.messages.some(m => m.role === 'assistant' && m.request_id === result.request_id)) {
        this.messages.push({role:'assistant', text:result.reply.final_reply, request_id:result.request_id});
      }
      delete this.data.pending; this.state = 'completed'; this.error = ''; this.retryable = false;
      this.save(); return true;
    }
    if (result.status === 'failed') {
      this.state = 'proven_failed'; this.error = 'Your question could not be completed. You can retry it.';
      this.retryable = result.retryable === true; this.save(); return true;
    }
    this.state = 'recovering'; this.save(); return false;
  }
  async recover(epoch = this.epoch) {
    for (let attempt = 0; attempt < 30 && epoch === this.epoch && this.data.pending; attempt++) {
      await this.delay(Math.min(1000 * (attempt + 1), 5000));
      if (epoch !== this.epoch) return;
      try {
        const result = await this.request(`/api/threads/${this.data.thread_id}/requests/${this.data.pending.request_id}`);
        if (epoch !== this.epoch) return;
        if (this.accept(result)) return;
      } catch { /* Keep uncertain work for a later refresh, without resubmission. */ }
    }
    if (epoch === this.epoch && this.data.pending) {
      this.error = 'The reply is not available yet. Refresh to reconnect to your question.';
      this.state = 'recovering'; this.save();
    }
  }
  async retry() {
    if (!this.retryable || this.state !== 'proven_failed') return;
    this.state = 'pending'; this.retryable = false; this.error = ''; this.save();
    await this.submit(this.epoch);
  }
}

export async function claimTab(locks, key) {
  if (!locks) return false; // No collision primitive: safely detach from stored thread.
  let report;
  const acquired = new Promise(resolve => {report = resolve;});
  void locks.request(`parking:${key}`, {ifAvailable:true}, async lock => {
    report(Boolean(lock));
    if (lock) await new Promise(resolve => globalThis.addEventListener('pagehide', resolve, {once:true}));
  });
  return acquired;
}

if (typeof document !== 'undefined') {
  const elements = Object.fromEntries(['messages','message','send','new-chat','retry','error','composer'].map(id => [id,document.getElementById(id)]));
  const request = async (url, options = {}) => {
    const response = await fetch(url, {credentials:'same-origin', ...options,
      headers:{'Content-Type':'application/json'}, signal:AbortSignal.timeout(25000)});
    if (!response.ok) throw new Error('Request unavailable');
    return response.json();
  };
  const controller = new ChatController({storage:sessionStorage, request, id:() => crypto.randomUUID(), render:chat => {
    elements.messages.replaceChildren(...chat.messages.map(message => {
      const node = document.createElement('p'); node.className = `message ${message.role}`;
      node.textContent = message.text; return node;
    }));
    elements.send.disabled = ['pending','recovering'].includes(chat.state) || !chat.data.thread_id || !chat.draft.trim();
    elements.retry.hidden = !chat.retryable;
    elements.error.textContent = chat.error;
    if (elements.message.value !== chat.draft) elements.message.value = chat.draft;
  }});
  elements.message.addEventListener('input', () => controller.edit(elements.message.value));
  elements.composer.addEventListener('submit', event => {event.preventDefault(); void controller.send();});
  elements['new-chat'].addEventListener('click', () => void controller.newChat());
  elements.retry.addEventListener('click', () => void controller.retry());
  const tab = controller.data.tab_id;
  const claimed = await claimTab(navigator.locks, tab);
  if (!claimed) {
    controller.data.tab_id = crypto.randomUUID();
    await claimTab(navigator.locks, controller.data.tab_id);
  }
  await controller.start(!claimed);
}
