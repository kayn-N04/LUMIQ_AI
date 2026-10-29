const shirtInput = document.querySelector("#shirt-file");
const patternInput = document.querySelector("#pattern-file");
const shirtPreview = document.querySelector("#shirt-preview");
const patternPreview = document.querySelector("#pattern-preview");
const shirtName = document.querySelector("#shirt-name");
const patternName = document.querySelector("#pattern-name");
const colorOptions = document.querySelector("#color-options");
const generateButton = document.querySelector("#generate-button");
const buttonLabel = document.querySelector("#button-label");
const message = document.querySelector("#message");
const resultImage = document.querySelector("#result-image");
const emptyState = document.querySelector("#empty-state");
const loadingState = document.querySelector("#loading-state");
const previewTitle = document.querySelector("#preview-title");
const mockupPreview = document.querySelector("#mockup-preview");
const mockupStage = document.querySelector("#mockup-stage");
const mockupShirt = document.querySelector("#mockup-shirt");
const mockupPattern = document.querySelector("#mockup-pattern");
const resultCanvas = document.querySelector(".result-canvas");
const downloadLink = document.querySelector("#download-link");
const selectedColorLabel = document.querySelector("#selected-color");
const centerX = document.querySelector("#center-x");
const centerY = document.querySelector("#center-y");
const printWidth = document.querySelector("#print-width");
const rotation = document.querySelector("#rotation");
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
let selectedColor = "Giữ nguyên";
const previewUrls = { shirt: null, pattern: null };

function showMessage(text) {
  message.textContent = text;
}

function resetResult() {
  resultImage.hidden = true;
  downloadLink.hidden = true;
  resultImage.removeAttribute("src");
  updatePlacementPreview();
}

function updatePlacementPreview() {
  previewTitle.textContent = resultImage.hidden ? "Xem trước" : "Kết quả";
  const shirtUrl = previewUrls.shirt;
  if (!shirtUrl) {
    mockupPreview.hidden = true;
    mockupPattern.hidden = true;
    emptyState.hidden = false;
    return;
  }

  mockupPreview.hidden = false;
  emptyState.hidden = true;
  if (mockupShirt.getAttribute("src") !== shirtUrl) {
    mockupShirt.onload = updatePlacementPreview;
    mockupShirt.src = shirtUrl;
  }

  const patternUrl = previewUrls.pattern;
  if (!patternUrl) {
    mockupPattern.hidden = true;
    return;
  }
  if (mockupPattern.getAttribute("src") !== patternUrl) {
    mockupPattern.onload = updatePlacementPreview;
    mockupPattern.src = patternUrl;
  }
  if (!mockupShirt.naturalWidth || !mockupPattern.naturalWidth) return;

  const shirtWidth = mockupShirt.naturalWidth;
  const shirtHeight = mockupShirt.naturalHeight;
  const patternWidth = mockupPattern.naturalWidth;
  const patternHeight = mockupPattern.naturalHeight;
  const degrees = Math.abs(Number(rotation.value));
  let rotatedWidth = patternWidth;
  let rotatedHeight = patternHeight;
  if (degrees === 90) {
    rotatedWidth = patternHeight;
    rotatedHeight = patternWidth;
  } else if (degrees !== 0 && degrees !== 180) {
    const angle = degrees * Math.PI / 180;
    const cosine = Math.abs(Math.cos(angle)) < 1e-12 ? 0 : Math.abs(Math.cos(angle));
    const sine = Math.abs(Math.sin(angle)) < 1e-12 ? 0 : Math.abs(Math.sin(angle));
    rotatedWidth = 2 * Math.ceil(
      cosine * patternWidth / 2 + sine * patternHeight / 2,
    );
    rotatedHeight = 2 * Math.ceil(
      sine * patternWidth / 2 + cosine * patternHeight / 2,
    );
  }
  const scale = Math.min(
    shirtWidth * Number(printWidth.value) / 100 / rotatedWidth,
    shirtHeight / rotatedHeight,
  );
  const placedWidth = Math.max(1, Math.floor(rotatedWidth * scale + .5));
  const placedHeight = Math.max(1, Math.floor(rotatedHeight * scale + .5));
  const left = Math.max(0, Math.min(
    shirtWidth - placedWidth,
    Math.floor(shirtWidth * Number(centerX.value) / 100 - placedWidth / 2 + .5),
  ));
  const top = Math.max(0, Math.min(
    shirtHeight - placedHeight,
    Math.floor(shirtHeight * Number(centerY.value) / 100 - placedHeight / 2 + .5),
  ));

  mockupStage.style.setProperty("--shirt-ratio", `${shirtWidth} / ${shirtHeight}`);
  mockupStage.style.width = `${Math.max(1, Math.min(resultCanvas.clientWidth - 34, 300 * shirtWidth / shirtHeight))}px`;
  const imageWidth = patternWidth * scale / shirtWidth * 100;
  const imageHeight = patternHeight * scale / shirtHeight * 100;
  mockupPattern.style.left = `${(left + placedWidth / 2) / shirtWidth * 100 - imageWidth / 2}%`;
  mockupPattern.style.top = `${(top + placedHeight / 2) / shirtHeight * 100 - imageHeight / 2}%`;
  mockupPattern.style.width = `${imageWidth}%`;
  mockupPattern.style.height = `${imageHeight}%`;
  mockupPattern.style.transform = `rotate(${rotation.value}deg)`;
  mockupPattern.hidden = false;
}

function setPreview(input, preview, nameLabel, currentUrl) {
  const file = input.files[0];
  if (!file) return currentUrl;

  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
    input.value = "";
    showMessage("Vui lòng chọn ảnh PNG, JPG hoặc WebP.");
    return currentUrl;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    input.value = "";
    showMessage("Mỗi ảnh chỉ được tải lên tối đa 10 MB.");
    return currentUrl;
  }

  if (currentUrl) URL.revokeObjectURL(currentUrl);
  const previewUrl = URL.createObjectURL(file);
  preview.replaceChildren();
  const image = document.createElement("img");
  image.src = previewUrl;
  image.alt = "";
  preview.append(image);
  preview.classList.add("has-image");
  nameLabel.textContent = file.name;
  showMessage("");
  return previewUrl;
}

shirtInput.addEventListener("change", () => {
  const url = setPreview(shirtInput, shirtPreview, shirtName, previewUrls.shirt);
  if (url !== previewUrls.shirt) {
    previewUrls.shirt = url;
    resetResult();
  }
});
patternInput.addEventListener("change", () => {
  const url = setPreview(patternInput, patternPreview, patternName, previewUrls.pattern);
  if (url !== previewUrls.pattern) {
    previewUrls.pattern = url;
    resetResult();
  }
});
window.addEventListener("pagehide", () => {
  Object.values(previewUrls).forEach((url) => {
    if (url) URL.revokeObjectURL(url);
  });
});
window.addEventListener("resize", () => {
  if (!mockupPreview.hidden) updatePlacementPreview();
});

document.querySelectorAll(".range-grid input").forEach((input) => {
  const output = document.querySelector(`#${input.id}-value`);
  input.addEventListener("input", () => {
    output.value = input.id === "rotation" ? `${input.value}°` : `${input.value}%`;
    resetResult();
  });
});

async function loadColors() {
  const response = await fetch("/api/colors");
  if (!response.ok) throw new Error("Không thể tải danh sách màu áo.");
  const data = await response.json();

  for (const color of data.colors) {
    const button = document.createElement("button");
    button.className = "color-choice";
    button.type = "button";
    button.setAttribute("aria-label", color.name);
    button.setAttribute("aria-pressed", String(color.name === selectedColor));
    button.title = color.name;
    if (color.hex) button.style.backgroundColor = color.hex;
    button.addEventListener("click", () => {
      selectedColor = color.name;
      selectedColorLabel.textContent = color.name;
      colorOptions.querySelectorAll("button").forEach((option) => {
        option.setAttribute("aria-pressed", String(option === button));
      });
    });
    colorOptions.append(button);
  }
}

generateButton.addEventListener("click", async () => {
  const shirt = shirtInput.files[0];
  const pattern = patternInput.files[0];
  if (!shirt || !pattern) {
    showMessage("Hãy tải lên đủ ảnh áo và ảnh họa tiết trước nhé.");
    return;
  }

  const form = new FormData();
  form.append("shirt", shirt);
  form.append("pattern", pattern);
  form.append("garment_color", selectedColor);
  form.append("center_x", centerX.value);
  form.append("center_y", centerY.value);
  form.append("print_width", printWidth.value);
  form.append("rotation", rotation.value);

  showMessage("");
  resetResult();
  previewTitle.textContent = "Kết quả";
  emptyState.hidden = true;
  mockupPreview.hidden = true;
  loadingState.hidden = false;
  generateButton.disabled = true;
  buttonLabel.textContent = "Đang tạo thiết kế...";

  try {
    const response = await fetch("/api/generate", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || data.detail || "Không thể tạo ảnh. Vui lòng thử lại.");
    }
    resultImage.src = data.image_url;
    resultImage.hidden = false;
    downloadLink.href = data.image_url;
    downloadLink.hidden = false;
  } catch (error) {
    updatePlacementPreview();
    showMessage(error instanceof Error ? error.message : "Đã có lỗi xảy ra. Vui lòng thử lại.");
  } finally {
    loadingState.hidden = true;
    generateButton.disabled = false;
    buttonLabel.textContent = "Tạo thiết kế";
  }
});

loadColors().catch((error) => showMessage(error.message));
