import * as THREE from "three";
import "./styles.css";

const app = document.querySelector("#app");
const TOF_CHANNELS = [0, 1, 2, 3, 6];
const ORIENTATION_MAP_VERSION = 2;
const DEFAULT_ORIENTATION_MAP = {
  version: ORIENTATION_MAP_VERSION,
  forward: [0.99, -0.03, 0.1],
  right: [-0.05, -1.0, -0.03],
  level: [0.0, -0.12, -0.99],
};

function makeEmptyTofReadings() {
  return Object.fromEntries(TOF_CHANNELS.map((channel) => [channel, null]));
}

app.innerHTML = `
  <main class="shell">
    <section class="stage" aria-label="3D plane heading and altitude visualization">
      <div class="attitude-strip" aria-label="Pitch, roll, and tilt meters">
        <div class="meter tilt-meter">
          <span class="label">Tilt</span>
          <div class="tilt-face" aria-hidden="true">
            <i class="gauge-tick tick-n"></i>
            <i class="gauge-tick tick-e"></i>
            <i class="gauge-tick tick-s"></i>
            <i class="gauge-tick tick-w"></i>
            <i class="tilt-cross tilt-cross-x"></i>
            <i class="tilt-cross tilt-cross-y"></i>
            <b class="mini-aircraft">+</b>
            <i id="tilt-dot" class="tilt-dot"></i>
          </div>
          <strong id="tilt-value">--</strong>
        </div>
        <div class="meter pitch-meter">
          <span class="label">Pitch</span>
          <div class="pitch-face" aria-hidden="true">
            <div id="pitch-bar" class="pitch-horizon">
              <i class="sky"></i>
              <i class="ground"></i>
              <span class="horizon-line"></span>
            </div>
            <div class="pitch-ladder">
              <i></i><i></i><i></i><i></i><i></i>
            </div>
            <b class="aircraft-symbol"></b>
          </div>
          <strong id="pitch-meter-value">--</strong>
        </div>
        <div class="meter roll-meter">
          <span class="label">Roll</span>
          <div class="roll-face" aria-hidden="true">
            <i class="roll-mark mark-left"></i>
            <i class="roll-mark mark-left-mid"></i>
            <i class="roll-mark mark-center"></i>
            <i class="roll-mark mark-right-mid"></i>
            <i class="roll-mark mark-right"></i>
            <span class="bank-pointer"></span>
            <b id="roll-needle"></b>
          </div>
          <strong id="roll-meter-value">--</strong>
        </div>
      </div>
      <div class="scene-frame">
        <canvas id="scene"></canvas>
        <div class="rc-overlay" aria-label="R8EF receiver channel readings">
          <div class="rc-title">
            <span>R8EF</span>
            <strong>PPM GP15</strong>
          </div>
          <div id="rc-line" class="rc-list">
            <div class="rc-channel rc-vertical" data-channel="3"><span>LSV</span><i><b></b></i><strong>--</strong><em>CH3</em></div>
            <div class="rc-channel rc-vertical" data-channel="2"><span>RSV</span><i><b></b></i><strong>--</strong><em>CH2</em></div>
            <div class="rc-channel" data-channel="4"><span>LSH</span><i><b></b></i><strong>--</strong><em>CH4</em></div>
            <div class="rc-channel" data-channel="1"><span>RSH</span><i><b></b></i><strong>--</strong><em>CH1</em></div>
            <div class="rc-channel" data-channel="7" data-mode="switch"><span>CH7</span><i><b></b></i><strong>--</strong><em>ON/OFF</em></div>
            <div class="rc-channel" data-channel="5" data-mode="three"><span>CH5</span><i><b></b></i><strong>--</strong><em>TOP/MID/BOT</em></div>
            <div class="rc-channel rc-arc rc-arc-left" data-channel="8" data-mode="arc-left"><span>CH8</span><i><b></b></i><strong>--</strong><em>LEFT -> TOP</em></div>
            <div class="rc-channel rc-arc rc-arc-right" data-channel="6" data-mode="arc-right"><span>CH6</span><i><b></b></i><strong>--</strong><em>BOTTOM -> TOP</em></div>
          </div>
        </div>
        <div class="hud hud-top">
          <div>
            <span class="label">Heading</span>
            <strong id="heading">--.- deg</strong>
          </div>
          <div>
            <span class="label">Sensor</span>
            <strong id="sensor">Disconnected</strong>
          </div>
        </div>
        <div class="hud hud-bottom">
          <div><span class="label">Pitch</span><strong id="pitch-value">--</strong></div>
          <div><span class="label">Roll</span><strong id="roll-value">--</strong></div>
          <div><span class="label">Accel Z</span><strong id="z-value">--</strong></div>
          <div><span class="label">Altitude TOF0</span><strong id="altitude">--</strong></div>
        </div>
      </div>
    </section>
    <aside class="panel">
      <div class="brand">
        <div class="mark"></div>
        <div>
          <h1>Pico Flight Sensor Viewer</h1>
          <p id="status">Ready to connect</p>
        </div>
      </div>
      <div class="controls">
        <button id="connect" type="button">Connect Pico</button>
        <button id="disconnect" type="button" disabled>Disconnect</button>
        <div class="calibration-controls">
          <button id="calibrate-pose" type="button" class="secondary">Zero Pose</button>
          <button id="show-orientation-cal" type="button" class="secondary">Map Motion</button>
          <span id="north-offset">Pose offset waiting</span>
        </div>
        <div class="utility-actions">
          <button id="show-raw" type="button" class="secondary">Raw Data</button>
          <button id="show-wiring" type="button" class="secondary">Wiring</button>
        </div>
        <label class="toggle">
          <input id="demo" type="checkbox" />
          <span>Demo magnetic field</span>
        </label>
      </div>
      <div class="readout compact-readout">
        <div>
          <span>Magnetic field</span>
          <code id="field-line">--</code>
        </div>
        <div>
          <span>ADXL345 attitude</span>
          <code id="attitude-line">--</code>
        </div>
        <div>
          <span>Distance sensors</span>
          <p class="range-guide">VL53L0X: best 50-1000 mm, extended 1000-2000 mm.</p>
          <div id="range-line" class="range-grid">
            <div data-tof="0"><span>TOF0</span><strong>--</strong><em>waiting</em></div>
            <div data-tof="1"><span>Top / TOF1</span><strong>--</strong><em>waiting</em></div>
            <div data-tof="2"><span>Right / TOF2</span><strong>--</strong><em>waiting</em></div>
            <div data-tof="3"><span>Left / TOF3</span><strong>--</strong><em>waiting</em></div>
            <div data-tof="6"><span>Forward TOF5 / CH6</span><strong>--</strong><em>waiting</em></div>
          </div>
        </div>
      </div>
    </aside>
    <dialog id="wiring-dialog" class="modal">
      <div class="modal-card">
        <div class="modal-title">
          <div>
            <span>Wiring diagram</span>
            <strong>Pico -> HW-617 mux</strong>
          </div>
          <button id="close-wiring" type="button" class="icon-button" aria-label="Close wiring diagram">x</button>
        </div>
        <section class="hardware-map" aria-label="Current Pico wiring">
          <div class="section-heading">
            <span>Hardware map</span>
            <strong>Full bench wiring</strong>
          </div>
          <div class="wiring-note">
            <strong>Common rule</strong>
            <span>Every board needs shared GND. Keep R8EF signal direct to Pico GP15; do not route it through the HW-617.</span>
          </div>
          <div class="bus-card">
            <div class="device pico-device">
              <span>Pico</span>
              <strong>GP0 SDA</strong>
              <strong>GP1 SCL</strong>
              <strong>3V3</strong>
              <strong>GND</strong>
            </div>
            <div class="wire-stack" aria-hidden="true">
              <i></i><i></i><i></i><i></i>
            </div>
            <div class="device mux-device">
              <span>HW-617 / TCA9548A</span>
              <strong>SDA</strong>
              <strong>SCL</strong>
              <strong>VCC</strong>
              <strong>GND</strong>
            </div>
          </div>
          <div class="direct-grid">
            <div class="direct-card">
              <span>Receiver direct input</span>
              <strong>R8EF CH2 signal -> Pico GP15</strong>
              <em>R8EF VCC -> Pico 3V3, R8EF GND -> Pico GND</em>
            </div>
            <div class="direct-card">
              <span>R8EF mode</span>
              <strong>Blue/purple LED = SBUS/PPM</strong>
              <em>Double-press ID SET within 1 second to toggle mode</em>
            </div>
          </div>
          <div class="mux-grid">
            <div><span>HW-617 CH0</span><strong>UL53LDK #0</strong><em>VIN/VCC, GND, SC0, SD0</em></div>
            <div><span>HW-617 CH1</span><strong>UL53LDK #1</strong><em>VIN/VCC, GND, SC1, SD1</em></div>
            <div><span>HW-617 CH2</span><strong>UL53LDK #2</strong><em>VIN/VCC, GND, SC2, SD2</em></div>
            <div><span>HW-617 CH3</span><strong>UL53LDK #3</strong><em>VIN/VCC, GND, SC3, SD3</em></div>
            <div class="mag-channel"><span>HW-617 CH4</span><strong>GY-271 compass</strong><em>VCC, GND, SC4/SCL, SD4/SDA</em></div>
            <div class="mag-channel"><span>HW-617 CH5</span><strong>ADXL345 accelerometer</strong><em>VCC, GND, SC5/SCL, SD5/SDA</em></div>
            <div><span>HW-617 CH6</span><strong>Forward TOF5</strong><em>VIN/VCC, GND, SC6/SCL, SD6/SDA</em></div>
          </div>
        </section>
      </div>
    </dialog>
    <dialog id="raw-dialog" class="modal">
      <div class="modal-card">
        <div class="modal-title">
          <div>
            <span>Debug stream</span>
            <strong>Pico serial data</strong>
          </div>
          <button id="close-raw" type="button" class="icon-button" aria-label="Close raw data">x</button>
        </div>
      <div class="readout debug-readout">
        <div>
          <span>Raw line</span>
          <code id="raw-line">No serial data yet</code>
        </div>
      </div>
      <textarea id="manual-line" spellcheck="false" rows="4" placeholder="Paste a Pico output line here to test parsing"></textarea>
      <button id="parse-manual" type="button" class="secondary">Parse Line</button>
      </div>
    </dialog>
    <dialog id="orientation-dialog" class="modal">
      <div class="modal-card">
        <div class="modal-title">
          <div>
            <span>Orientation mapping</span>
            <strong>Capture known positions</strong>
          </div>
          <button id="close-orientation-cal" type="button" class="icon-button" aria-label="Close orientation mapping">x</button>
        </div>
        <div class="orientation-map">
          <div class="wiring-note">
            <strong>Live accelerometer</strong>
            <span id="orientation-live">Connect the Pico and hold the frame still.</span>
          </div>
          <div id="orientation-steps" class="orientation-steps">
            <button type="button" data-pose="level">Capture Level Upright</button>
            <button type="button" data-pose="noseUp">Capture Nose Up</button>
            <button type="button" data-pose="noseDown">Capture Nose Down</button>
            <button type="button" data-pose="rightDown">Capture Right Side Down</button>
            <button type="button" data-pose="leftDown">Capture Left Side Down</button>
          </div>
          <code id="orientation-result">No orientation samples captured yet.</code>
          <div class="utility-actions">
            <button id="apply-orientation-cal" type="button">Apply Mapping</button>
            <button id="reset-orientation-cal" type="button" class="secondary">Reset Mapping</button>
          </div>
        </div>
      </div>
    </dialog>
  </main>
`;

const els = {
  canvas: document.querySelector("#scene"),
  heading: document.querySelector("#heading"),
  sensor: document.querySelector("#sensor"),
  status: document.querySelector("#status"),
  pitch: document.querySelector("#pitch-value"),
  roll: document.querySelector("#roll-value"),
  tiltValue: document.querySelector("#tilt-value"),
  tiltDot: document.querySelector("#tilt-dot"),
  pitchMeterValue: document.querySelector("#pitch-meter-value"),
  pitchBar: document.querySelector("#pitch-bar"),
  rollMeterValue: document.querySelector("#roll-meter-value"),
  rollNeedle: document.querySelector("#roll-needle"),
  z: document.querySelector("#z-value"),
  altitude: document.querySelector("#altitude"),
  rawLine: document.querySelector("#raw-line"),
  fieldLine: document.querySelector("#field-line"),
  attitudeLine: document.querySelector("#attitude-line"),
  rangeLine: document.querySelector("#range-line"),
  rcLine: document.querySelector("#rc-line"),
  connect: document.querySelector("#connect"),
  disconnect: document.querySelector("#disconnect"),
  calibratePose: document.querySelector("#calibrate-pose"),
  showOrientationCal: document.querySelector("#show-orientation-cal"),
  closeOrientationCal: document.querySelector("#close-orientation-cal"),
  orientationDialog: document.querySelector("#orientation-dialog"),
  orientationLive: document.querySelector("#orientation-live"),
  orientationSteps: document.querySelector("#orientation-steps"),
  orientationResult: document.querySelector("#orientation-result"),
  applyOrientationCal: document.querySelector("#apply-orientation-cal"),
  resetOrientationCal: document.querySelector("#reset-orientation-cal"),
  showRaw: document.querySelector("#show-raw"),
  closeRaw: document.querySelector("#close-raw"),
  rawDialog: document.querySelector("#raw-dialog"),
  showWiring: document.querySelector("#show-wiring"),
  closeWiring: document.querySelector("#close-wiring"),
  wiringDialog: document.querySelector("#wiring-dialog"),
  northOffset: document.querySelector("#north-offset"),
  demo: document.querySelector("#demo"),
  manualLine: document.querySelector("#manual-line"),
  parseManual: document.querySelector("#parse-manual"),
};

const savedOrientationMap = JSON.parse(localStorage.getItem("adxlOrientationMap") ?? "null");
const savedOrientationSamples = JSON.parse(localStorage.getItem("adxlOrientationSamples") ?? "{}");
const activeOrientationMap =
  isValidOrientationMap(savedOrientationMap) && savedOrientationMap.version === ORIENTATION_MAP_VERSION
    ? savedOrientationMap
    : DEFAULT_ORIENTATION_MAP;

const state = {
  x: 0,
  y: 0,
  z: 0,
  ax: 0,
  ay: 0,
  az: 0,
  pitch: 0,
  roll: 0,
  rawPitch: 0,
  rawRoll: 0,
  heading: 0,
  mappedX: 0,
  mappedY: 0,
  calibratedHeading: 0,
  northOffsetDeg: 0,
  pitchZeroDeg: 0,
  rollZeroDeg: 0,
  autoCalibrated: false,
  orientationMap: activeOrientationMap,
  orientationSamples: savedOrientationSamples && typeof savedOrientationSamples === "object" ? savedOrientationSamples : {},
  sensor: "Disconnected",
  connected: false,
  port: null,
  reader: null,
  keepReading: false,
  lastLine: "",
  targetHeadingQuaternion: new THREE.Quaternion(),
  targetQuaternion: new THREE.Quaternion(),
  fieldVector: new THREE.Vector3(1, 0, 0),
  altitudeMm: null,
  targetAltitudeY: 0,
  obstacleTargets: {
    ground: null,
    top: null,
    right: null,
    left: null,
    forward: null,
  },
  tof: makeEmptyTofReadings(),
  rc: [null, null, null, null, null, null, null, null],
};

const renderer = new THREE.WebGLRenderer({
  canvas: els.canvas,
  antialias: true,
  alpha: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x11151a);

const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
camera.position.set(0, 3.6, 8.4);
camera.lookAt(0, 0, 0);

const hemi = new THREE.HemisphereLight(0xaec9ff, 0x1d2026, 2.7);
scene.add(hemi);

const key = new THREE.DirectionalLight(0xffffff, 2.2);
key.position.set(4, 7, 6);
key.castShadow = true;
scene.add(key);

const grid = new THREE.GridHelper(22, 22, 0x334150, 0x25313c);
grid.position.y = -1.2;
grid.visible = false;
scene.add(grid);

const compass = makeCompassRose();
compass.position.y = -0.08;
scene.add(compass);

const horizon = new THREE.Mesh(
  new THREE.PlaneGeometry(80, 24),
  new THREE.MeshBasicMaterial({
    color: 0x19202a,
    transparent: true,
    opacity: 0.55,
    side: THREE.DoubleSide,
  }),
);
horizon.position.set(0, -1.25, -18);
horizon.visible = false;
scene.add(horizon);

const planeRig = makePlaneRig();
scene.add(planeRig);

function makePlaneRig() {
  const group = new THREE.Group();
  const plane = makePlane();
  plane.scale.setScalar(0.2);
  group.add(plane);
  group.userData.plane = plane;

  const altitudeLine = new THREE.Mesh(
    new THREE.CylinderGeometry(0.018, 0.018, 1, 12),
    new THREE.MeshBasicMaterial({ color: 0xffd166, transparent: true, opacity: 0.9 }),
  );
  altitudeLine.position.y = -0.6;
  group.add(altitudeLine);
  group.userData.altitudeLine = altitudeLine;

  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(1.4, 48),
    new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28 }),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -1.17;
  group.add(shadow);
  group.userData.shadow = shadow;

  const obstacles = {
    ground: makeTofBoundary(0xffd166, "Ground / TOF0"),
    top: makeTofBoundary(0xffd166, "Ceiling / TOF1"),
    right: makeTofBoundary(0x7bc7ff, "Right wall / TOF2"),
    left: makeTofBoundary(0xff8b90, "Left wall / TOF3"),
    forward: makeTofBoundary(0x2fd39e, "Forward TOF5 / CH6"),
  };
  for (const obstacle of Object.values(obstacles)) {
    group.add(obstacle);
  }
  group.userData.obstacles = obstacles;

  return group;
}

function makeTofBoundary(color, labelText) {
  const group = new THREE.Group();
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.16,
    depthWrite: false,
  });
  const edgeMaterial = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.82,
  });
  const box = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)), edgeMaterial);
  const connector = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(1, 0, 0)]),
    edgeMaterial,
  );
  const label = makeBillboardLabel(labelText, color, 0.55);

  group.add(box);
  group.add(edges);
  group.add(connector);
  group.add(label);
  group.visible = false;
  group.userData.box = box;
  group.userData.edges = edges;
  group.userData.connector = connector;
  group.userData.label = label;
  return group;
}

function makeSensorRig() {
  const group = new THREE.Group();
  const board = makeGy271Board();
  board.scale.setScalar(2.2);
  board.position.y = -0.38;
  group.add(board);
  group.userData.board = board;

  const fieldArrow = makeVectorArrow(0xffd166, "Magnetic field");
  fieldArrow.position.set(0, 0.05, 0);
  group.add(fieldArrow);
  group.userData.fieldArrow = fieldArrow;

  const horizontalArrow = makeVectorArrow(0xf1f5f9, "Horizontal heading");
  horizontalArrow.position.set(0, -0.7, 0);
  group.add(horizontalArrow);
  group.userData.horizontalArrow = horizontalArrow;

  return group;
}

function makeVectorArrow(color, labelText) {
  const group = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color });
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 1, 16), mat);
  const cone = new THREE.Mesh(new THREE.ConeGeometry(0.095, 0.26, 24), mat);
  const label = makeBillboardLabel(labelText, color, 0.72);

  shaft.position.y = 0.5;
  cone.position.y = 1.13;
  label.position.y = 1.42;

  group.add(shaft);
  group.add(cone);
  group.add(label);
  group.userData.shaft = shaft;
  group.userData.cone = cone;
  group.userData.label = label;
  return group;
}

function setArrowVector(arrow, vector, length = 2.4) {
  const safe = vector.lengthSq() > 0.0001 ? vector.clone().normalize() : new THREE.Vector3(1, 0, 0);
  const scaledLength = length;
  const shaftLength = Math.max(0.25, scaledLength - 0.28);

  arrow.userData.shaft.scale.y = shaftLength;
  arrow.userData.shaft.position.y = shaftLength / 2;
  arrow.userData.cone.position.y = shaftLength + 0.13;
  arrow.userData.label.position.y = shaftLength + 0.48;

  const quaternion = new THREE.Quaternion();
  quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), safe);
  arrow.quaternion.copy(quaternion);
}

function makePlane() {
  const group = new THREE.Group();
  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0xdce8f2,
    metalness: 0.22,
    roughness: 0.32,
  });
  const accentMat = new THREE.MeshStandardMaterial({
    color: 0x2fd39e,
    metalness: 0.14,
    roughness: 0.45,
  });
  const glassMat = new THREE.MeshStandardMaterial({
    color: 0x7bc7ff,
    metalness: 0.05,
    roughness: 0.1,
    transparent: true,
    opacity: 0.7,
  });

  const fuselage = new THREE.Mesh(new THREE.CapsuleGeometry(0.38, 2.7, 12, 28), bodyMat);
  fuselage.rotation.z = Math.PI / 2;
  fuselage.castShadow = true;
  group.add(fuselage);

  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.4, 0.9, 32), accentMat);
  nose.rotation.z = -Math.PI / 2;
  nose.position.x = 1.82;
  nose.castShadow = true;
  group.add(nose);

  const canopy = new THREE.Mesh(new THREE.SphereGeometry(0.38, 24, 12), glassMat);
  canopy.scale.set(1.1, 0.42, 0.8);
  canopy.position.set(0.42, 0.38, 0);
  canopy.castShadow = true;
  group.add(canopy);

  const wingShape = new THREE.Shape();
  wingShape.moveTo(-0.55, 0);
  wingShape.lineTo(0.2, 0.18);
  wingShape.lineTo(1.0, 2.95);
  wingShape.lineTo(-1.0, 2.95);
  wingShape.lineTo(-0.32, 0.12);
  wingShape.lineTo(-0.55, 0);
  const wingGeo = new THREE.ShapeGeometry(wingShape);

  const leftWing = new THREE.Mesh(wingGeo, accentMat);
  leftWing.rotation.x = Math.PI / 2;
  leftWing.position.set(0.02, -0.05, 0.05);
  leftWing.castShadow = true;
  group.add(leftWing);

  const rightWing = leftWing.clone();
  rightWing.scale.y = -1;
  group.add(rightWing);

  const tailWing = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 1.55), accentMat);
  tailWing.position.set(-1.35, 0.04, 0);
  tailWing.castShadow = true;
  group.add(tailWing);

  const fin = new THREE.Mesh(new THREE.ConeGeometry(0.36, 0.9, 4), accentMat);
  fin.rotation.y = Math.PI / 4;
  fin.scale.set(0.75, 1, 0.45);
  fin.position.set(-1.45, 0.55, 0);
  fin.castShadow = true;
  group.add(fin);

  const prop = new THREE.Mesh(new THREE.BoxGeometry(0.04, 1.45, 0.08), new THREE.MeshStandardMaterial({ color: 0x11151a }));
  prop.position.x = 2.35;
  group.add(prop);
  group.userData.prop = prop;

  const axes = makePlaneAxes();
  axes.position.set(0.05, 0.92, 0);
  group.add(axes);

  group.rotation.y = Math.PI;
  return group;
}

function makePlaneAxes() {
  const group = new THREE.Group();
  const axes = [
    {
      label: "Nose +X",
      color: 0xff5a5f,
      direction: new THREE.Vector3(1, 0, 0),
      position: new THREE.Vector3(1.05, 0, 0),
      labelPosition: new THREE.Vector3(1.75, 0.06, 0),
    },
    {
      label: "Right +Y",
      color: 0x7bc7ff,
      direction: new THREE.Vector3(0, 0, 1),
      position: new THREE.Vector3(0, 0, 0.72),
      labelPosition: new THREE.Vector3(0, 0.06, 1.34),
    },
    {
      label: "Up +Z",
      color: 0x2fd39e,
      direction: new THREE.Vector3(0, 1, 0),
      position: new THREE.Vector3(0, 0.58, 0),
      labelPosition: new THREE.Vector3(0, 1.12, 0),
    },
  ];

  for (const axis of axes) {
    const axisGroup = new THREE.Group();
    const material = new THREE.MeshBasicMaterial({ color: axis.color });
    const length = axis.direction.length();
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, length, 12), material);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.2, 18), material);

    shaft.position.copy(axis.direction.clone().multiplyScalar(0.5));
    cone.position.copy(axis.position);

    const quaternion = new THREE.Quaternion();
    quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), axis.direction.clone().normalize());
    shaft.quaternion.copy(quaternion);
    cone.quaternion.copy(quaternion);

    axisGroup.add(shaft);
    axisGroup.add(cone);

    const label = makeBillboardLabel(axis.label, axis.color, 0.52);
    label.position.copy(axis.labelPosition);
    axisGroup.add(label);

    group.add(axisGroup);
  }

  return group;
}

function makeBillboardLabel(text, color, width = 0.6) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 160;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(12, 16, 21, 0.72)";
  ctx.strokeStyle = `#${color.toString(16).padStart(6, "0")}`;
  ctx.lineWidth = 8;
  roundRect(ctx, 18, 24, 476, 112, 18);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "800 46px system-ui, sans-serif";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(width * 2.2, width * 0.68, 1);
  return sprite;
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

function makeGy271Board() {
  const group = new THREE.Group();
  const boardMat = new THREE.MeshStandardMaterial({
    color: 0x127a59,
    metalness: 0.05,
    roughness: 0.58,
  });
  const copperMat = new THREE.MeshStandardMaterial({
    color: 0xd8a63c,
    metalness: 0.55,
    roughness: 0.35,
  });
  const chipMat = new THREE.MeshStandardMaterial({
    color: 0x11151a,
    metalness: 0.08,
    roughness: 0.5,
  });
  const silkMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    map: makeBoardTexture(),
  });
  const arrowMat = new THREE.MeshBasicMaterial({ color: 0x2fd39e });
  const yArrowMat = new THREE.MeshBasicMaterial({ color: 0x7bc7ff });

  const board = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.05, 1.28), boardMat);
  board.castShadow = true;
  group.add(board);

  const silk = new THREE.Mesh(new THREE.PlaneGeometry(0.82, 1.18), silkMat);
  silk.rotation.x = -Math.PI / 2;
  silk.position.y = 0.029;
  group.add(silk);

  const chip = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.055, 0.28), chipMat);
  chip.position.set(0, 0.058, 0.06);
  chip.castShadow = true;
  group.add(chip);

  const header = new THREE.Group();
  for (let i = 0; i < 4; i += 1) {
    const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.24, 12), copperMat);
    pin.rotation.x = Math.PI / 2;
    pin.position.set(-0.34 + i * 0.23, 0.03, 0.78);
    pin.castShadow = true;
    header.add(pin);
  }
  group.add(header);

  const xArrow = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.22, 3), arrowMat);
  xArrow.rotation.z = -Math.PI / 2;
  xArrow.position.set(0.58, 0.1, -0.52);
  group.add(xArrow);

  const xShaft = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.025, 0.025), arrowMat);
  xShaft.position.set(0.37, 0.1, -0.52);
  group.add(xShaft);

  const yArrow = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.22, 3), yArrowMat);
  yArrow.rotation.x = Math.PI / 2;
  yArrow.position.set(-0.36, 0.1, -0.76);
  group.add(yArrow);

  const yShaft = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.025, 0.36), yArrowMat);
  yShaft.position.set(-0.36, 0.1, -0.58);
  group.add(yShaft);

  return group;
}

function makeCompassRose() {
  const group = new THREE.Group();
  const lineMat = new THREE.LineBasicMaterial({
    color: 0x5f7488,
    transparent: true,
    opacity: 0.9,
  });
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0x2fd39e,
    transparent: true,
    opacity: 0.12,
    side: THREE.DoubleSide,
  });

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(5.35, 5.43, 128),
    ringMat,
  );
  ring.rotation.x = -Math.PI / 2;
  group.add(ring);

  for (let degrees = 0; degrees < 360; degrees += 15) {
    const radians = THREE.MathUtils.degToRad(degrees);
    const isCardinal = degrees % 90 === 0;
    const isOrdinal = degrees % 45 === 0;
    const inner = isCardinal ? 4.55 : isOrdinal ? 4.85 : 5.08;
    const outer = isCardinal ? 5.82 : isOrdinal ? 5.62 : 5.43;
    const points = [
      new THREE.Vector3(Math.sin(radians) * inner, 0, -Math.cos(radians) * inner),
      new THREE.Vector3(Math.sin(radians) * outer, 0, -Math.cos(radians) * outer),
    ];
    group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), lineMat));
  }

  const labels = [
    ["N", 0, 0x2fd39e, 0.88],
    ["E", 90, 0xf1f5f9, 0.72],
    ["S", 180, 0xf1f5f9, 0.72],
    ["W", 270, 0xf1f5f9, 0.72],
    ["NE", 45, 0x9fb0c3, 0.42],
    ["SE", 135, 0x9fb0c3, 0.42],
    ["SW", 225, 0x9fb0c3, 0.42],
    ["NW", 315, 0x9fb0c3, 0.42],
  ];

  for (const [text, degrees, color, size] of labels) {
    const radians = THREE.MathUtils.degToRad(degrees);
    const label = makeGroundLabel(text, color, size);
    label.position.set(Math.sin(radians) * 6.28, 0.015, -Math.cos(radians) * 6.28);
    label.rotation.x = -Math.PI / 2;
    group.add(label);
  }

  const northArrow = new THREE.Mesh(
    new THREE.ConeGeometry(0.22, 0.72, 3),
    new THREE.MeshBasicMaterial({ color: 0x2fd39e }),
  );
  northArrow.rotation.x = -Math.PI / 2;
  northArrow.position.set(0, 0.025, -4.12);
  group.add(northArrow);

  return group;
}

function makeGroundLabel(text, color, size) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = `#${color.toString(16).padStart(6, "0")}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "800 76px system-ui, sans-serif";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(size * 1.45, size * 0.72), material);
  return mesh;
}

function makeBoardTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 768;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "700 54px system-ui, sans-serif";
  ctx.fillText("GY-271", 256, 132);
  ctx.font = "600 32px system-ui, sans-serif";
  ctx.fillText("+X", 408, 500);
  ctx.fillText("+Y", 144, 610);
  ctx.font = "700 24px system-ui, sans-serif";
  ["VCC", "GND", "SCL", "SDA"].forEach((label, index) => {
    ctx.save();
    ctx.translate(95 + index * 106, 704);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(label, 0, 0);
    ctx.restore();
  });
  ctx.strokeStyle = "rgba(255,255,255,0.75)";
  ctx.lineWidth = 8;
  ctx.strokeRect(58, 52, 396, 656);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function resize() {
  const rect = els.canvas.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height, false);
  camera.aspect = rect.width / rect.height;
  camera.updateProjectionMatrix();
}

window.addEventListener("resize", resize);
resize();

function parseSensorLine(line) {
  const match = line.match(
    /sensor=(?<sensor>.*?)\s+x=(?<x>-?\d+(?:\.\d+)?)\s+y=(?<y>-?\d+(?:\.\d+)?)\s+z=(?<z>-?\d+(?:\.\d+)?).*?heading=(?<heading>-?\d+(?:\.\d+)?)/,
  );
  if (!match?.groups) return null;

  return {
    sensor: match.groups.sensor.trim(),
    x: Number(match.groups.x),
    y: Number(match.groups.y),
    z: Number(match.groups.z),
    heading: Number(match.groups.heading),
    tof: parseTofFields(line),
    attitude: parseAttitudeFields(line),
    rc: parseRcFields(line),
    raw: line.trim(),
  };
}

function parseTofFields(line) {
  const distances = makeEmptyTofReadings();
  for (const match of line.matchAll(/tof(\d+)=(\d+|None|err)/g)) {
    const index = Number(match[1]);
    if (TOF_CHANNELS.includes(index)) {
      distances[index] = /^\d+$/.test(match[2]) ? Number(match[2]) : match[2];
    }
  }
  return distances;
}

function parseAttitudeFields(line) {
  const number = "(-?\\d+(?:\\.\\d+)?)";
  const ax = line.match(new RegExp(`\\bax=${number}`));
  const ay = line.match(new RegExp(`\\bay=${number}`));
  const az = line.match(new RegExp(`\\baz=${number}`));
  const pitch = line.match(new RegExp(`\\bpitch=${number}`));
  const roll = line.match(new RegExp(`\\broll=${number}`));
  return {
    ax: ax ? Number(ax[1]) : 0,
    ay: ay ? Number(ay[1]) : 0,
    az: az ? Number(az[1]) : 0,
    pitch: pitch ? Number(pitch[1]) : 0,
    roll: roll ? Number(roll[1]) : 0,
    present: Boolean(ax && ay && az && pitch && roll),
  };
}

function parseRcFields(line) {
  const channels = [null, null, null, null, null, null, null, null];
  for (const match of line.matchAll(/rc([1-8])=(\d+|None|err)/g)) {
    const index = Number(match[1]) - 1;
    channels[index] = /^\d+$/.test(match[2]) ? Number(match[2]) : match[2];
  }
  return channels;
}

function isValidOrientationMap(map) {
  return Boolean(
    map &&
      Array.isArray(map.forward) &&
      Array.isArray(map.right) &&
      Array.isArray(map.level) &&
      map.forward.length === 3 &&
      map.right.length === 3 &&
      map.level.length === 3,
  );
}

function normalizeVector(vector) {
  const length = Math.hypot(vector[0], vector[1], vector[2]);
  if (length < 0.0001) return null;
  return vector.map((value) => value / length);
}

function subtractVectors(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function dotVector(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function calculateMappedAttitude(ax, ay, az) {
  if (!isValidOrientationMap(state.orientationMap)) return null;
  const raw = [ax, ay, az];
  const forward = dotVector(raw, state.orientationMap.forward);
  const right = dotVector(raw, state.orientationMap.right);
  const level = dotVector(raw, state.orientationMap.level);
  return {
    pitch: -THREE.MathUtils.radToDeg(Math.atan2(right, Math.sqrt(forward * forward + level * level))),
    roll: THREE.MathUtils.radToDeg(Math.atan2(forward, Math.abs(level))),
  };
}

function buildOrientationMap(samples) {
  const required = ["level", "noseUp", "noseDown", "rightDown", "leftDown"];
  if (!required.every((key) => Array.isArray(samples[key]))) return null;
  const forward = normalizeVector(subtractVectors(samples.noseUp, samples.noseDown));
  const right = normalizeVector(subtractVectors(samples.rightDown, samples.leftDown));
  const level = normalizeVector(samples.level);
  if (!forward || !right || !level) return null;
  return { version: ORIENTATION_MAP_VERSION, forward, right, level };
}

function saveOrientationCalibration() {
  localStorage.setItem("adxlOrientationSamples", JSON.stringify(state.orientationSamples));
  if (state.orientationMap) {
    localStorage.setItem("adxlOrientationMap", JSON.stringify(state.orientationMap));
  } else {
    localStorage.removeItem("adxlOrientationMap");
  }
}

function updateOrientationLive() {
  if (!els.orientationLive) return;
  els.orientationLive.textContent = `ax=${state.ax.toFixed(3)} ay=${state.ay.toFixed(3)} az=${state.az.toFixed(
    3,
  )} pitch=${state.pitch.toFixed(1)} roll=${state.roll.toFixed(1)}`;
}

function updateOrientationResult() {
  const labels = {
    level: "level",
    noseUp: "nose up",
    noseDown: "nose down",
    rightDown: "right side down",
    leftDown: "left side down",
  };
  const captured = Object.entries(labels)
    .map(([key, label]) => `${label}: ${Array.isArray(state.orientationSamples[key]) ? "captured" : "missing"}`)
    .join("\n");
  const map = buildOrientationMap(state.orientationSamples);
  const mapText = map
    ? `\n\nProposed mapping:\nforward=[${map.forward.map((value) => value.toFixed(2)).join(", ")}]\nright=[${map.right
        .map((value) => value.toFixed(2))
        .join(", ")}]\nlevel=[${map.level.map((value) => value.toFixed(2)).join(", ")}]`
    : "\n\nCapture all positions to calculate a mapping.";
  els.orientationResult.textContent = `${captured}${mapText}`;
}

function applyReading(reading) {
  if (!reading) return false;

  state.sensor = reading.sensor;
  state.x = reading.x;
  state.y = reading.y;
  state.z = reading.z;
  const mapped = mapMagnetometerAxes(state.x, state.y);
  state.mappedX = mapped.x;
  state.mappedY = mapped.y;
  state.heading = headingFromAxes(mapped.x, mapped.y);
  state.tof = reading.tof ?? makeEmptyTofReadings();
  state.rc = reading.rc ?? [null, null, null, null, null, null, null, null];
  state.ax = reading.attitude?.ax ?? 0;
  state.ay = reading.attitude?.ay ?? 0;
  state.az = reading.attitude?.az ?? 0;
  const rawPitch = reading.attitude?.pitch ?? 0;
  const rawRoll = reading.attitude?.roll ?? 0;
  state.rawPitch = rawPitch;
  state.rawRoll = rawRoll;
  const mappedAttitude = calculateMappedAttitude(state.ax, state.ay, state.az);
  const displayPitch = mappedAttitude?.pitch ?? rawPitch;
  const displayRoll = mappedAttitude?.roll ?? rawRoll;
  if (!state.autoCalibrated && reading.attitude?.present) {
    calibrateCurrentPose(displayPitch, displayRoll);
  }
  state.calibratedHeading = normalizeDegrees(state.heading + state.northOffsetDeg);
  state.pitch = displayPitch - state.pitchZeroDeg;
  state.roll = normalizeSignedDegrees(displayRoll - state.rollZeroDeg);
  state.altitudeMm = typeof state.tof[0] === "number" ? state.tof[0] : null;
  state.targetAltitudeY = altitudeToSceneY(state.altitudeMm);
  updateObstacleTargets();
  state.lastLine = reading.raw;

  const mag = Math.max(1, Math.hypot(state.mappedX, state.mappedY, state.z));
  state.fieldVector.set(state.mappedX / mag, state.z / mag, state.mappedY / mag);
  updateTargetQuaternion();

  els.sensor.textContent = state.sensor;
  els.heading.textContent = `${state.calibratedHeading.toFixed(1)} deg`;
  els.pitch.textContent = `${state.pitch.toFixed(1)} deg`;
  els.roll.textContent = `${state.roll.toFixed(1)} deg`;
  els.z.textContent = `${state.az.toFixed(2)} g`;
  els.altitude.textContent = state.altitudeMm === null ? "--" : `${state.altitudeMm} mm`;
  updateAttitudeMeters();
  els.rawLine.textContent = state.lastLine;
  els.fieldLine.textContent = `|B| ${mag.toFixed(1)} raw units, mapped x=${Math.round(
    state.mappedX,
  )} y=${Math.round(state.mappedY)}`;
  els.attitudeLine.textContent = reading.attitude?.present
    ? `ax=${state.ax.toFixed(2)}g ay=${state.ay.toFixed(2)}g az=${state.az.toFixed(
        2,
      )}g pitch=${state.pitch.toFixed(1)} roll=${state.roll.toFixed(1)}`
    : "ADXL345 not detected";
  if (state.sensor === "Receiver / waiting") {
    els.status.textContent = "Pico is sending data; I2C sensors are not detected";
  } else {
    els.status.textContent = `Reading ${state.sensor}`;
  }
  updateTofReadout();
  updateRcReadout();
  updateOrientationLive();
  return true;
}

function handleDiagnosticLine(line) {
  if (line.includes("I2C bus held low")) {
    els.status.textContent = line;
    els.sensor.textContent = "I2C bus fault";
    return true;
  }
  if (line.includes("No HW-617/TCA9548A detected")) {
    els.status.textContent = "HW-617 mux not detected";
    els.sensor.textContent = "Mux missing";
    return true;
  }
  if (line.includes("Root I2C devices:")) {
    els.status.textContent = line;
    return true;
  }
  return false;
}

function updateAttitudeMeters() {
  const pitch = THREE.MathUtils.clamp(state.pitch, -45, 45);
  const roll = THREE.MathUtils.clamp(state.roll, -60, 60);
  const tiltMagnitude = THREE.MathUtils.clamp(Math.hypot(state.pitch, state.roll), 0, 90);
  const dotX = THREE.MathUtils.clamp(roll / 45, -1, 1) * 38;
  const dotY = THREE.MathUtils.clamp(-pitch / 45, -1, 1) * 38;
  const pitchOffset = THREE.MathUtils.clamp(-pitch / 45, -1, 1) * 36;

  els.tiltDot.style.transform = `translate(calc(-50% + ${dotX.toFixed(1)}px), calc(-50% + ${dotY.toFixed(
    1,
  )}px))`;
  els.pitchBar.style.transform = `translate(-50%, calc(-50% + ${pitchOffset.toFixed(
    1,
  )}px)) rotate(${roll.toFixed(1)}deg)`;
  els.rollNeedle.style.transform = `translateX(-50%) rotate(${roll.toFixed(1)}deg)`;
  els.tiltValue.textContent = `${tiltMagnitude.toFixed(1)} deg`;
  els.pitchMeterValue.textContent = `${state.pitch.toFixed(1)} deg`;
  els.rollMeterValue.textContent = `${state.roll.toFixed(1)} deg`;
}

function mapMagnetometerAxes(rawX, rawY) {
  return { x: rawX, y: rawY };
}

function headingFromAxes(x, y) {
  const heading = THREE.MathUtils.radToDeg(Math.atan2(y, x));
  return normalizeDegrees(heading);
}

function altitudeToSceneY(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  return THREE.MathUtils.clamp(value / 240, 0.15, 5.2);
}

function tofToSceneDistance(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return THREE.MathUtils.clamp(value / 220, 0.25, 8);
}

function updateObstacleTargets() {
  state.obstacleTargets.ground = tofToSceneDistance(state.tof[0]);
  state.obstacleTargets.top = tofToSceneDistance(state.tof[1]);
  state.obstacleTargets.right = tofToSceneDistance(state.tof[2]);
  state.obstacleTargets.left = tofToSceneDistance(state.tof[3]);
  state.obstacleTargets.forward = tofToSceneDistance(state.tof[6]);
}

function updateTofReadout() {
  const cells = [...els.rangeLine.querySelectorAll("[data-tof]")];
  for (const cell of cells) {
    const value = state.tof[Number(cell.dataset.tof)];
    const valueEl = cell.querySelector("strong");
    const statusEl = cell.querySelector("em");
    cell.className = "";
    if (value === null || value === undefined) {
      valueEl.textContent = "--";
      statusEl.textContent = "waiting";
    } else if (value === "None") {
      valueEl.textContent = "not found";
      statusEl.textContent = "not detected";
      cell.classList.add("range-missing");
    } else if (value === "err") {
      valueEl.textContent = "error";
      statusEl.textContent = "read failed";
      cell.classList.add("range-error");
    } else {
      valueEl.textContent = `${value} mm`;
      const status = classifyTofRange(value);
      statusEl.textContent = status.label;
      cell.classList.add(status.className);
    }
  }
}

function classifyTofRange(value) {
  if (value < 30) return { label: "too close", className: "range-bad" };
  if (value < 50) return { label: "close edge", className: "range-edge" };
  if (value <= 1000) return { label: "best range", className: "range-good" };
  if (value <= 2000) return { label: "extended/noisy", className: "range-edge" };
  return { label: "out of range", className: "range-bad" };
}

function updateRcReadout() {
  const cells = [...els.rcLine.querySelectorAll(".rc-channel")];
  cells.forEach((cell) => {
    const index = Number(cell.dataset.channel) - 1;
    const value = state.rc[index];
    const bar = cell.querySelector("b");
    const valueEl = cell.querySelector("strong");
    cell.className = "";
    cell.classList.add("rc-channel");
    if (cell.dataset.channel === "2" || cell.dataset.channel === "3") {
      cell.classList.add("rc-vertical");
    }
    if (cell.dataset.mode === "arc-left" || cell.dataset.mode === "arc-right") {
      cell.classList.add("rc-arc");
      cell.classList.add(cell.dataset.mode === "arc-left" ? "rc-arc-left" : "rc-arc-right");
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      const percent = THREE.MathUtils.clamp(((value - 1000) / 1000) * 100, 0, 100);
      if (cell.classList.contains("rc-vertical")) {
        bar.style.width = "100%";
        bar.style.height = `${percent.toFixed(1)}%`;
      } else if (cell.classList.contains("rc-arc")) {
        bar.style.width = "9px";
        bar.style.height = "9px";
        bar.style.setProperty("--rc-dot-x", `${(3 + percent * 0.24).toFixed(1)}px`);
        bar.style.setProperty("--rc-dot-y", `${(25 - percent * 0.22).toFixed(1)}px`);
      } else {
        bar.style.width = `${percent.toFixed(1)}%`;
        bar.style.height = "100%";
      }
      valueEl.textContent = formatRcValue(value, cell.dataset.mode);
      cell.classList.add("rc-active");
      if (value < 900 || value > 2100) {
        cell.classList.add("rc-warn");
      }
    } else {
      bar.style.width = "0%";
      bar.style.height = "0%";
      bar.style.removeProperty("--rc-dot-x");
      bar.style.removeProperty("--rc-dot-y");
      valueEl.textContent = value === "err" ? "err" : "no pulse";
    }
  });
}

function formatRcValue(value, mode) {
  if (mode === "switch") {
    return value >= 1500 ? "ON" : "OFF";
  }
  if (mode === "three") {
    if (value < 1300) return "TOP";
    if (value > 1700) return "BOTTOM";
    return "MIDDLE";
  }
  return `${value} us`;
}

function demoRcChannels(t) {
  return Array.from({ length: 8 }, (_, index) => Math.round(1500 + Math.sin(t * (0.42 + index * 0.08) + index) * 420));
}

function updateTargetQuaternion() {
  const base = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2);
  const pitch = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 0, 1),
    THREE.MathUtils.degToRad(THREE.MathUtils.clamp(state.pitch, -70, 70)),
  );
  const roll = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    THREE.MathUtils.degToRad(THREE.MathUtils.clamp(state.roll, -85, 85)),
  );

  state.targetQuaternion.copy(pitch).multiply(roll).multiply(base);
}

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function normalizeSignedDegrees(value) {
  const normalized = normalizeDegrees(value);
  return normalized > 180 ? normalized - 360 : normalized;
}

function calibrateCurrentPose(rawPitch, rawRoll) {
  state.northOffsetDeg = normalizeDegrees(-state.heading);
  state.pitchZeroDeg = rawPitch;
  state.rollZeroDeg = rawRoll;
  state.autoCalibrated = true;
  updateNorthOffsetLabel();
}

function updateNorthOffsetLabel() {
  els.northOffset.textContent = `Pose zero: heading ${state.northOffsetDeg.toFixed(
    1,
  )} deg, pitch ${state.pitchZeroDeg.toFixed(1)}, roll ${state.rollZeroDeg.toFixed(
    1,
  )}`;
}

async function connectSerial() {
  if (!("serial" in navigator)) {
    els.status.textContent = "Web Serial needs Chrome or Edge over localhost/https";
    return;
  }

  try {
    state.port = await navigator.serial.requestPort({
      filters: [{ usbVendorId: 0x2e8a }],
    });
    await state.port.open({ baudRate: 115200 });
    await state.port.setSignals?.({ dataTerminalReady: true, requestToSend: true });
    state.connected = true;
    state.keepReading = true;
    state.autoCalibrated = false;
    els.status.textContent = "Connected and reading";
    els.connect.disabled = true;
    els.disconnect.disabled = false;
    readSerialLoop();
  } catch (error) {
    els.status.textContent = `Connect failed: ${error.message}`;
  }
}

async function readSerialLoop() {
  const decoder = new TextDecoderStream();
  const closed = state.port.readable.pipeTo(decoder.writable);
  state.reader = decoder.readable.getReader();
  let buffer = "";

  try {
    while (state.keepReading) {
      const { value, done } = await state.reader.read();
      if (done) break;
      buffer += value;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        els.rawLine.textContent = trimmed;
        try {
          const reading = parseSensorLine(line);
          if (reading) {
            applyReading(reading);
          } else if (handleDiagnosticLine(trimmed)) {
            continue;
          } else {
            els.status.textContent = `Serial text: ${trimmed.slice(0, 64)}`;
          }
        } catch (error) {
          els.status.textContent = `Display error: ${error.message}`;
        }
      }
    }
  } catch (error) {
    els.status.textContent = `Read stopped: ${error.message}`;
  } finally {
    state.reader.releaseLock();
    await closed.catch(() => {});
  }
}

async function disconnectSerial() {
  state.keepReading = false;
  if (state.reader) {
    await state.reader.cancel().catch(() => {});
  }
  if (state.port) {
    await state.port.close().catch(() => {});
  }
  state.connected = false;
  state.port = null;
  state.reader = null;
  els.status.textContent = "Disconnected";
  els.sensor.textContent = "Disconnected";
  els.connect.disabled = false;
  els.disconnect.disabled = true;
}

els.connect.addEventListener("click", connectSerial);
els.disconnect.addEventListener("click", disconnectSerial);
els.showRaw.addEventListener("click", () => els.rawDialog.showModal());
els.closeRaw.addEventListener("click", () => els.rawDialog.close());
els.showWiring.addEventListener("click", () => els.wiringDialog.showModal());
els.closeWiring.addEventListener("click", () => els.wiringDialog.close());
els.showOrientationCal.addEventListener("click", () => {
  updateOrientationLive();
  updateOrientationResult();
  els.orientationDialog.showModal();
});
els.closeOrientationCal.addEventListener("click", () => els.orientationDialog.close());
for (const dialog of [els.rawDialog, els.wiringDialog, els.orientationDialog]) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
}
els.orientationSteps.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-pose]");
  if (!button) return;
  state.orientationSamples[button.dataset.pose] = [state.ax, state.ay, state.az];
  saveOrientationCalibration();
  updateOrientationResult();
  els.status.textContent = `Captured ${button.textContent.replace("Capture ", "").toLowerCase()}`;
});
els.applyOrientationCal.addEventListener("click", () => {
  const map = buildOrientationMap(state.orientationSamples);
  if (!map) {
    els.status.textContent = "Capture all orientation positions first";
    updateOrientationResult();
    return;
  }
  state.orientationMap = map;
  state.autoCalibrated = false;
  saveOrientationCalibration();
  updateOrientationResult();
  if (state.lastLine) {
    applyReading(parseSensorLine(state.lastLine));
  }
  els.status.textContent = "Applied ADXL orientation mapping";
});
els.resetOrientationCal.addEventListener("click", () => {
  state.orientationMap = DEFAULT_ORIENTATION_MAP;
  state.orientationSamples = {};
  state.autoCalibrated = false;
  saveOrientationCalibration();
  localStorage.removeItem("adxlOrientationSamples");
  updateOrientationResult();
  if (state.lastLine) {
    applyReading(parseSensorLine(state.lastLine));
  }
  els.status.textContent = "Reset ADXL orientation mapping";
});
els.calibratePose.addEventListener("click", () => {
  calibrateCurrentPose(state.pitch + state.pitchZeroDeg, state.roll + state.rollZeroDeg);
  updateNorthOffsetLabel();
  if (state.lastLine) {
    applyReading(parseSensorLine(state.lastLine));
  }
  els.status.textContent = "Calibrated current pose";
});
els.parseManual.addEventListener("click", () => {
  const line = els.manualLine.value.trim();
  els.demo.checked = false;
  if (!applyReading(parseSensorLine(line))) {
    els.status.textContent = "That line did not match the Pico output format";
  } else {
    els.status.textContent = "Parsed manual sensor line";
  }
});

function runDemo(time) {
  const t = time * 0.001;
  const heading = (t * 28) % 360;
  applyReading({
    sensor: "Demo motion",
    x: Math.cos(t) * 420,
    y: Math.sin(t * 0.8) * 260,
    z: Math.sin(t * 0.6) * 180,
    heading,
    attitude: {
      ax: Math.sin(t * 0.65) * 0.45,
      ay: Math.sin(t * 0.9) * 0.5,
      az: 0.92,
      pitch: Math.sin(t * 0.65) * 22,
      roll: Math.sin(t * 0.9) * 38,
      present: true,
    },
    tof: [
      Math.round(420 + Math.sin(t) * 170),
      Math.round(520 + Math.sin(t * 0.7 + 1) * 140),
      Math.round(650 + Math.sin(t * 0.9 + 2) * 210),
      Math.round(780 + Math.sin(t * 0.4 + 3) * 260),
      null,
      null,
      Math.round(700 + Math.sin(t * 0.8 + 4) * 240),
    ],
    rc: demoRcChannels(t),
    raw: `sensor=Demo motion x=${Math.round(Math.cos(t) * 420)} y=${Math.round(
      Math.sin(t * 0.8) * 260,
    )} z=${Math.round(Math.sin(t * 0.6) * 180)} heading=${heading.toFixed(1)} tof0=${Math.round(
      420 + Math.sin(t) * 170,
    )} tof1=${Math.round(520 + Math.sin(t * 0.7 + 1) * 140)} tof2=${Math.round(
      650 + Math.sin(t * 0.9 + 2) * 210,
    )} tof3=${Math.round(780 + Math.sin(t * 0.4 + 3) * 260)} tof6=${Math.round(
      700 + Math.sin(t * 0.8 + 4) * 240,
    )} ax=${(
      Math.sin(t * 0.65) * 0.45
    ).toFixed(3)} ay=${(Math.sin(t * 0.9) * 0.5).toFixed(3)} az=0.920 pitch=${(
      Math.sin(t * 0.65) * 22
    ).toFixed(1)} roll=${(Math.sin(t * 0.9) * 38).toFixed(1)} ${demoRcChannels(t)
      .map((value, index) => `rc${index + 1}=${value}`)
      .join(" ")}`,
  });
}

function animate(time = 0) {
  if (els.demo.checked && !state.connected) runDemo(time);

  planeRig.userData.plane.quaternion.slerp(state.targetQuaternion, 0.08);
  planeRig.userData.plane.position.y = THREE.MathUtils.lerp(planeRig.userData.plane.position.y, 0, 0.08);
  planeRig.userData.plane.userData.prop.rotation.x += 0.55;

  compass.rotation.y = THREE.MathUtils.lerp(
    compass.rotation.y,
    THREE.MathUtils.degToRad(state.calibratedHeading),
    0.08,
  );

  planeRig.userData.altitudeLine.visible = state.obstacleTargets.ground !== null;
  const groundDistance = state.obstacleTargets.ground ?? 0;
  const altitudeHeight = Math.max(0.05, groundDistance);
  planeRig.userData.altitudeLine.scale.y = altitudeHeight;
  planeRig.userData.altitudeLine.position.y = -altitudeHeight / 2;
  const shadowScale = THREE.MathUtils.mapLinear(groundDistance, 0.25, 8, 1.1, 0.35);
  planeRig.userData.shadow.position.y = -groundDistance;
  planeRig.userData.shadow.visible = state.obstacleTargets.ground !== null;
  planeRig.userData.shadow.scale.setScalar(THREE.MathUtils.clamp(shadowScale, 0.25, 1.2));

  updateTofBoundary(
    planeRig.userData.obstacles.ground,
    state.obstacleTargets.ground,
    new THREE.Vector3(0, -1, 0),
    new THREE.Vector3(7, 0.08, 7),
  );
  updateTofBoundary(
    planeRig.userData.obstacles.top,
    state.obstacleTargets.top,
    new THREE.Vector3(0, 1, 0),
    new THREE.Vector3(7, 0.08, 7),
  );
  updateTofBoundary(
    planeRig.userData.obstacles.right,
    state.obstacleTargets.right,
    new THREE.Vector3(1, 0, 0),
    new THREE.Vector3(0.08, 3.5, 7),
  );
  updateTofBoundary(
    planeRig.userData.obstacles.left,
    state.obstacleTargets.left,
    new THREE.Vector3(-1, 0, 0),
    new THREE.Vector3(0.08, 3.5, 7),
  );
  updateTofBoundary(
    planeRig.userData.obstacles.forward,
    state.obstacleTargets.forward,
    new THREE.Vector3(0, 0, -1),
    new THREE.Vector3(5.4, 3.5, 0.08),
  );

  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

function updateTofBoundary(boundary, distance, direction, scale) {
  if (distance === null) {
    boundary.visible = false;
    return;
  }

  const origin = planeRig.userData.plane.position.clone();
  const offset = direction.clone().multiplyScalar(distance);
  const position = origin.clone().add(offset);
  boundary.visible = true;
  boundary.position.lerp(position, 0.14);
  boundary.userData.box.scale.copy(scale);
  boundary.userData.edges.scale.copy(scale);
  boundary.userData.label.position.copy(direction.clone().multiplyScalar(0.38));

  const localOrigin = boundary.worldToLocal(origin.clone());
  const localEnd = new THREE.Vector3(0, 0, 0);
  boundary.userData.connector.geometry.setFromPoints([localOrigin, localEnd]);
}

updateTargetQuaternion();
updateNorthOffsetLabel();
updateAttitudeMeters();
updateRcReadout();
updateOrientationResult();
planeRig.userData.plane.quaternion.copy(state.targetQuaternion);
animate();
