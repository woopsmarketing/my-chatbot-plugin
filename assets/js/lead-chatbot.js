(function(){
  // ──────────────────────────────
  // 1. localStorage 기반 세션 및 제출 잠금 관리 함수
  // ──────────────────────────────

  /**
   * getOrCreateSessionId: localStorage에서 "chat_session_id"를 읽어오고,
   * 값이 없으면 새로운 session_id를 생성하여 저장합니다.
   * @returns {string} - 고유한 session_id
   */
  function getOrCreateSessionId() {
    let sessionId = localStorage.getItem("chat_session_id");
    if (!sessionId) {
      sessionId = `sess-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      localStorage.setItem("chat_session_id", sessionId);
    }
    return sessionId;
  }

  /**
   * isFormSubmissionLocked: localStorage에 저장된 양식 제출 타임스탬프를 확인하여,
   * 제출 후 30분 이내면 true를 반환합니다.
   * @returns {boolean}
   */
  function isFormSubmissionLocked() {
    const ts = localStorage.getItem("formSubmittedTimestamp");
    if (ts) {
      const THIRTY_MIN_MS = 30 * 60 * 1000; // 30분
      if (Date.now() - parseInt(ts) < THIRTY_MIN_MS) {
        return true;
      } else {
        localStorage.removeItem("formSubmittedTimestamp");
        return false;
      }
    }
    return false;
  }

  /**
   * getChatCollapsedState: "chatCollapsed" 값을 가져옴 (기본값 "false")
   */
  function getChatCollapsedState() {
    return localStorage.getItem("chatCollapsed") || "false"; 
    // "true" = 접힘, "false" = 펼침
  }

  /**
   * setChatCollapsedState: "chatCollapsed" 값을 설정.
   */
  function setChatCollapsedState(isCollapsed) {
    // isCollapsed는 boolean. 저장 시 문자열 "true"/"false"로 변환
    localStorage.setItem("chatCollapsed", isCollapsed ? "true" : "false");
  }

  // ──────────────────────────────
  // 2. 대화 내역 관리 함수 (localStorage - JSON 방식)
  // ──────────────────────────────

  /**
   * getCurrentTime: 현재 시간을 밀리초 단위로 반환합니다.
   * @returns {number}
   */
  function getCurrentTime() {
    return Date.now();
  }

  /**
   * saveMessageToLocalStorage: 메시지 객체를 localStorage에 저장합니다.
   * 메시지 객체 형식: { time: number, sender: string, content: string }
   * @param {Object} messageObj
   */
  function saveMessageToLocalStorage(messageObj) {
    let messages = JSON.parse(localStorage.getItem("chatMessages") || "[]");
    messages.push(messageObj);
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }

  /**
   * cleanupOldMessages: 1시간 이전의 메시지를 localStorage에서 제거합니다.
   */
  function cleanupOldMessages() {
    const oneHourAgo = getCurrentTime() - 3600000; // 1시간 전
    let messages = JSON.parse(localStorage.getItem("chatMessages") || "[]");
    messages = messages.filter(msg => msg.time >= oneHourAgo);
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }

  /**
   * renderConversation: localStorage에 저장된 최근(1시간 이내) 대화 메시지를 DOM에 렌더링합니다.
   * @param {HTMLElement} container
   */
  function renderConversation(container) {
    // 먼저 showdown을 로드합니다.
    loadShowdown(function() {
      // 오래된 메시지 정리
      cleanupOldMessages();
      // localStorage에서 메시지 목록(JSON 문자열)을 읽어서 파싱
      const messages = JSON.parse(localStorage.getItem("chatMessages") || "[]");
      container.innerHTML = "";
      // showdown converter 생성 (옵션은 필요에 따라 조정)
      const converter = new showdown.Converter({ simpleLineBreaks: true, tables: true });
      
      messages.forEach(msg => {
        let content = msg.content;
        // 상담원 메시지는 마크다운을 HTML로 변환
        if (msg.sender === "상담원") {
          content = converter.makeHtml(content);
        }
        const p = document.createElement("p");
        p.innerHTML = `<strong>${msg.sender}:</strong> ${content}`;
        if (msg.sender === "사용자") {
          p.classList.add("user-message");
        } else {
          p.classList.add("agent-message");
        }
        container.appendChild(p);
      });
      smoothScrollToBottom(container, 1000);
    });
  }

  /**
   * addMessageToLocal: 한 메시지를 localStorage에 추가 (time, sender, content)
   */
  function addMessageToLocal(sender, content) {
    const msg = { time: Date.now(), sender, content };
    let msgs = JSON.parse(localStorage.getItem("chatMessages") || "[]");
    msgs.push(msg);
    localStorage.setItem("chatMessages", JSON.stringify(msgs));
  }

  /**
   * appendMsgAndSave: 메시지를 DOM에 추가하고 localStorage에 저장합니다.
   * @param {string} sender
   * @param {string} message
   */
  function appendMsgAndSave(sender, message) {
    appendMsg(sender, message);
    const msgObj = {
      time: getCurrentTime(),
      sender: sender,
      content: message
    };
    saveMessageToLocalStorage(msgObj);
  }
  // ──────────────────────────────
  // 3. 부드러운 스크롤 함수 (1초 동안 스크롤)
  // ──────────────────────────────
  function smoothScrollToBottom(container, duration) {
    const start = container.scrollTop;
    const end = container.scrollHeight - container.clientHeight;
    const change = end - start;
    const startTime = performance.now();
    
    function animateScroll(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      container.scrollTop = start + change * progress;
      if (progress < 1) {
        requestAnimationFrame(animateScroll);
      }
    }
    requestAnimationFrame(animateScroll);
  }

  // ──────────────────────────────
  // 3. 동적 Showdown 로드
  // ──────────────────────────────

  function loadShowdown(callback) {
    if (typeof showdown !== "undefined") {
      callback();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/showdown/dist/showdown.min.js";
    script.onload = callback;
    script.onerror = () => { console.error("Showdown load fail."); callback(); };
    document.head.appendChild(script);
  }

  // ──────────────────────────────
  // 4. DOM 요소, API 엔드포인트 및 기본 변수 초기화
  // ──────────────────────────────
  const sessionId = getOrCreateSessionId();
  console.log("Session ID (from localStorage):", sessionId);

  const API_SUBMIT = "https://localhost:8000/lead/submit";
  const API_CHAT = "https://localhost:8000/chat";

  const form = document.getElementById("lead-form");
  const successMsg = document.getElementById("lead-success");
  const chatBox = document.getElementById("chatbox");
  const chatMsgs = document.getElementById("chat-messages");
  const chatInput = document.getElementById("chat-input");
  const chatForm = document.getElementById("chat-input-area");
  const wrapper = document.getElementById("lead-chatbot-wrapper");

  if (!form) return;

  // 페이지 로드시 대화 내역 복원 (1시간 이내)
  document.addEventListener("DOMContentLoaded", function() {
    renderConversation(chatMsgs);
    // 오래된 메시지 정리 (5분 간격)
    setInterval(cleanupOldLocalMessages, 5*60*1000);
  });

  // ──────────────────────────────
  // 5. "채팅창 펼치기" 버튼 (모바일용) 생성 및 이벤트 등록
  // ──────────────────────────────
  const expandChatBtn = document.createElement("button");
  expandChatBtn.id = "expand-chat-btn";
  expandChatBtn.innerText = "채팅창 펼치기";
  expandChatBtn.style.display = "none";
  expandChatBtn.style.position = "fixed";
  expandChatBtn.style.bottom = "20px";
  expandChatBtn.style.right = "20px";
  expandChatBtn.style.zIndex = "9999";
  document.body.appendChild(expandChatBtn);
  

  expandChatBtn.addEventListener("click", function() {
    setChatCollapsedState(false); // 펼침
    if (window.innerWidth <= 768) {
      wrapper.classList.add("full-screen-chat");
      document.body.style.overflow = "hidden";
    }
    chatBox.style.display = "flex";
    expandChatBtn.style.display = "none";
    smoothScrollToBottom(chatMsgs, 1000);
  });

  // ──────────────────────────────
  // 6. 양식 제출 이벤트 처리 (폼 제출 후 2초 지연)
  // ──────────────────────────────
  form.addEventListener("submit", function(e) {
    e.preventDefault();
    const data = {};
    new FormData(form).forEach(function(value, key) {
      data[key] = value;
    });

    fetch(API_SUBMIT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId
      },
      credentials: "include",
      body: JSON.stringify(data)
    }).then(response => response.json())
      .then(function(res) {
        if (res.status !== "ok") {
          alert(res.message || "메일 발송 실패");
          return;
        }
        localStorage.setItem("formSubmittedTimestamp", Date.now().toString());
        form.style.display = "none";
        successMsg.innerHTML = "양식 제출에 성공했습니다! 챗봇 준비 중...";
        successMsg.style.display = "block";

        setTimeout(() => {
          successMsg.innerHTML = 
            "샘플링크 구축에 최소 1분~5분 소요됩니다.<br>" +
            "그동안 구글상위노출 전문 상담가와 24시간 대화를 나누며 도움이 되는 정보를 얻으실 수 있습니다." +
            "<br><br><button id='start-chat-btn' class='action-btn'>상담 및 대화하기</button>";
          const startChatBtn = document.getElementById("start-chat-btn");
          startChatBtn.addEventListener("click", function() {
            successMsg.style.display = "none";
            setChatCollapsedState(false); // 펼침
            if (window.innerWidth <= 768) {
              wrapper.classList.add("full-screen-chat");
              document.body.style.overflow = "hidden";
            }
            chatBox.style.display = "flex";
            loadShowdown(() => {
              if (!headerCreated) {
                createChatHeader();
                headerCreated = true;
              }
              renderConversation(chatMsgs); // 대화 내역 다시 렌더링 (마크다운 변환 적용)
              chatInput.focus();
              smoothScrollToBottom(chatMsgs, 1000);
            });
          });
        }, 2000);
      })
      .catch(function(err) {
        alert("메일 발송 에러: " + err.message);
      });
  });

  // 폼 제출 후 30분 잠금 시, 페이지 로드시 바로 챗봇 UI 표시
  if (isFormSubmissionLocked()) {
    form.style.display="none";
    successMsg.style.display="none";
    // chatCollapsed 여부 확인
    const collapsedState = getChatCollapsedState(); // "true"/"false"
    if(collapsedState==="true"){
      // 접힘
      chatBox.style.display="none";
      expandChatBtn.style.display="block";
      wrapper.classList.remove("full-screen-chat");
      document.body.style.overflow="auto";
    } else {
      // 펼침
      chatBox.style.display="flex";
      expandChatBtn.style.display="none";
      if(window.innerWidth<=768){
        wrapper.classList.add("full-screen-chat");
        document.body.style.overflow="hidden";
      }
    }
    loadShowdown(() => {
      if (!headerCreated) {
        createChatHeader();
        headerCreated = true;
      }
      chatInput.focus();
      smoothScrollToBottom(chatMsgs, 1000);
    });
  }

  // ──────────────────────────────
  // 7. 채팅 이벤트 처리
  // ──────────────────────────────
  chatForm.addEventListener("submit", function(e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    appendMsgAndSave("사용자", text);
    saveConversationToLocalStorage();

    const spinnerBubble = showTypingIndicator(chatMsgs);

    fetch(API_CHAT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId
      },
      credentials: "include",
      body: JSON.stringify({ question: text })
    })
      .then(response => response.json())
      .then(data => {
        hideTypingIndicator(spinnerBubble, data.answer);
        // localStorage에는 답변을 추가만 해주자:
        addMessageToLocal("상담원", data.answer);
        smoothScrollToBottom(chatMsgs, 1000);
      })
      .catch(function(err) {
        console.error("Error:", err);
        hideTypingIndicator(spinnerBubble, "오류가 발생했습니다.");
        addMessageToLocal("상담원","오류가 발생했습니다.");
        smoothScrollToBottom(chatMsgs, 1000);
      });
    chatInput.value = "";
  });

  // ──────────────────────────────
  // 8. 대화 내역 복원 및 저장 (저장된 대화 불러오기)
  // ──────────────────────────────
  function loadConversationFromLocalStorage() {
    const saved = localStorage.getItem("chat_conversation");
    if (saved) {
      chatMsgs.innerHTML = saved;
      chatMsgs.scrollTop = chatMsgs.scrollHeight;
    }
  }

  function saveConversationToLocalStorage() {
    localStorage.setItem("chat_conversation", chatMsgs.innerHTML);
  }

  // ──────────────────────────────
  // 9. 챗봇 헤더 생성 함수
  // ──────────────────────────────
  let headerCreated = false;

  function createChatHeader() {
    if (chatBox.querySelector(".chatbox-header")) {
      return;
    }
    const infoDiv = document.createElement("div");
    infoDiv.className = "chatbox-header";
    infoDiv.innerHTML = `
      <span>SEO에 관한 궁금한 모든 것을 물어보세요!</span>
      <button id="btn-ai-chatbot" class="header-btn">AI 챗봇 제작문의</button>
      <button id="close-chat-btn" class="header-btn close-chat-btn">챗봇 접기</button>
    `;
    chatBox.insertBefore(infoDiv, chatBox.firstChild);

    const aiBtn = infoDiv.querySelector("#btn-ai-chatbot");
    aiBtn.addEventListener("click", () => {
      window.open("https://t.me/goat82", "_blank");
    });

    const closeBtn = infoDiv.querySelector("#close-chat-btn");
    closeBtn.addEventListener("click", function() {
      setChatCollapsedState(true); // 접힘
      wrapper.classList.remove("full-screen-chat");
      document.body.style.overflow = "auto";
      chatBox.style.display = "none";
      expandChatBtn.style.display = "block";
    });
  }

  // ──────────────────────────────
  // 10. 메시지 추가 함수
  // ──────────────────────────────
  function appendMsg(sender, message) {
    const p = document.createElement("p");
    p.innerHTML = `<strong>${sender}:</strong> ${message}`;
    if (sender === "사용자") {
      p.classList.add("user-message");
    } else {
      p.classList.add("agent-message");
    }
    chatMsgs.appendChild(p);
    smoothScrollToBottom(chatMsgs, 1000);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
  }

  function appendMsgAndSave(sender, message) {
    appendMsg(sender, message);
    const msgObj = {
      time: getCurrentTime(),
      sender: sender,
      content: message
    };
    let messages = JSON.parse(localStorage.getItem("chatMessages") || "[]");
    messages.push(msgObj);
    localStorage.setItem("chatMessages", JSON.stringify(messages));
  }

  // ──────────────────────────────
  // 11. Typing Indicator 함수
  // ──────────────────────────────
  function showTypingIndicator(parentElement) {
    const bubble = document.createElement("div");
    bubble.classList.add("agent-message");
    bubble.innerHTML = `<div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>`;
    parentElement.appendChild(bubble);
    smoothScrollToBottom(chatMsgs, 1000);
    return bubble;
  }

  function hideTypingIndicator(indicatorBubble, finalText) {
    if (typeof showdown !== "undefined") {
      const converter = new showdown.Converter({ simpleLineBreaks: true, tables: true });
      const html = converter.makeHtml(finalText);
      indicatorBubble.innerHTML = `<strong>상담원:</strong> ${html}`;
    } else {
      indicatorBubble.innerHTML = `<strong>상담원:</strong> ${finalText}`;
    }
  }

  // ──────────────────────────────
  // [추가] 1시간 지난 메시지는 localStorage에서 주기적으로 정리
  setInterval(function() {
    cleanupOldMessages();
  }, 5 * 60 * 1000); // 5분마다 실행

})();
