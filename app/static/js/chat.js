// chat.js — gerencia UI, lista de salas, WebSocket, envio/recebimento de mensagens.
(() => {
  const qs = new URLSearchParams(location.search);
  const initialRoom = qs.get('room') || localStorage.getItem('room') || 'general';
  let room = initialRoom;
  let ws = null;
  let heartbeatInterval = null;
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

  // ---------------------------
  // Perfil do usuário
  // ---------------------------
  function renderProfile(){
    if(!user) return profileBox.innerHTML = `<div>Nenhum perfil</div>`;
    profileBox.innerHTML = `<img src="${user.avatar}" />
      <div>
        <div style="font-weight:600">${user.name}</div>
        <div class="small">${room}</div>
      </div>`;
  }

  // ---------------------------
  // Lista de salas
  // ---------------------------
  async function loadRooms(){
    roomsEl.innerHTML = 'Carregando...';
    try {
      const res = await fetch('/rooms');
      const j = await res.json();
      const arr = j.rooms || [];
      roomsEl.innerHTML = '';
      arr.forEach(r => {
        const div = document.createElement('div');
        div.className = 'room';
        div.innerHTML = `<div>
          <div class="name">${r.name}</div>
          <div class="meta">${r.is_private ? 'Privada' : 'Pública'}</div>
        </div>`;
        div.onclick = () => joinRoom(r.name);
        roomsEl.appendChild(div);
      });
    } catch(e) {
      roomsEl.innerHTML = 'Erro ao carregar salas';
    }
  }

  // ---------------------------
  // Exibe mensagens no chat
  // ---------------------------
  function appendMessage(item){
    // Evita duplicação: verifica se a mensagem já existe
    if([...messagesEl.children].some(c => c.dataset.id === item.id)) return;

    const d = document.createElement('div');
    d.className = 'msg';
    d.dataset.id = item.id; // marca ID da mensagem
    d.innerHTML = `<img src="${item.avatar || ''}" onerror="this.style.display='none'"/>
      <div>
        <div class="metaRow">[${new Date(item.created_at).toLocaleTimeString()}] <strong>${item.username}</strong></div>
        <div class="bubble">${escapeHtml(item.content)}</div>
      </div>`;
    messagesEl.appendChild(d);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(unsafe) {
    return unsafe.replace(/[&<"'>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  }

  function setStatus(s){
    statusEl.innerText = 'status: ' + s;
  }

  // ---------------------------
  // WebSocket
  // ---------------------------
  function connectWS() {
    if(!room) return;
    if(!user) return alert('Escolha um personagem no /');

    // Fecha WS antigo e limpa heartbeat
    if(ws) { ws.close(); ws = null; }
    if(heartbeatInterval) { clearInterval(heartbeatInterval); heartbeatInterval = null; }

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/${encodeURIComponent(room)}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('conectado');
      roomTitle.innerText = `Sala: ${room}`;
      roomInfo.innerText = `Conectado como ${user.name}`;

      heartbeatInterval = setInterval(() => {
        if(ws && ws.readyState === WebSocket.OPEN){
          ws.send(JSON.stringify({ type: "heartbeat", username: user.name }));
        }
      }, 30000);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if(data.type === 'history'){
          messagesEl.innerHTML = '';
          (data.items || []).forEach(it => appendMessage(normalize(it)));
        } else if(data.type === 'message'){
          appendMessage(normalize(data.item));
        }
      } catch(e) { console.error("Erro ao processar WS:", e); }
    };

    ws.onclose = () => {
      setStatus('desconectado');
      if(heartbeatInterval) { clearInterval(heartbeatInterval); heartbeatInterval = null; }
    };
    ws.onerror = () => setStatus('erro');
  }

  // Normaliza datas
  function normalize(item){
    if(item.created_at && typeof item.created_at === 'string'){
      item.created_at = item.created_at;
    } else if(item.created_at && item.created_at.$date){
      item.created_at = item.created_at.$date;
    } else if(!item.created_at){
      item.created_at = new Date().toISOString();
    }
    return item;
  }

  // ---------------------------
  // Envia mensagem
  // ---------------------------
  sendBtn.onclick = () => {
    const text = inputEl.value.trim();
    if(!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    const payload = { username: user.name, content: text, avatar: user.avatar };
    ws.send(JSON.stringify(payload));
    inputEl.value = '';
  };

  // ---------------------------
  // Troca de salas
  // ---------------------------
  function joinRoom(r){
    localStorage.setItem('room', r);
    room = r;
    messagesEl.innerHTML = '';
    connectWS();
  }

  // ---------------------------
  // Criação de sala
  // ---------------------------
  createBtn.onclick = async () => {
    const name = newRoomName.value.trim();
    if(!name) return alert('Informe nome da sala');

    const is_private = document.getElementById('newRoomPrivate').checked;
    const password = document.getElementById('newRoomPass').value;

    await fetch('/rooms', { 
      method: 'POST', 
      headers: {'Content-Type':'application/json'}, 
      body: JSON.stringify({ name, is_private, password })
    });

    newRoomName.value = '';
    document.getElementById('newRoomPass').value = '';
    document.getElementById('newRoomPrivate').checked = false;

    await loadRooms();
  };

  backBtn.onclick = () => { window.location.href = '/index.html'; };

  // ---------------------------
  // Inicialização
  // ---------------------------
  (function init(){
    if(!user) {
      alert('Perfil não encontrado — você será redirecionado para a seleção de personagem');
      return window.location.href = '/index.html';
    }
    renderProfile();
    loadRooms().then(()=> joinRoom(room));
  })();

})();
