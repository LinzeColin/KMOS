// 竖屏 1080×1920、46 秒、120 BPM；时长与节拍来自 cues.js。fastFill：无 GPU 时把角色身上的水彩填充换成半透明平涂，
// 大面积水彩天空预渲染成底板（assets/plates，见 README）。
const PROJECT = {
  duration: CUE.dur, bpm: CUE.bpm, offset: 0, w: 1080, h: 1920, fastFill: true,
  fonts: ['60px "ZCOOL KuaiLe"', '60px "Smiley Sans"', '600 40px "Fredoka"', '60px "Permanent Marker"'],
};
