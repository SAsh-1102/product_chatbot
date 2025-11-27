// js/chat.js
const chatBox = document.getElementById("chatBox");
const queryInput = document.getElementById("query");

function addMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `msg ${sender}`;
    msg.innerHTML = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addLoader() {
    const loader = document.createElement("div");
    loader.className = "msg bot loader";
    loader.innerHTML = "<span></span><span></span><span></span>";
    chatBox.appendChild(loader);
    chatBox.scrollTop = chatBox.scrollHeight;
    return loader;
}

function sendQuery() {
    const query = queryInput.value.trim();
    if (!query) return;

    addMessage(query, "user");
    queryInput.value = "";

    const loader = addLoader();

    fetch("/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ query })
    })
    .then(res => res.json())
    .then(data => {
        loader.remove();
        addMessage(data.answer, "bot");
        speak(data.answer); // call TTS
    })
    .catch(err => {
        loader.remove();
        addMessage("Oops! Something went wrong. Please try again.", "bot");
        speak("Oops! Something went wrong. Please try again.");
    });
}

queryInput.addEventListener("keypress", e => {
    if (e.key === "Enter") sendQuery();
});
let isListening = false;
let recognitionObj = null;

document.getElementById("micBtn").addEventListener("click", () => {
    if (!isListening) {
        startMic();
    } else {
        stopMic();
    }
});

function startMic() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Your browser doesn't support voice input.");
        return;
    }

    recognitionObj = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognitionObj.lang = 'en-US';
    recognitionObj.interimResults = false;
    recognitionObj.maxAlternatives = 1;

    recognitionObj.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        sendQuery();
    };

    recognitionObj.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
    };

    recognitionObj.onend = () => {
        stopMic();
    };

    recognitionObj.start();

    isListening = true;
    document.getElementById("micBtn").classList.add("listening");
}

function stopMic() {
    if (recognitionObj) recognitionObj.stop();
    isListening = false;
    document.getElementById("micBtn").classList.remove("listening");
}

