import test from 'node:test';
import assert from 'node:assert/strict';
import {ChatController} from '../../src/parking/web/app.mjs';

function setup(request) {
  const values = new Map(); let sequence = 0;
  return new ChatController({storage:{getItem:key => values.get(key),setItem:(key,value) => values.set(key,value)},
    request, id:() => `identity_${++sequence}`, render:() => {}, delay:async () => {}});
}

test('pending preserves editable draft and rejects second send', async () => {
  let finish; let posts = 0;
  const chat = setup(async (url, options) => {
    if (url === '/api/threads') return {thread_id:'thread'};
    posts++;
    return new Promise(resolve => {finish = () => resolve({thread_id:'thread',request_id:chat.data.pending.request_id,status:'completed',reply:{final_reply:'Cited reply'}});});
  });
  await chat.newChat(); chat.edit('First question');
  const pending = chat.send();
  chat.edit('Next draft'); await chat.send();
  assert.equal(posts, 1); assert.equal(chat.state, 'pending');
  finish(); await pending;
  assert.equal(chat.draft, 'Next draft'); assert.equal(chat.messages.length, 2);
});

test('lost acknowledgement uses GET without another POST', async () => {
  let posts = 0;
  const chat = setup(async url => {
    if (url === '/api/threads') return {thread_id:'thread'};
    if (url === '/api/chat') {posts++; throw Error('lost acknowledgement');}
    return {thread_id:'thread',request_id:chat.data.pending.request_id,status:'completed',reply:{final_reply:'Recovered'}};
  });
  await chat.newChat(); chat.edit('Question'); await chat.send();
  assert.equal(posts, 1); assert.equal(chat.messages.at(-1).text, 'Recovered');
});

test('new chat ignores a stale previous reply', async () => {
  let finish; let threads = 0;
  const chat = setup(async url => {
    if (url === '/api/threads') return {thread_id:`thread${++threads}`};
    return new Promise(resolve => {finish = () => resolve({thread_id:'thread1',request_id:'old',status:'completed',reply:{final_reply:'Old'}});});
  });
  await chat.newChat(); chat.edit('Old question'); const old = chat.send();
  await chat.newChat(); finish(); await old;
  assert.equal(chat.data.thread_id, 'thread2'); assert.deepEqual(chat.messages, []);
});
