const VIDEO_FORMATS = ["mp4", "webm", "mov", "mkv"];

const videoFormatField = {
  name: "output_format",
  label: "输出格式",
  type: "select",
  options: VIDEO_FORMATS,
  value: "mp4",
};

export const OPERATIONS = {
  convert: [videoFormatField],
  compress: [
    videoFormatField,
    {
      name: "crf",
      label: "CRF",
      type: "number",
      min: 18,
      max: 51,
      step: 1,
      value: 23,
    },
    {
      name: "preset",
      label: "编码预设",
      type: "select",
      options: ["ultrafast", "veryfast", "fast", "medium", "slow", "veryslow"],
      value: "medium",
    },
    {
      name: "width",
      label: "宽度",
      type: "number",
      min: 64,
      max: 7680,
      step: 2,
      placeholder: "可选",
    },
  ],
  extract_audio: [
    {
      name: "audio_format",
      label: "音频格式",
      type: "select",
      options: ["mp3", "wav", "aac", "flac"],
      value: "mp3",
    },
  ],
  gif: [
    {
      name: "fps",
      label: "帧率",
      type: "number",
      min: 1,
      max: 30,
      step: 1,
      value: 10,
    },
    {
      name: "width",
      label: "宽度",
      type: "number",
      min: 64,
      max: 1920,
      step: 2,
      value: 480,
    },
  ],
  mute: [videoFormatField],
  rotate: [
    {
      name: "mode",
      label: "变换",
      type: "select",
      options: [
        ["cw90", "顺时针 90 度"],
        ["ccw90", "逆时针 90 度"],
        ["180", "旋转 180 度"],
        ["hflip", "水平翻转"],
        ["vflip", "垂直翻转"],
        ["hvflip", "水平+垂直翻转"],
      ],
      value: "cw90",
    },
    videoFormatField,
  ],
  crop: [
    { name: "x", label: "X", type: "number", min: 0, step: 1, value: 0, required: true },
    { name: "y", label: "Y", type: "number", min: 0, step: 1, value: 0, required: true },
    { name: "width", label: "裁剪宽度", type: "number", min: 1, step: 1, required: true },
    { name: "height", label: "裁剪高度", type: "number", min: 1, step: 1, required: true },
    videoFormatField,
  ],
  thumbnail: [
    {
      name: "timestamp_seconds",
      label: "时间点秒数",
      type: "number",
      min: 0,
      step: 0.1,
      value: 0,
    },
    {
      name: "image_format",
      label: "图片格式",
      type: "select",
      options: ["jpg", "png"],
      value: "jpg",
    },
  ],
  speed: [
    {
      name: "factor",
      label: "速度倍数",
      type: "number",
      min: 0.25,
      max: 4,
      step: 0.05,
      value: 1,
    },
    videoFormatField,
  ],
  volume: [
    {
      name: "multiplier",
      label: "音量倍数",
      type: "number",
      min: 0,
      max: 4,
      step: 0.05,
      value: 1,
    },
    videoFormatField,
  ],
  strip_metadata: [videoFormatField],
  normalize_audio: [
    {
      name: "target_lufs",
      label: "目标响度",
      type: "select",
      options: [
        ["-14", "-14 LUFS"],
        ["-16", "-16 LUFS"],
        ["-23", "-23 LUFS"],
      ],
      value: "-16",
    },
    videoFormatField,
  ],
  subtitles: [
    {
      name: "subtitle_file",
      label: "字幕文件",
      type: "file",
      accept: ".srt,.vtt,.ass,.ssa",
      required: true,
      wide: true,
    },
    {
      name: "output_format",
      label: "输出格式",
      type: "select",
      options: ["mp4", "mkv"],
      value: "mp4",
    },
  ],
  raw: [
    {
      name: "raw_args",
      label: "FFmpeg 参数",
      type: "textarea",
      placeholder: "-vf scale=1280:-2 -c:v libx264 -crf 23 -c:a aac",
      required: true,
      wide: true,
      rawArray: true,
    },
    {
      name: "output_extension",
      label: "输出扩展名",
      type: "text",
      value: "mp4",
      placeholder: "mp4",
    },
    {
      name: "raw_note",
      type: "note",
      text: "Raw FFmpeg 仅面向个人本机高级使用。输入和输出路径仍由后端统一管理。",
      wide: true,
    },
  ],
};

export function renderOperationFields(container, operation) {
  container.replaceChildren();
  for (const field of OPERATIONS[operation] || []) {
    container.appendChild(createField(field));
  }
}

export function collectJobPayload(form, fileId) {
  const formData = new FormData(form);
  const operation = formData.get("operation");
  const options = {};

  for (const key of ["start_seconds", "end_seconds"]) {
    const value = normalizeNumber(formData.get(key));
    if (value !== null) {
      options[key] = value;
    }
  }

  for (const field of OPERATIONS[operation] || []) {
    if (field.type === "file" || field.type === "note") {
      continue;
    }
    const raw = formData.get(field.name);
    if (field.rawArray) {
      options[field.name] = parseShellArgs(String(raw || ""));
    } else if (field.type === "number") {
      const value = normalizeNumber(raw);
      if (value !== null) {
        options[field.name] = value;
      }
    } else if (raw !== null && raw !== "") {
      options[field.name] = raw;
    }
  }

  return { file_id: fileId, operation, options };
}

function createField(field) {
  if (field.type === "note") {
    const note = document.createElement("p");
    note.className = "field-note";
    note.textContent = field.text;
    return note;
  }

  const wrapper = document.createElement("div");
  wrapper.className = field.wide ? "field is-wide" : "field";

  const label = document.createElement("label");
  label.htmlFor = field.name;
  label.textContent = field.label;
  wrapper.appendChild(label);

  if (field.type === "select") {
    const select = document.createElement("select");
    select.id = field.name;
    select.name = field.name;
    if (field.required) {
      select.required = true;
    }
    for (const item of field.options) {
      const [value, text] = Array.isArray(item) ? item : [item, item];
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      option.selected = value === field.value;
      select.appendChild(option);
    }
    wrapper.appendChild(select);
    return wrapper;
  }

  if (field.type === "textarea") {
    const textarea = document.createElement("textarea");
    textarea.id = field.name;
    textarea.name = field.name;
    textarea.placeholder = field.placeholder || "";
    textarea.required = Boolean(field.required);
    wrapper.appendChild(textarea);
    return wrapper;
  }

  const input = document.createElement("input");
  input.id = field.name;
  input.name = field.name;
  input.type = field.type;
  input.required = Boolean(field.required);
  for (const attr of ["min", "max", "step", "placeholder", "accept"]) {
    if (field[attr] !== undefined) {
      input.setAttribute(attr, field[attr]);
    }
  }
  if (field.value !== undefined) {
    input.value = field.value;
  }
  wrapper.appendChild(input);
  return wrapper;
}

function normalizeNumber(value) {
  if (value === null || value === "") {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function parseShellArgs(value) {
  const args = [];
  let current = "";
  let quote = null;
  let escaping = false;

  for (const char of value.trim()) {
    if (escaping) {
      current += char;
      escaping = false;
      continue;
    }
    if (char === "\\") {
      escaping = true;
      continue;
    }
    if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }
    if (/\s/.test(char)) {
      if (current) {
        args.push(current);
        current = "";
      }
      continue;
    }
    current += char;
  }

  if (escaping) {
    current += "\\";
  }
  if (quote) {
    throw new Error("Raw FFmpeg 参数引号未闭合");
  }
  if (current) {
    args.push(current);
  }
  return args;
}
