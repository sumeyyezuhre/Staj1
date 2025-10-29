document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chatForm");
  const questionInput = document.getElementById("question");
  const chatBox = document.getElementById("chatBox");
  const pdfUpload = document.getElementById("pdfUpload");
  const webSearchBtn = document.getElementById("webSearchBtn");

  function appendMessage(message, isUser = true) {
    const bubble = document.createElement("div");
    bubble.className = `p-3 rounded-xl max-w-[75%] whitespace-pre-wrap ${
      isUser
        ? "bg-purple-200 self-end text-right"
        : "bg-yellow-200 self-start text-left"
    }`;
    bubble.textContent = message;
    chatBox.appendChild(bubble);

    const initialMessage = document.querySelector(".chat-placeholder");
    if (initialMessage) initialMessage.remove();

    chatBox.scrollTop = chatBox.scrollHeight;
  }

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    appendMessage(question, true);
    questionInput.value = "";

    appendMessage("🤖 Düşünüyor...", false);

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      const data = await res.json();
      const responseMsg = data.answer || "Cevap alınamadı.";
      const botMessages = Array.from(document.querySelectorAll(".bg-yellow-200"));
      botMessages[botMessages.length - 1].textContent = responseMsg;
    } catch (error) {
      const botMessages = Array.from(document.querySelectorAll(".bg-yellow-200"));
      botMessages[botMessages.length - 1].textContent = "Hata oluştu.";
    }
  });
  pdfUpload.addEventListener("change", async () => {
    const file = pdfUpload.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    appendMessage(`📄 "${file.name}" yükleniyor ve işleniyor...`, false);

    try {
      const res = await fetch("/upload-pdf/", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      const msg = data.status === "ok"
        ? `✅ "${file.name}" başarıyla yüklendi.`
        : `❌ Yükleme başarısız: ${data.message || "Bilinmeyen hata"}`;
      appendMessage(msg, false);
    } catch (err) {
      appendMessage("❌ PDF yüklenemedi.", false);
    }

    pdfUpload.value = "";
  });

  webSearchBtn.addEventListener("click", async () => {
    const question = questionInput.value.trim();
    if (!question) {
      alert("Lütfen önce aramak istediğiniz soruyu yazın.");
      return;
    }

    appendMessage(`🌐 Web'de arama yapılıyor: "${question}"`, true);
    appendMessage("🔎 Aranıyor...", false);

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, search_web_flag: true }),
      });

      const data = await res.json();
      const results = data.answer || "❌ Sonuç bulunamadı.";
      const botMessages = Array.from(document.querySelectorAll(".bg-yellow-200"));
      botMessages[botMessages.length - 1].textContent = results;
    } catch (error) {
      const botMessages = Array.from(document.querySelectorAll(".bg-yellow-200"));
      botMessages[botMessages.length - 1].textContent = "❌ Web araması başarısız.";
    }
  });

  questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.requestSubmit();
    }
  });
});