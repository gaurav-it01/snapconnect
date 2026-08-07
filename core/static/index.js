const snapFile = document.getElementById("snap-file");
const fileBtn = document.getElementById("file-button");
const previewDock = document.getElementById("preview-dock");
const previewContainer = document.getElementById("preview-container");
const caption = document.getElementById("caption");
const clearPreview = document.getElementById("clear-preview");

if (fileBtn && snapFile) {
  fileBtn.addEventListener("click", () => snapFile.click());

  snapFile.addEventListener("change", () => {
    const file = snapFile.files[0];
    if (!file || !previewDock || !previewContainer || !caption) return;

    previewContainer.innerHTML = `<img src="${URL.createObjectURL(file)}" class="object-cover h-full w-full">`;
    caption.innerText = file.name;
    previewDock.classList.remove("hidden");
  });
}

if (clearPreview && snapFile && previewDock && previewContainer) {
  clearPreview.addEventListener("click", () => {
    snapFile.value = "";
    previewContainer.innerHTML = "";
    previewDock.classList.add("hidden");
  });
}
