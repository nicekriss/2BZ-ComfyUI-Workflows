const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
function base64(bytes) {
  const parts = [];
  let chunk = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i], b = bytes[i + 1] || 0, c = bytes[i + 2] || 0;
    chunk += ALPHABET[a >> 2] + ALPHABET[((a & 3) << 4) | (b >> 4)] +
      (i + 1 < bytes.length ? ALPHABET[((b & 15) << 2) | (c >> 6)] : "=") +
      (i + 2 < bytes.length ? ALPHABET[c & 63] : "=");
    if (chunk.length >= 8192) { parts.push(chunk); chunk = ""; }
  }
  parts.push(chunk);
  return parts.join("");
}
function inputPreviewPath(name) {
  if (!/^TooBusyPS\/[a-f0-9]{32}\.png$/.test(name)) throw new Error("싱크 이미지 경로가 올바르지 않습니다.");
  return "/view?type=input&subfolder=TooBusyPS&filename=" + encodeURIComponent(name.slice(10)) + "&preview=jpeg;85";
}
module.exports = {base64, inputPreviewPath};
