const POLICY = 1;

function restore(saved) {
  if (!saved) return saved;
  const settings = {...saved, inpaintLineartPolicy: POLICY};
  if (saved.inpaint && saved.inpaintLineartPolicy !== POLICY) settings.lineart = false;
  return settings;
}

function bind({inpaint, lineart, denoise, persist, status}) {
  inpaint.addEventListener("change", () => {
    if (inpaint.checked) {
      lineart.checked = false;
      denoise.value = "0.75";
      status("선택 영역 수정 · 라인아트를 껐어요. 필요하면 다시 켤 수 있어요.");
    }
    persist();
  });
}

module.exports = {POLICY, restore, bind};
