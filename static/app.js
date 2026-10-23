// Các phần giao diện dùng chung.
const form = document.querySelector('#designForm');
const generateButton = document.querySelector('#generate');
const statusElement = document.querySelector('#status');
const resultElement = document.querySelector('#result');
const downloadLink = document.querySelector('#download');

// Hiển thị ảnh vừa chọn; khi chưa có file thì giữ khung hướng dẫn tải ảnh.
function setupImagePreview(inputId, previewId, placeholderId, nameId) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  const placeholder = document.getElementById(placeholderId);
  const name = document.getElementById(nameId);
  let previousUrl = null;

  input.addEventListener('change', () => {
    downloadLink.hidden = true;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    const file = input.files[0];
    if (!file) {
      preview.removeAttribute('src');
      preview.hidden = true;
      placeholder.hidden = false;
      name.textContent = 'Chưa chọn file';
      previousUrl = null;
      renderCompositePreview();
      return;
    }
    previousUrl = URL.createObjectURL(file);
    preview.src = previousUrl;
    preview.hidden = false;
    placeholder.hidden = true;
    name.textContent = file.name;
  });
  preview.addEventListener('load', renderCompositePreview);
  preview.addEventListener('error', () => {
    resultElement.replaceChildren();
    setStatus('Không đọc được ảnh xem trước. Vui lòng chọn PNG, JPEG hoặc WebP hợp lệ.', 'error');
  });
}

function renderCompositePreview() {
  downloadLink.hidden = true;
  const shirt = document.getElementById('shirtPreview');
  const pattern = document.getElementById('patternPreview');
  if (shirt.hidden || !shirt.complete || !shirt.naturalWidth) {
    resultElement.replaceChildren();
    return;
  }
  const canvas = document.createElement('canvas');
  const ratio = Math.min(1, 1000 / Math.max(shirt.naturalWidth, shirt.naturalHeight));
  canvas.width = Math.max(1, Math.round(shirt.naturalWidth * ratio));
  canvas.height = Math.max(1, Math.round(shirt.naturalHeight * ratio));
  canvas.setAttribute('aria-label', 'Xem trước vị trí họa tiết trên ảnh gốc');
  const context = canvas.getContext('2d');
  context.drawImage(shirt, 0, 0, canvas.width, canvas.height);
  if (!pattern.hidden && pattern.complete && pattern.naturalWidth) {
    const w = shirt.naturalWidth, h = shirt.naturalHeight;
    const scale = Math.min(w * Number(document.getElementById('printWidth').value) / 100 / pattern.naturalWidth, h / pattern.naturalHeight);
    const pw = Math.max(1, Math.round(pattern.naturalWidth * scale));
    const ph = Math.max(1, Math.round(pattern.naturalHeight * scale));
    const x = Math.max(0, Math.min(w - pw, Math.floor(w * Number(document.getElementById('centerX').value) / 100 - pw / 2 + 0.5)));
    const y = Math.max(0, Math.min(h - ph, Math.floor(h * Number(document.getElementById('centerY').value) / 100 - ph / 2 + 0.5)));
    context.drawImage(pattern, x * canvas.width / w, y * canvas.height / h, pw * canvas.width / w, ph * canvas.height / h);
  }
  resultElement.replaceChildren(canvas);
  document.getElementById('resultTag').textContent = 'Xem trước';
  setStatus('Bản xem trước bố cục.');
}

function setStatus(message, type = '') {
  statusElement.textContent = message;
  statusElement.className = type ? `status status--${type}` : 'status';
}

function setLoading(isLoading) {
  form.querySelectorAll('input, select, button').forEach(element => { element.disabled = isLoading; });
  generateButton.querySelector('span').textContent = isLoading ? 'Đang tạo ảnh…' : 'Tạo ảnh sản phẩm';
}

// Chỉ đưa ảnh thành phẩm vào khung kết quả; không chèn HTML từ phản hồi API.
function showResult(imageUrl) {
  const image = document.createElement('img');
  image.src = `${imageUrl}?t=${Date.now()}`;
  image.alt = 'Ảnh sản phẩm áo hoàn thiện';
  resultElement.replaceChildren(image);
  downloadLink.href = imageUrl;
  downloadLink.hidden = false;
}

async function handleSubmit(event) {
  event.preventDefault();
  const shirtInput = document.getElementById('shirt');
  const patternInput = document.getElementById('pattern');
  if (!shirtInput.files.length || !patternInput.files.length) {
    setStatus('Vui lòng chọn đủ ảnh áo và ảnh họa tiết.', 'error');
    (shirtInput.files.length ? patternInput : shirtInput).focus();
    return;
  }
  const data = new FormData(form);
  setLoading(true);
  setStatus('Đang tạo thiết kế…');
  document.getElementById('resultTag').textContent = 'Đang tạo';

  try {
    const response = await fetch('/api/generate', { method: 'POST', body: data });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || 'Không thể tạo ảnh.');

    showResult(body.image_url);
    document.getElementById('resultTag').textContent = 'Hoàn tất';
    setStatus(body.status || 'Đã tạo xong ảnh sản phẩm.', 'success');
  } catch (error) {
    document.getElementById('resultTag').textContent = 'Chưa hoàn tất';
    setStatus(`Không tạo được ảnh: ${error.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

setupImagePreview('shirt', 'shirtPreview', 'shirtPlaceholder', 'shirtName');
setupImagePreview('pattern', 'patternPreview', 'patternPlaceholder', 'patternName');
form.addEventListener('submit', handleSubmit);
for (const id of ['centerX', 'centerY', 'printWidth']) {
  document.getElementById(id).addEventListener('input', event => {
    document.getElementById(`${id}Value`).textContent = `${event.target.value}%`;
    renderCompositePreview();
  });
}

document.getElementById('garmentColor').addEventListener('change', renderCompositePreview);
