export const OPERATIONS = {
  convert: [
    {
      name: "output_format",
      label: "输出格式",
      type: "select",
      options: ["mp4", "webm", "mov", "mkv"],
      value: "mp4",
    },
  ],
  compress: [
    {
      name: "output_format",
      label: "输出格式",
      type: "select",
      options: ["mp4", "webm", "mov", "mkv"],
      value: "mp4",
    },
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
    const raw = formData.get(field.name);
    if (field.type === "number") {
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
  const wrapper = document.createElement("div");
  wrapper.className = "field";

  const label = document.createElement("label");
  label.htmlFor = field.name;
  label.textContent = field.label;
  wrapper.appendChild(label);

  if (field.type === "select") {
    const select = document.createElement("select");
    select.id = field.name;
    select.name = field.name;
    for (const item of field.options) {
      const option = document.createElement("option");
      option.value = item;
      option.textContent = item;
      option.selected = item === field.value;
      select.appendChild(option);
    }
    wrapper.appendChild(select);
    return wrapper;
  }

  const input = document.createElement("input");
  input.id = field.name;
  input.name = field.name;
  input.type = field.type;
  for (const attr of ["min", "max", "step", "placeholder"]) {
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

