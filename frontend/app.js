let sessionId = null;

const uploadBtn = document.getElementById("uploadBtn");
const sendBtn = document.getElementById("sendBtn");
const resumeText = document.getElementById("resumeText");
const resumeFile = document.getElementById("resumeFile");
const resumeData = document.getElementById("resumeData");
const chatInput = document.getElementById("chatInput");
const chatBox = document.getElementById("chatBox");

async function initSession() {
  const res = await fetch("/api/session", { method: "POST" });
  const data = await res.json();
  sessionId = data.session_id;
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

uploadBtn.addEventListener("click", async () => {
  if (!sessionId) await initSession();

  const form = new FormData();
  form.append("session_id", sessionId);
  if (resumeText.value.trim()) {
    form.append("resume_text", resumeText.value.trim());
  }
  if (resumeFile.files[0]) {
    form.append("resume_file", resumeFile.files[0]);
  }

  const res = await fetch("/api/upload-resume", {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    resumeData.textContent = JSON.stringify(data, null, 2);
    return;
  }

  resumeData.textContent = JSON.stringify(data.extracted_data, null, 2);
  addMessage("assistant", "Resume processed. Ask your hiring questions.");
});

sendBtn.addEventListener("click", async () => {
  const message = chatInput.value.trim();
  if (!message) return;
  if (!sessionId) await initSession();

  addMessage("user", message);
  chatInput.value = "";

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    addMessage("assistant", JSON.stringify(data));
    return;
  }

  addMessage(
    "assistant",
    `${data.answer}\n\nconfidence: ${data.confidence}\nsource: ${data.source}\nmissing_data: ${JSON.stringify(
      data.missing_data
    )}`
  );
});

initSession().catch(() => {
  addMessage("assistant", "Unable to initialize session.");
});
