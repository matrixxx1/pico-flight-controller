const TOF_CHANNELS = [0, 1, 2, 3, 6];
const els = {
  craft: document.querySelector("#craft"),
  driftVector: document.querySelector("#drift-vector"),
  scenario: document.querySelector("#scenario"),
  play: document.querySelector("#play"),
  step: document.querySelector("#step"),
  reset: document.querySelector("#reset"),
  throttle: document.querySelector("#throttle"),
  yaw: document.querySelector("#yaw"),
  pitchControl: document.querySelector("#pitch-control"),
  rollControl: document.querySelector("#roll-control"),
  wind: document.querySelector("#wind"),
  tofFault: document.querySelector("#tof-fault"),
  magFault: document.querySelector("#mag-fault"),
  rcStale: document.querySelector("#rc-stale"),
  useGamepad: document.querySelector("#use-gamepad"),
  gamepadStatus: document.querySelector("#gamepad-status"),
  connectSerial: document.querySelector("#connect-serial"),
  reconnectSerial: document.querySelector("#reconnect-serial"),
  serialBaud: document.querySelector("#serial-baud"),
  baudPresets: [...document.querySelectorAll(".baud-preset")],
  serialStatus: document.querySelector("#serial-status"),
  status: document.querySelector("#status"),
  serialLine: document.querySelector("#serial-line"),
  script: document.querySelector("#script"),
  runScript: document.querySelector("#run-script"),
  loadExample: document.querySelector("#load-example"),
  copyLine: document.querySelector("#copy-line"),
  heading: document.querySelector("#heading"),
  pitch: document.querySelector("#pitch"),
  roll: document.querySelector("#roll"),
  drift: document.querySelector("#drift"),
  tof: Object.fromEntries(TOF_CHANNELS.map((channel) => [channel, document.querySelector(`#tof${channel}`)])),
};

const state = {
  running: true,
  t: 0,
  heading: 0,
  pitch: 0,
  roll: 0,
  drift: 0,
  altitude: 620,
  scriptQueue: [],
  scriptIndex: 0,
  scriptHold: 0,
  gamepadEnabled: false,
  gamepadIndex: null,
  gamepadId: "",
  serialEnabled: false,
  serialPort: null,
  serialReader: null,
  serialBytes: [],
  serialText: "",
  rc: [1500, 1500, 1500, 1500, 1000, 1500, 1000, 1500],
  tof: { 0: 620, 1: 900, 2: 740, 3: 740, 6: 880 },
};

function reset() {
  state.t = 0;
  state.heading = 0;
  state.pitch = 0;
  state.roll = 0;
  state.drift = 0;
  state.altitude = 620;
  state.scriptQueue = [];
  state.scriptIndex = 0;
  state.scriptHold = 0;
  state.gamepadIndex = null;
  state.gamepadId = "";
  els.scenario.value = "manual";
  setSliderValues({ throttle: 1500, yaw: 1500, pitch: 1500, roll: 1500, wind: 0 });
  els.tofFault.checked = false;
  els.magFault.checked = false;
  els.rcStale.checked = false;
  update(0.1);
  els.status.textContent = "Reset";
}

function setSliderValues(values) {
  if (values.throttle !== undefined) els.throttle.value = values.throttle;
  if (values.yaw !== undefined) els.yaw.value = values.yaw;
  if (values.pitch !== undefined) els.pitchControl.value = values.pitch;
  if (values.roll !== undefined) els.rollControl.value = values.roll;
  if (values.wind !== undefined) els.wind.value = values.wind;
}

function update(dt) {
  state.t += dt;
  applyScenario(dt);
  applyControls(dt);
  updateDistances();
  render();
}

function applyScenario(dt) {
  const scenario = els.scenario.value;
  if (scenario === "drift") {
    setSliderValues({
      throttle: 1570,
      yaw: 1500 + Math.sin(state.t * 0.45) * 90,
      pitch: 1530 + Math.sin(state.t * 0.8) * 80,
      roll: 1500 + Math.sin(state.t * 1.25) * 230,
      wind: 58 + Math.sin(state.t * 0.5) * 28,
    });
  } else if (scenario === "rc") {
    setSliderValues({
      throttle: 1450 + Math.sin(state.t * 0.8) * 220,
      yaw: 1500 + Math.sin(state.t * 0.7) * 390,
      pitch: 1500 + Math.sin(state.t * 1.2 + 1.5) * 430,
      roll: 1500 + Math.sin(state.t * 1.1 + 3.1) * 430,
      wind: 8,
    });
  } else if (scenario === "fault") {
    setSliderValues({ throttle: 1500, yaw: 1510, pitch: 1500, roll: 1500, wind: 0 });
    els.tofFault.checked = Math.floor(state.t) % 3 !== 0;
    els.magFault.checked = Math.floor(state.t) % 8 >= 5;
  } else if (scenario === "landing") {
    setSliderValues({
      throttle: 1320,
      yaw: 1500,
      pitch: 1430 + Math.sin(state.t * 0.7) * 50,
      roll: 1500 + Math.sin(state.t * 0.9) * 65,
      wind: -16,
    });
    state.altitude = Math.max(80, state.altitude - dt * 18);
  }

  if (state.scriptQueue.length) {
    applyScript(dt);
  }

  if (state.gamepadEnabled) {
    applyGamepadInput();
  }
}

function applyGamepadInput() {
  const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
  const selected =
    pads.find((pad) => pad.index === state.gamepadIndex) ??
    pads.find((pad) => /radiolink|t8|controller|joystick|gamepad|hid/i.test(pad.id)) ??
    pads[0];

  if (!selected) {
    els.gamepadStatus.textContent = "No browser gamepad found yet. Move a stick, press a transmitter button, or replug USB.";
    return;
  }

  state.gamepadIndex = selected.index;
  state.gamepadId = selected.id || `Gamepad ${selected.index}`;
  const axes = selected.axes.map((value) => applyDeadzone(value));
  const yaw = axisToPwm(axes[0] ?? 0, false);
  const pitch = axisToPwm(axes[1] ?? 0, true);
  const throttle = axisToPwm(axes[2] ?? axes[1] ?? 0, true);
  const roll = axisToPwm(axes[3] ?? axes[0] ?? 0, false);

  els.scenario.value = "manual";
  setSliderValues({ throttle, yaw, pitch, roll });
  els.gamepadStatus.textContent = `${state.gamepadId}
axes=${axes.map((value) => value.toFixed(2)).join(", ")}
mapped rc1=${Math.round(yaw)} rc2=${Math.round(pitch)} rc3=${Math.round(throttle)} rc4=${Math.round(roll)}`;
}

async function connectSerialController() {
  if (!("serial" in navigator)) {
    els.serialStatus.textContent = "Web Serial needs Chrome or Edge over localhost.";
    return;
  }

  if (state.serialEnabled) {
    await disconnectSerialController({ forgetPort: false });
    return;
  }

  try {
    if (!state.serialPort) {
      state.serialPort = await navigator.serial.requestPort({
        filters: [{ usbVendorId: 0x1a86, usbProductId: 0x7523 }],
      });
    }
    await openSerialControllerPort();
  } catch (error) {
    els.serialStatus.textContent = `Serial connect failed: ${error.message}`;
  }
}

async function openSerialControllerPort() {
  const baudRate = Number(els.serialBaud.value);
  await state.serialPort.open(getSerialOptions(baudRate));
  state.serialEnabled = true;
  state.serialBytes = [];
  state.serialText = "";
  els.connectSerial.textContent = "Disconnect";
  els.status.textContent = "Serial RC input enabled";
  els.serialStatus.textContent = `Connected at ${baudRate}. Move the sticks.`;
  readSerialControllerLoop();
}

function getSerialOptions(baudRate) {
  return {
    baudRate,
    dataBits: 8,
    stopBits: baudRate === 100000 ? 2 : 1,
    parity: baudRate === 100000 ? "even" : "none",
    flowControl: "none",
  };
}

function setBaudRate(baudRate) {
  els.serialBaud.value = String(baudRate);
  for (const button of els.baudPresets) {
    button.classList.toggle("active", button.dataset.baud === String(baudRate));
  }
}

async function disconnectSerialController({ forgetPort = false } = {}) {
  state.serialEnabled = false;
  if (state.serialReader) {
    await state.serialReader.cancel().catch(() => {});
  }
  if (state.serialPort) {
    await state.serialPort.close().catch(() => {});
  }
  state.serialReader = null;
  if (forgetPort) {
    state.serialPort = null;
  }
  els.connectSerial.textContent = "Connect COM4";
  els.status.textContent = "Serial RC input stopped";
  els.serialStatus.textContent = "Disconnected. Pick another baud, then click Apply Baud or Connect COM4.";
}

async function reconnectSerialController() {
  try {
    if (!state.serialPort) {
      await connectSerialController();
      return;
    }
    const baudRate = Number(els.serialBaud.value);
    if (state.serialEnabled) {
      await disconnectSerialController({ forgetPort: false });
    }
    els.serialStatus.textContent = `Reopening COM at ${baudRate}...`;
    await openSerialControllerPort();
  } catch (error) {
    els.serialStatus.textContent = `Baud change failed: ${error.message}`;
  }
}

async function readSerialControllerLoop() {
  try {
    state.serialReader = state.serialPort.readable.getReader();
    while (state.serialEnabled) {
      const { value, done } = await state.serialReader.read();
      if (done) break;
      if (!value?.length) continue;
      handleSerialBytes([...value]);
    }
  } catch (error) {
    if (state.serialEnabled) {
      els.serialStatus.textContent = `Serial read stopped: ${error.message}`;
    }
  } finally {
    state.serialReader?.releaseLock?.();
    state.serialReader = null;
  }
}

function handleSerialBytes(bytes) {
  state.serialBytes.push(...bytes);
  if (state.serialBytes.length > 512) {
    state.serialBytes.splice(0, state.serialBytes.length - 512);
  }

  const decoded =
    decodeIbusFrames() ||
    decodeSbusFrames() ||
    decodeTextFrames(bytes);

  const hex = bytes
    .slice(0, 32)
    .map((value) => value.toString(16).padStart(2, "0"))
    .join(" ");
  if (!decoded) {
    els.serialStatus.textContent = `Reading raw serial. Last bytes: ${hex || "none"}`;
  }
}

function decodeTextFrames(bytes) {
  const text = new TextDecoder("utf-8", { fatal: false }).decode(new Uint8Array(bytes));
  state.serialText += text;
  if (state.serialText.length > 1000) {
    state.serialText = state.serialText.slice(-1000);
  }
  const lines = state.serialText.split(/\r?\n/);
  state.serialText = lines.pop() ?? "";
  for (const line of lines) {
    const channels = parseChannelNumbers(line);
    if (channels) {
      applySerialChannels(channels, "text");
      return true;
    }
  }
  return false;
}

function decodeIbusFrames() {
  for (let offset = 0; offset <= state.serialBytes.length - 32; offset += 1) {
    if (state.serialBytes[offset] !== 0x20 || state.serialBytes[offset + 1] !== 0x40) continue;
    const frame = state.serialBytes.slice(offset, offset + 32);
    const expected = frame[30] | (frame[31] << 8);
    const actual = 0xffff - frame.slice(0, 30).reduce((sum, value) => sum + value, 0);
    if (expected !== actual) continue;
    const channels = [];
    for (let index = 0; index < 14; index += 1) {
      channels.push(frame[2 + index * 2] | (frame[3 + index * 2] << 8));
    }
    state.serialBytes.splice(0, offset + 32);
    applySerialChannels(channels, "iBUS");
    return true;
  }
  return false;
}

function decodeSbusFrames() {
  for (let offset = 0; offset <= state.serialBytes.length - 25; offset += 1) {
    if (state.serialBytes[offset] !== 0x0f) continue;
    const frame = state.serialBytes.slice(offset, offset + 25);
    const endByte = frame[24];
    if (![0x00, 0x04, 0x14, 0x24, 0x34].includes(endByte)) continue;
    const data = frame.slice(1, 23);
    const channels = [
      (data[0] | (data[1] << 8)) & 0x07ff,
      ((data[1] >> 3) | (data[2] << 5)) & 0x07ff,
      ((data[2] >> 6) | (data[3] << 2) | (data[4] << 10)) & 0x07ff,
      ((data[4] >> 1) | (data[5] << 7)) & 0x07ff,
      ((data[5] >> 4) | (data[6] << 4)) & 0x07ff,
      ((data[6] >> 7) | (data[7] << 1) | (data[8] << 9)) & 0x07ff,
      ((data[8] >> 2) | (data[9] << 6)) & 0x07ff,
      ((data[9] >> 5) | (data[10] << 3)) & 0x07ff,
    ].map(sbusToPwm);
    state.serialBytes.splice(0, offset + 25);
    applySerialChannels(channels, "SBUS");
    return true;
  }
  return false;
}

function parseChannelNumbers(line) {
  const rcMatches = [...line.matchAll(/\brc([1-8])=(\d{3,4})/gi)];
  if (rcMatches.length >= 4) {
    const channels = Array(8).fill(1500);
    for (const match of rcMatches) {
      channels[Number(match[1]) - 1] = Number(match[2]);
    }
    return channels;
  }

  const numbers = line.match(/\b(?:[9]\d{2}|1\d{3}|20\d{2}|21\d{2}|22[0-5]\d)\b/g);
  if (numbers && numbers.length >= 4) {
    return numbers.slice(0, 8).map(Number);
  }
  return null;
}

function applySerialChannels(channels, source) {
  const normalized = channels.map((value) => clamp(Number(value), 1000, 2000));
  els.scenario.value = "manual";
  setSliderValues({
    yaw: normalized[0] ?? 1500,
    pitch: normalized[1] ?? 1500,
    throttle: normalized[2] ?? 1500,
    roll: normalized[3] ?? 1500,
  });
  els.serialStatus.textContent = `${source} channels
rc1=${Math.round(normalized[0] ?? 1500)} rc2=${Math.round(normalized[1] ?? 1500)} rc3=${Math.round(
    normalized[2] ?? 1500,
  )} rc4=${Math.round(normalized[3] ?? 1500)}
rc5=${Math.round(normalized[4] ?? 1500)} rc6=${Math.round(normalized[5] ?? 1500)} rc7=${Math.round(
    normalized[6] ?? 1500,
  )} rc8=${Math.round(normalized[7] ?? 1500)}`;
}

function applyScript(dt) {
  if (state.scriptIndex >= state.scriptQueue.length) {
    state.scriptQueue = [];
    els.status.textContent = "Script complete";
    return;
  }

  state.scriptHold -= dt;
  if (state.scriptHold > 0) return;

  const instruction = state.scriptQueue[state.scriptIndex];
  state.scriptIndex += 1;
  state.scriptHold = instruction.hold;
  if (instruction.scenario) els.scenario.value = instruction.scenario;
  if (instruction.values) setSliderValues(instruction.values);
  if (instruction.faults) {
    els.tofFault.checked = Boolean(instruction.faults.tof);
    els.magFault.checked = Boolean(instruction.faults.mag);
    els.rcStale.checked = Boolean(instruction.faults.rcStale);
  }
  els.status.textContent = `Instruction ${state.scriptIndex}/${state.scriptQueue.length}`;
}

function applyControls(dt) {
  const throttle = Number(els.throttle.value);
  const yaw = Number(els.yaw.value);
  const pitchControl = Number(els.pitchControl.value);
  const rollControl = Number(els.rollControl.value);
  const wind = Number(els.wind.value);

  state.rc = els.rcStale.checked
    ? Array(8).fill(null)
    : [
        Math.round(yaw),
        Math.round(pitchControl),
        Math.round(throttle),
        Math.round(rollControl),
        throttle > 1550 ? 2000 : 1000,
        1500 + Math.round(wind * 3),
        wind > 25 ? 2000 : 1000,
        rollControl,
      ];

  const yawRate = (yaw - 1500) / 500;
  const pitchTarget = ((pitchControl - 1500) / 500) * -35;
  const rollTarget = ((rollControl - 1500) / 500) * 50 + wind * 0.08;
  state.heading = normalizeDegrees(state.heading + yawRate * 54 * dt + wind * 0.018);
  state.pitch = lerp(state.pitch, pitchTarget, 0.08);
  state.roll = lerp(state.roll, rollTarget, 0.1);
  state.drift = lerp(state.drift, wind / 100, 0.05);
  if (els.scenario.value !== "landing") {
    state.altitude = clamp(state.altitude + ((throttle - 1500) / 500) * 90 * dt - Math.abs(state.pitch) * 0.08, 80, 1400);
  }
}

function updateDistances() {
  const sideBias = state.roll * 4;
  const forwardBias = state.pitch * 5;
  state.tof = {
    0: Math.round(state.altitude),
    1: Math.round(clamp(1300 - state.altitude + Math.abs(state.pitch) * 5, 80, 2000)),
    2: Math.round(clamp(760 - sideBias, 40, 2000)),
    3: Math.round(clamp(760 + sideBias, 40, 2000)),
    6: Math.round(clamp(900 + forwardBias - Math.abs(state.drift) * 140, 40, 2000)),
  };
}

function render() {
  const rawX = Math.round(Math.cos(toRad(state.heading)) * 420);
  const rawY = Math.round(Math.sin(toRad(state.heading)) * 420);
  const rawZ = Math.round(Math.sin(state.t * 0.75) * 80);
  const ax = Math.sin(toRad(state.pitch)) * -1;
  const ay = Math.sin(toRad(state.roll));
  const az = Math.max(0.15, Math.cos(toRad(state.pitch)) * Math.cos(toRad(state.roll)));
  const line = makeSerialLine({ rawX, rawY, rawZ, ax, ay, az });

  els.serialLine.textContent = line;
  els.heading.textContent = `${state.heading.toFixed(1)} deg`;
  els.pitch.textContent = `${state.pitch.toFixed(1)} deg`;
  els.roll.textContent = `${state.roll.toFixed(1)} deg`;
  els.drift.textContent = state.drift.toFixed(2);
  for (const channel of TOF_CHANNELS) {
    els.tof[channel].textContent = els.tofFault.checked ? "err" : `${state.tof[channel]} mm`;
  }

  els.craft.style.transform = `translate(-50%, -50%) rotate(${state.roll.toFixed(1)}deg) translateY(${(
    -state.pitch * 1.2
  ).toFixed(1)}px)`;
  els.driftVector.style.opacity = Math.min(0.85, Math.abs(state.drift) + 0.12).toFixed(2);
  els.driftVector.style.transform = `translate(-50%, -50%) rotate(${(state.drift * 35).toFixed(1)}deg) scaleX(${(
    0.5 + Math.abs(state.drift) * 1.4
  ).toFixed(2)})`;
}

function makeSerialLine({ rawX, rawY, rawZ, ax, ay, az }) {
  const sensor = els.magFault.checked ? "QMC5883P / HP5883 x=0 y=0 z=0 heading=0.0" : `QMC5883P / HP5883 x=${rawX} y=${rawY} z=${rawZ} xuT=${(rawX / 1000).toFixed(2)} yuT=${(rawY / 1000).toFixed(2)} zuT=${(rawZ / 1000).toFixed(2)} heading=${state.heading.toFixed(1)}`;
  const tof = TOF_CHANNELS.map((channel) => `tof${channel}=${els.tofFault.checked ? "err" : state.tof[channel]}`).join(" ");
  const rc = els.rcStale.checked
    ? Array.from({ length: 8 }, (_, index) => `rc${index + 1}=None`).join(" ")
    : state.rc.map((value, index) => `rc${index + 1}=${Math.round(value)}`).join(" ");
  const magError = els.magFault.checked ? " magerr=[Errno 110] ETIMEDOUT" : "";
  return `sensor=${sensor} ${tof} adxl=ok ax=${ax.toFixed(3)} ay=${ay.toFixed(3)} az=${az.toFixed(
    3,
  )} pitch=${state.pitch.toFixed(1)} roll=${state.roll.toFixed(1)} rc=ppm ${rc}${magError}`;
}

function parseScript(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => {
      const parts = Object.fromEntries(
        line.split(/\s+/).map((part) => {
          const [key, value = ""] = part.split("=");
          return [key.toLowerCase(), value];
        }),
      );
      return {
        hold: Number(parts.hold ?? parts.wait ?? 0.8),
        scenario: parts.scenario,
        values: {
          throttle: toNumber(parts.throttle),
          yaw: toNumber(parts.yaw ?? parts.ch1),
          pitch: toNumber(parts.pitch ?? parts.ch2),
          roll: toNumber(parts.roll ?? parts.ch4),
          wind: toNumber(parts.wind),
        },
        faults: {
          tof: parts.tof === "err",
          mag: parts.mag === "err",
          rcStale: parts.rc === "stale",
        },
      };
    });
}

function toNumber(value) {
  if (value === undefined || value === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function applyDeadzone(value) {
  if (!Number.isFinite(value) || Math.abs(value) < 0.04) return 0;
  return clamp(value, -1, 1);
}

function axisToPwm(value, invert) {
  const signed = invert ? -value : value;
  return Math.round(clamp(1500 + signed * 500, 1000, 2000));
}

function sbusToPwm(value) {
  return Math.round(clamp(1000 + ((value - 172) / (1811 - 172)) * 1000, 1000, 2000));
}

function loadExample() {
  els.script.value = [
    "# One instruction per line. Values are PWM microseconds unless noted.",
    "scenario=manual throttle=1550 yaw=1500 pitch=1450 roll=1500 wind=0 hold=1.0",
    "scenario=manual throttle=1580 yaw=1500 pitch=1500 roll=1850 wind=45 hold=1.4",
    "scenario=manual throttle=1520 yaw=1200 pitch=1530 roll=1500 wind=30 hold=1.0",
    "scenario=manual throttle=1400 yaw=1500 pitch=1600 roll=1300 wind=-40 hold=1.2",
    "scenario=manual throttle=1500 yaw=1500 pitch=1500 roll=1500 wind=0 hold=1.0",
    "scenario=fault tof=err mag=err rc=stale hold=1.0",
  ].join("\n");
}

function runScript() {
  state.scriptQueue = parseScript(els.script.value);
  state.scriptIndex = 0;
  state.scriptHold = 0;
  els.status.textContent = state.scriptQueue.length ? "Script armed" : "No script instructions";
}

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function lerp(a, b, amount) {
  return a + (b - a) * amount;
}

function toRad(value) {
  return (value * Math.PI) / 180;
}

els.play.addEventListener("click", () => {
  state.running = !state.running;
  els.play.textContent = state.running ? "Pause" : "Play";
  els.status.textContent = state.running ? "Running" : "Paused";
});
els.step.addEventListener("click", () => update(0.1));
els.reset.addEventListener("click", reset);
els.useGamepad.addEventListener("click", () => {
  state.gamepadEnabled = !state.gamepadEnabled;
  els.useGamepad.textContent = state.gamepadEnabled ? "Stop T8FB" : "Use T8FB";
  els.status.textContent = state.gamepadEnabled ? "USB controller input enabled" : "USB controller input stopped";
  if (state.gamepadEnabled) {
    applyGamepadInput();
  }
});
els.connectSerial.addEventListener("click", connectSerialController);
els.reconnectSerial.addEventListener("click", reconnectSerialController);
els.serialBaud.addEventListener("change", () => {
  setBaudRate(els.serialBaud.value);
  if (state.serialEnabled) {
    reconnectSerialController();
  } else if (state.serialPort) {
    els.serialStatus.textContent = "Baud changed. Click Apply Baud to reopen the same COM port.";
  }
});
for (const button of els.baudPresets) {
  button.addEventListener("click", () => {
    setBaudRate(button.dataset.baud);
    if (state.serialEnabled) {
      reconnectSerialController();
    } else if (state.serialPort) {
      els.serialStatus.textContent = "Baud changed. Click Apply Baud to reopen the same COM port.";
    } else {
      els.serialStatus.textContent = `Baud set to ${button.textContent}. Click Connect COM4.`;
    }
  });
}
els.loadExample.addEventListener("click", loadExample);
els.runScript.addEventListener("click", runScript);
els.copyLine.addEventListener("click", async () => {
  await navigator.clipboard.writeText(els.serialLine.textContent);
  els.status.textContent = "Serial line copied";
});

window.addEventListener("gamepadconnected", (event) => {
  state.gamepadIndex = event.gamepad.index;
  state.gamepadId = event.gamepad.id;
  els.gamepadStatus.textContent = `Detected ${event.gamepad.id}. Click Use T8FB to feed it into RC channels.`;
});

window.addEventListener("gamepaddisconnected", (event) => {
  if (event.gamepad.index === state.gamepadIndex) {
    state.gamepadIndex = null;
    els.gamepadStatus.textContent = "Controller disconnected.";
  }
});

let lastTime = performance.now();
function frame(time) {
  const dt = Math.min(0.05, (time - lastTime) / 1000);
  lastTime = time;
  if (state.running) update(dt);
  requestAnimationFrame(frame);
}

loadExample();
update(0.1);
requestAnimationFrame(frame);
