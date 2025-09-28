// chat.js — gerencia UI, lista de salas, WebSocket, envio/recebimento de mensagens.
(() => {
  const qs = new URLSearchParams(location.search);
  const initialRoom = qs.get('room') || localStorage.getItem('room') || 'general';
  let room = initialRoom;
  let ws = null;
  let user = JSON.parse(localStorage.getItem('user')) || null;

  const roomsEl = document.getElementById('rooms');
  const messagesEl = document.getElementById('messages');
  const roomTitle = document.getElementById('roomTitle');
  const roomInfo = document.getElementById('roomInfo');
  const statusEl = document.getElementById('status');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const createBtn = document.getElementById('create');
  const newRoomName = document.getElementById('newRoomName');
  const backBtn = document.getElementById('backBtn');
  const profileBox = document.getElementById('profileBox');

  function renderProfile(){
    if(!user) return profileBox.innerHTML = `<div>Nenhum perfil</div>`;
    profileBox.innerHTML = `<img src="${user.avatar}" /><div><div style="font-weight:600">${user.name}</div><div class="small">${room}</div></div>`;
  }

  async function loadRooms(){
    roomsEl.innerHTML = 'Carregando...';
    try{
      const res = await fetch('/rooms');
      const j = await res.json();
      const arr = j.rooms || [];
      roomsEl.innerHTML = '';
      arr.forEach(r=>{
        const div = document.createElement('div');
        div.className = 'room';
        div.innerHTML = `<div><div class="name">${r.name}</div><div class="meta">${r.is_private ? 'Privada' : 'Pública'}</div></div>`;
        div.onclick = () => joinRoom(r.name);
        roomsEl.appendChild(div);
      });
    }catch(e){
      roomsEl.innerHTML = 'Erro ao carregar salas';
    }
  }

  function appendMessage(item){
    const d = document.createElement('div');
    d.className = 'msg';
    d.innerHTML = `<img src="${item.avatar || ''}" onerror="this.style.display='none'"/>
      <div>
        <div class="metaRow">[${new Date(item.created_at).toLocaleTimeString()}] <strong>${item.username}</strong></div>
        <div class="bubble">${escapeHtml(item.content)}</div>
      </div>`;
    messagesEl.appendChild(d);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(unsafe) {
    return unsafe.replace(/[&<"'>]/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  }

  function setStatus(s){
    statusEl.innerText = 'status: ' + s;
  }

  function connectWS() {
    if(!room) return;
    if(!user) return alert('Escolha um personagem no /');
    if(ws) ws.close();
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/${encodeURIComponent(room)}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('conectado');
      roomTitle.innerText = `Sala: ${room}`;
      roomInfo.innerText = `Conectado como ${user.name}`;
    };

    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if(data.type === 'history'){
        messagesEl.innerHTML = '';
        (data.items || []).forEach(it => appendMessage(normalize(it)));
      }else if(data.type === 'message'){
        appendMessage(normalize(data.item));
      }
    };

    ws.onclose = () => setStatus('desconectado');
    ws.onerror = () => setStatus('erro');
  }

  function normalize(item){
    // older messages may have created_at as ISO or Date string
    if(item.created_at && typeof item.created_at === 'string'){
      item.created_at = item.created_at;
    }else if(item.created_at && item.created_at.$date){
      item.created_at = item.created_at.$date;
    }else if(!item.created_at){
      item.created_at = new Date().toISOString();
    }
    return item;
  }

  sendBtn.onclick = () => {
    const text = inputEl.value.trim();
    if(!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    const payload = { username: user.name, content: text, avatar: user.avatar };
    ws.send(JSON.stringify(payload));
    inputEl.value = '';
  };

  function joinRoom(r){
    localStorage.setItem('room', r);
    room = r;
    messagesEl.innerHTML = '';
    connectWS();
  }

  createBtn.onclick = async () => {
    const name = newRoomName.value.trim();
    if(!name) return alert('Informe nome da sala');
    await fetch('/rooms', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name, is_private:false }) });
    newRoomName.value = '';
    await loadRooms();
  };

  backBtn.onclick = () => { window.location.href = '/'; };

  // inicialização
  (function init(){
    if(!user) {
      alert('Perfil não encontrado — você será redirecionado para a seleção de personagem');
      return window.location.href = '/';
    }
    renderProfile();
    loadRooms().then(()=> {
      joinRoom(room);
    });
  })();

})();
