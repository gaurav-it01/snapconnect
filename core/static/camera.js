const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const capture = document.getElementById("capture");
const container = document.getElementById("camera-container");
const captureBar = document.getElementById("capture-bar");
const previewActions = document.getElementById("preview-actions");
const retakeBtn = document.getElementById("retake");
const openSendToBtn = document.getElementById("open-send-to");
const sendToSheet = document.getElementById("send-to-sheet");
const closeSendToBtn = document.getElementById("close-send-to");
const imageDataInput = document.getElementById("image-data");
const snapThumb = document.getElementById("snap-thumb");
const sendSnapForm = document.getElementById("send-snap-form");

if (video && canvas && capture) {
  let stream = null;
  let cameraReady = false;

  async function startCamera() {
    cameraReady = false;
    capture.disabled = true;
    capture.style.opacity = "0.5";

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });
    } catch (err) {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      } catch (err2) {
        alert("Unable to access camera.");
        console.error(err2);
        return;
      }
    }

    video.srcObject = stream;

    video.onloadedmetadata = async function () {
      try {
        await video.play();
      } catch (err) {
        console.error(err);
      }
      cameraReady = true;
      capture.disabled = false;
      capture.style.opacity = "1";
    };
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      video.srcObject = null;
      stream = null;
    }
    cameraReady = false;
  }

  function goBack() {
    stopCamera();
    history.back();
  }
  window.goBack = goBack;

  // Filter selection handling
  const filterBtns = document.querySelectorAll(".filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation(); // prevent focusing caption text input
      filterBtns.forEach(b => {
  b.classList.remove(
    "bg-[#FFFC00]",
    "text-black",
    "font-semibold",
    "selected-filter"
  );

  b.classList.add(
    "bg-black/40",
    "text-white/70",
    "font-medium"
  );
});
       btn.classList.remove(
  "bg-black/40",
  "text-white/70",
  "font-medium"
);

btn.classList.add(
  "bg-[#FFFC00]",
  "text-black",
  "font-semibold",
  "selected-filter"
);
      
      // Clear old filters
      video.classList.remove("filter-grayscale", "filter-sepia", "filter-warm", "filter-cool");
      
      const filterType = btn.dataset.filter;
      if (filterType !== "none") {
        video.classList.add("filter-" + filterType);
      }
      
      // Direct inline style backup with webkit prefix
      if (filterType === "grayscale") {
        video.style.filter = "grayscale(100%)";
        video.style.webkitFilter = "grayscale(100%)";
      } else if (filterType === "sepia") {
        video.style.filter = "sepia(100%)";
        video.style.webkitFilter = "sepia(100%)";
      } else if (filterType === "warm") {
        const val = "contrast(110%) brightness(105%) sepia(30%)";
        video.style.filter = val;
        video.style.webkitFilter = val;
      } else if (filterType === "cool") {
        const val = "contrast(95%) brightness(100%) hue-rotate(20deg) saturate(110%)";
        video.style.filter = val;
        video.style.webkitFilter = val;
      } else {
        video.style.filter = "none";
        video.style.webkitFilter = "none";
      }
    });
  });

  // Caption text input toggle
  const captionOverlay = document.getElementById("caption-overlay-container");
  const captionInput = document.getElementById("caption-text-input");

  if (container && captionOverlay && captionInput) {
    container.addEventListener("click", () => {
      if (captionOverlay.classList.contains("hidden")) {
        captionOverlay.classList.remove("hidden");
        captionInput.focus();
      } else if (!captionInput.value.trim()) {
        captionOverlay.classList.add("hidden");
      }
    });

    captionInput.addEventListener("blur", () => {
      if (!captionInput.value.trim()) {
        captionOverlay.classList.add("hidden");
      }
    });
  }

  capture.addEventListener("click", () => {
    if (!cameraReady || !video.videoWidth || !video.videoHeight) {
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");

    // Apply active filter to the captured canvas context

    const activeFilterBtn = document.querySelector(".filter-btn.selected-filter");
const activeFilter = activeFilterBtn
  ? activeFilterBtn.dataset.filter
  : "none";
    
    if (activeFilter === "grayscale") {
      ctx.filter = "grayscale(100%)";
    } else if (activeFilter === "sepia") {
      ctx.filter = "sepia(100%)";
    } else if (activeFilter === "warm") {
      ctx.filter = "contrast(110%) brightness(105%) sepia(30%)";
    } else if (activeFilter === "cool") {
      ctx.filter = "contrast(95%) brightness(100%) hue-rotate(20deg) saturate(110%)";
    } else {
      ctx.filter = "none";
    }

    // Draw the current video frame onto the canvas
    ctx.drawImage(video, 0, 0);

    // Overlay caption text if present
    const captionText = captionInput ? captionInput.value.trim() : "";
    if (captionText) {
      const textY = canvas.height / 2;
      const barHeight = canvas.height * 0.08;
      
      // Black translucent background bar
      ctx.filter = "none"; // caption text shouldn't be filtered
      ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
      ctx.fillRect(0, textY - barHeight / 2, canvas.width, barHeight);
      
      // Text drawing
      ctx.fillStyle = "white";
      ctx.font = `bold ${Math.floor(canvas.height * 0.038)}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(captionText, canvas.width / 2, textY);
    }

    const photo = canvas.toDataURL("image/jpeg", 0.85);
    imageDataInput.value = photo;

    stopCamera();
    
    // Hide filters during preview
    const filterBar = document.getElementById("filter-bar");
    if (filterBar) filterBar.style.display = "none";
    if (captionOverlay) captionOverlay.style.display = "none";

    container.innerHTML = `<img src="${photo}" class="w-full h-full object-cover">`;
    if (snapThumb) {
      snapThumb.innerHTML = `<img src="${photo}" class="w-full h-full object-cover">`;
    }

    captureBar.style.display = "none";
    previewActions.style.display = "flex";
  });

  retakeBtn.addEventListener("click", () => {
    location.reload();
  });

  if (openSendToBtn && sendToSheet) {
    openSendToBtn.addEventListener("click", () => {
      sendToSheet.style.display = "flex";
    });
  }

  if (closeSendToBtn && sendToSheet) {
    closeSendToBtn.addEventListener("click", () => {
      sendToSheet.style.display = "none";
    });
  }

  if (sendSnapForm) {
    sendSnapForm.addEventListener("submit", async (e) => {
      e.preventDefault(); // Stop standard sync submit

      if (!imageDataInput.value) {
        alert("Please take a photo first.");
        return;
      }

      const checked = document.querySelectorAll(".friend-check:checked");
      const hasDirectFriend = sendSnapForm.querySelector('input[name="friend_ids"][type="hidden"]');
      const postToSpotlightCheck = document.getElementById("post-to-spotlight-check");

      if (!hasDirectFriend && checked.length === 0 && (!postToSpotlightCheck || !postToSpotlightCheck.checked)) {
        alert("Please select at least one friend or My Spotlight.");
        return;
      }

      // If My Spotlight is checked, upload to spotlight addition endpoint
      if (postToSpotlightCheck && postToSpotlightCheck.checked) {
        const formData = new FormData();
        formData.append("image_data", imageDataInput.value);
        formData.append("title", "Snap Spotlight");
        formData.append("csrfmiddlewaretoken", document.querySelector('[name=csrfmiddlewaretoken]').value);
        try {
          await fetch("/profile/spotlight/add/", {
            method: "POST",
            body: formData
          });
        } catch (err) {
          console.error("Error posting to spotlight:", err);
        }
      }

      // If friends are checked, submit the normal form. Otherwise redirect to spotlight feed page.
      if (hasDirectFriend || checked.length > 0) {
        sendSnapForm.submit();
      } else {
        window.location.href = "/spotlight/";
      }
    });
  }

  window.addEventListener("beforeunload", stopCamera);
  if (document.readyState === "complete" || document.readyState === "interactive") {
    startCamera();
  } else {
    window.addEventListener("load", startCamera);
  }
}
