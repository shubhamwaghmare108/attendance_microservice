const state = {
  token: localStorage.getItem("face_attendance_token") || "",
  stream: null,
  pendingBlob: null,
  mode: "camera"
};

const els = {
  apiBase: document.getElementById("apiBase"),
  apiDot: document.getElementById("apiDot"),
  apiStatus: document.getElementById("apiStatus"),
  sessionStatus: document.getElementById("sessionStatus"),
  tokenPreview: document.getElementById("tokenPreview"),
  viewTitle: document.getElementById("viewTitle"),
  navItems: document.querySelectorAll(".nav-item"),
  views: document.querySelectorAll(".view"),
  loginForm: document.getElementById("loginForm"),
  logoutBtn: document.getElementById("logoutBtn"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  cameraVideo: document.getElementById("cameraVideo"),
  captureCanvas: document.getElementById("captureCanvas"),
  cameraEmpty: document.getElementById("cameraEmpty"),
  startCameraBtn: document.getElementById("startCameraBtn"),
  captureBtn: document.getElementById("captureBtn"),
  recognizeBtn: document.getElementById("recognizeBtn"),
  recognizeFile: document.getElementById("recognizeFile"),
  cameraMode: document.getElementById("cameraMode"),
  fileMode: document.getElementById("fileMode"),
  cameraPane: document.getElementById("cameraPane"),
  filePane: document.getElementById("filePane"),
  recognitionResult: document.getElementById("recognitionResult"),
  enrollForm: document.getElementById("enrollForm"),
  enrollImage: document.getElementById("enrollImage"),
  enrollFileLabel: document.getElementById("enrollFileLabel"),
  enrollmentResult: document.getElementById("enrollmentResult"),
  activityList: document.getElementById("activityList"),
  clearActivityBtn: document.getElementById("clearActivityBtn")
};

function apiBase() {
  return els.apiBase.value.replace(/\/$/, "");
}

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

function setSession() {
  if (state.token) {
    els.sessionStatus.textContent = "Signed in";
    els.tokenPreview.textContent = `${state.token.slice(0, 26)}...`;
  } else {
    els.sessionStatus.textContent = "Signed out";
    els.tokenPreview.textContent = "None";
  }
}

function addActivity(message) {
  const item = document.createElement("div");
  const time = document.createElement("time");
  const text = document.createElement("span");

  item.className = "activity-item";
  time.textContent = new Date().toLocaleTimeString();
  text.textContent = message;

  item.append(time, text);
  els.activityList.prepend(item);
}

function setResult(target, kind, title, meta = []) {
  target.className = `result-band ${kind || ""}`.trim();
  target.innerHTML = `
    <div>
      <p class="eyebrow">Result</p>
      <h3>${escapeHtml(title)}</h3>
      ${meta.length ? `<div class="result-meta">${meta.map(escapeHtml).map((value) => `<span>${value}</span>`).join("")}</div>` : ""}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function readError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.detail) return JSON.stringify(data.detail);
    return JSON.stringify(data);
  } catch {
    return response.statusText || "Request failed";
  }
}

async function checkGateway() {
  if (!state.token) {
    els.apiDot.className = "status-dot";
    els.apiStatus.textContent = "Sign in required";
    return;
  }

  try {
    const response = await fetch(`${apiBase()}/api/protected`, {
      headers: authHeaders()
    });

    if (!response.ok) throw new Error(await readError(response));

    els.apiDot.className = "status-dot online";
    els.apiStatus.textContent = "Gateway online";
  } catch (error) {
    els.apiDot.className = "status-dot offline";
    els.apiStatus.textContent = error.message || "Gateway offline";
  }
}

async function login(event) {
  event.preventDefault();

  try {
    const response = await fetch(`${apiBase()}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: els.username.value,
        password: els.password.value
      })
    });

    if (!response.ok) throw new Error(await readError(response));

    const data = await response.json();
    state.token = data.token;
    localStorage.setItem("face_attendance_token", state.token);
    setSession();
    addActivity(`Signed in as ${els.username.value}`);
    await checkGateway();
  } catch (error) {
    addActivity(`Sign in failed: ${error.message}`);
  }
}

function logout() {
  state.token = "";
  localStorage.removeItem("face_attendance_token");
  setSession();
  addActivity("Signed out");
  checkGateway();
}

function switchView(viewId) {
  els.views.forEach((view) => view.classList.toggle("active", view.id === viewId));
  els.navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === viewId));
  els.viewTitle.textContent = document.querySelector(`[data-view="${viewId}"]`).textContent.trim();
}

function switchSource(mode) {
  state.mode = mode;
  state.pendingBlob = null;
  els.recognizeBtn.disabled = true;
  els.cameraMode.classList.toggle("active", mode === "camera");
  els.fileMode.classList.toggle("active", mode === "file");
  els.cameraPane.classList.toggle("active", mode === "camera");
  els.filePane.classList.toggle("active", mode === "file");
}

async function startCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user" },
      audio: false
    });
    els.cameraVideo.srcObject = state.stream;
    els.cameraEmpty.classList.add("hidden");
    els.captureBtn.disabled = false;
    addActivity("Camera started");
  } catch (error) {
    addActivity(`Camera failed: ${error.message}`);
  }
}

function captureFrame() {
  const video = els.cameraVideo;
  const canvas = els.captureCanvas;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    state.pendingBlob = blob;
    els.recognizeBtn.disabled = !blob;
    addActivity("Frame captured");
  }, "image/jpeg", 0.92);
}

function selectedRecognitionFile() {
  return els.recognizeFile.files[0] || null;
}

async function recognize() {
  if (!state.token) {
    addActivity("Sign in required");
    return;
  }

  const formData = new FormData();
  const source = state.mode === "camera" ? state.pendingBlob : selectedRecognitionFile();

  if (!source) {
    addActivity("No image selected");
    return;
  }

  formData.append("image", source, "recognition.jpg");
  els.recognizeBtn.disabled = true;

  try {
    const response = await fetch(`${apiBase()}/api/recognize`, {
      method: "POST",
      headers: authHeaders(),
      body: formData
    });

    if (!response.ok) throw new Error(await readError(response));

    const data = await response.json();

    if (!data.recognized) {
      setResult(els.recognitionResult, "warning", "Not recognized", [
        data.distance === null ? "No enrolled embeddings" : `Distance ${Number(data.distance).toFixed(3)}`
      ]);
      addActivity("Recognition failed");
      return;
    }

    const attendanceType = data.attendance?.type || "marked";
    setResult(els.recognitionResult, "success", `${data.name} ${attendanceType}`, [
      `Code ${data.employee_code}`,
      `Confidence ${Number(data.confidence).toFixed(3)}`,
      `Distance ${Number(data.distance).toFixed(3)}`
    ]);
    addActivity(`${data.name} ${attendanceType}`);
  } catch (error) {
    setResult(els.recognitionResult, "error", "Recognition error", [error.message]);
    addActivity(`Recognition error: ${error.message}`);
  } finally {
    els.recognizeBtn.disabled = false;
  }
}

async function enroll(event) {
  event.preventDefault();

  if (!state.token) {
    addActivity("Sign in required");
    return;
  }

  const formData = new FormData(els.enrollForm);

  try {
    const response = await fetch(`${apiBase()}/api/enroll`, {
      method: "POST",
      headers: authHeaders(),
      body: formData
    });

    if (!response.ok) throw new Error(await readError(response));

    const data = await response.json();
    setResult(els.enrollmentResult, "success", data.message, [
      `ID ${data.employee_id}`,
      `Code ${data.employee_code}`
    ]);
    addActivity(`Enrolled ${data.employee_code}`);
    els.enrollForm.reset();
    els.enrollFileLabel.textContent = "Choose enrollment image";
  } catch (error) {
    setResult(els.enrollmentResult, "error", "Enrollment error", [error.message]);
    addActivity(`Enrollment error: ${error.message}`);
  }
}

els.navItems.forEach((item) => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});

els.loginForm.addEventListener("submit", login);
els.logoutBtn.addEventListener("click", logout);
els.startCameraBtn.addEventListener("click", startCamera);
els.captureBtn.addEventListener("click", captureFrame);
els.recognizeBtn.addEventListener("click", recognize);
els.enrollForm.addEventListener("submit", enroll);
els.cameraMode.addEventListener("click", () => switchSource("camera"));
els.fileMode.addEventListener("click", () => switchSource("file"));
els.clearActivityBtn.addEventListener("click", () => {
  els.activityList.innerHTML = "";
});
els.recognizeFile.addEventListener("change", () => {
  els.recognizeBtn.disabled = !selectedRecognitionFile();
  if (selectedRecognitionFile()) addActivity(`Selected ${selectedRecognitionFile().name}`);
});
els.enrollImage.addEventListener("change", () => {
  els.enrollFileLabel.textContent = els.enrollImage.files[0]?.name || "Choose enrollment image";
});
els.apiBase.addEventListener("change", checkGateway);

setSession();
checkGateway();
