const motionQuery = "(prefers-reduced-motion: reduce)";
const modelRequests = new Map();

function loadModelBytes(url) {
  if (!modelRequests.has(url)) {
    const request = fetch(url)
      .then(response => {
        if (!response.ok) throw new Error("Could not load the guide model");
        return response.arrayBuffer();
      })
      .catch(error => {
        modelRequests.delete(url);
        throw error;
      });
    modelRequests.set(url, request);
  }
  return modelRequests.get(url);
}

export function mountGuide(host, { guide, products, itemHref }) {
  if (!products.length) return () => {};
  const section = document.createElement("section");
  section.className = "project-guide";
  section.setAttribute("aria-label", guide.label);
  section.innerHTML = `
    <div class="guide-stage">
      <button class="guide-cat" type="button">
        <span class="guide-halo" aria-hidden="true"></span>
        <span class="guide-shadow" aria-hidden="true"></span>
        <img class="guide-poster" alt="" draggable="false">
        <canvas class="guide-canvas" aria-hidden="true"></canvas>
      </button>
      <div class="guide-toolbar">
        <button class="guide-fetch" type="button"><span></span><span class="guide-fetch-icon" aria-hidden="true">↻</span></button>
      </div>
    </div>
    <div class="guide-project" aria-live="polite" aria-atomic="true">
      <div class="guide-project-heading">
        <h2></h2>
        <a class="guide-link"><span></span><span aria-hidden="true">↗</span></a>
      </div>
      <p></p>
    </div>
  `;
  host.replaceChildren(section);

  const stage = section.querySelector(".guide-cat");
  const poster = section.querySelector(".guide-poster");
  const canvas = section.querySelector(".guide-canvas");
  const shadow = section.querySelector(".guide-shadow");
  const fetchButton = section.querySelector(".guide-fetch");
  const fetchText = fetchButton.firstElementChild;
  const projectCard = section.querySelector(".guide-project");
  const title = projectCard.querySelector("h2");
  const summary = projectCard.querySelector("p");
  const link = section.querySelector(".guide-link");
  const preference = matchMedia(motionQuery);
  const listeners = new AbortController();
  const { signal } = listeners;
  let activeScene;
  let sceneContext;
  let selected = 0;
  let pending = null;
  let cardAnimation;

  if (guide.poster) poster.src = guide.poster;
  stage.setAttribute("aria-label", guide.fetchLabel);
  stage.tabIndex = -1;
  fetchText.textContent = guide.fetchLabel;
  link.firstElementChild.textContent = guide.projectLabel;
  stage.disabled = products.length < 2;
  fetchButton.hidden = products.length < 2;

  function showProject() {
    const product = products[selected];
    title.textContent = product.title;
    summary.textContent = product.summary || product.subtitle;
    link.href = itemHref(product.id);
    link.setAttribute("aria-label", `${guide.projectLabel} — ${product.title}`);
  }

  function handoffProject(animateCard = false) {
    if (pending === null || selected === pending) return;
    selected = pending;
    showProject();
    if (animateCard) {
      cardAnimation?.cancel();
      cardAnimation = projectCard.animate([
        { transform: "translateY(5px)", opacity: .74 },
        { transform: "translateY(0)", opacity: 1 }
      ], { duration: 240, easing: "ease-out" });
    }
  }

  function finishFetch() {
    if (pending === null) return;
    handoffProject();
    pending = null;
    stage.removeAttribute("aria-disabled");
    fetchButton.removeAttribute("aria-disabled");
    fetchText.textContent = guide.fetchLabel;
  }

  function fetchProject() {
    if (pending !== null || products.length < 2) return;
    pending = (selected + 1) % products.length;
    if (preference.matches || document.hidden || !activeScene?.available()) {
      finishFetch();
      return;
    }

    stage.setAttribute("aria-disabled", "true");
    fetchButton.setAttribute("aria-disabled", "true");
    fetchText.textContent = guide.fetchingLabel || guide.fetchLabel;
    activeScene.fetch(() => handoffProject(true), finishFetch);
  }

  showProject();
  stage.addEventListener("click", fetchProject, { signal });
  fetchButton.addEventListener("click", fetchProject, { signal });
  preference.addEventListener("change", event => {
    if (event.matches) cardAnimation?.cancel();
  }, { signal });

  async function enableScene() {
    try {
      const contextOptions = { alpha: true, antialias: true, powerPreference: "low-power" };
      sceneContext = canvas.getContext("webgl2", contextOptions);
      if (!sceneContext) return;
      const src = new URL(guide.src, document.baseURI);
      const [THREE, { GLTFLoader }, bytes] = await Promise.all([
        import("three"),
        import("./assets/vendor/GLTFLoader.js"),
        loadModelBytes(src.href)
      ]);
      if (signal.aborted) return;
      const gltf = await new GLTFLoader().parseAsync(bytes, new URL(".", src).href);
      if (signal.aborted) {
        disposeModel(gltf.scene);
        return;
      }
      try {
        activeScene = createScene(THREE, gltf, {
          stage, canvas, shadow, context: sceneContext, preference, signal, onInterrupt: finishFetch
        });
      } catch (error) {
        disposeModel(gltf.scene);
        throw error;
      }
    } catch {
      stage.classList.remove("is-live");
      releaseUnusedContext();
    }
  }

  function releaseUnusedContext() {
    if (!activeScene && sceneContext) {
      sceneContext.getExtension("WEBGL_lose_context")?.loseContext();
      sceneContext = undefined;
    }
  }

  if (guide.src) enableScene();
  return () => {
    listeners.abort();
    cardAnimation?.cancel();
    activeScene?.dispose();
    releaseUnusedContext();
    section.remove();
  };
}

function disposeModel(model) {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  model.traverse(node => {
    if (!node.isMesh) return;
    geometries.add(node.geometry);
    for (const material of [].concat(node.material)) materials.add(material);
  });
  for (const material of materials) {
    for (const value of Object.values(material)) {
      if (value?.isTexture) textures.add(value);
    }
    material.dispose();
  }
  for (const texture of textures) {
    texture.source.data?.close?.();
    texture.dispose();
  }
  for (const geometry of geometries) geometry.dispose();
}

function createScene(THREE, gltf, { stage, canvas, shadow, context, preference, signal, onInterrupt }) {
  const renderer = new THREE.WebGLRenderer({ canvas, context });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;

  const scene = new THREE.Scene();
  const model = gltf.scene;
  scene.add(model, new THREE.HemisphereLight(0xfff4e7, 0xa49082, 2.3));
  const key = new THREE.DirectionalLight(0xffe5ce, 3.1);
  key.position.set(-4, 7, 6);
  const fill = new THREE.DirectionalLight(0xffffff, 1.2);
  fill.position.set(5, 2, 1);
  const rim = new THREE.DirectionalLight(0xffd5b1, 1.65);
  rim.position.set(3, 5, -6);
  scene.add(key, fill, rim);

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 100);
  const cameraPosition = new THREE.Vector3(2.85, 3.25, 9.45);
  camera.position.copy(cameraPosition);
  camera.lookAt(.05, 1.32, 0);
  const cameraRight = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
  const cameraUp = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);

  const head = model.getObjectByName("HeadPivot");
  const headRest = head?.quaternion.clone();
  const lookRotation = new THREE.Euler(0, 0, 0, "YXZ");
  const lookQuaternion = new THREE.Quaternion();
  const root = model.getObjectByName("FetchRoot");
  const clip = gltf.animations.find(animation => animation.name === "Fetch" && animation.duration > 0);
  const mixer = new THREE.AnimationMixer(model);
  const action = clip && mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1);
  const handoff = root?.userData.fetchHandoffSeconds;
  const handoffTime = clip && (Number.isFinite(handoff) && handoff > 0 && handoff < clip.duration
    ? handoff : clip.duration * .886);

  if (action) {
    action.clampWhenFinished = true;
    action.play();
    mixer.update(0);
  }

  const rootRest = root?.getWorldPosition(new THREE.Vector3());
  const rootPosition = new THREE.Vector3();
  const ground = new THREE.Vector3();
  const groundRest = new THREE.Vector3();
  const { clamp, smoothstep } = THREE.MathUtils;
  let frame = 0;
  let lost = context.isContextLost();
  let inView = true;
  let width = 0;
  let height = 0;
  let fetchState;
  let pointer;
  let yaw = 0;
  let pitch = 0;
  let lastLook = 0;

  function canRender() {
    return width > 0 && height > 0 && inView && !document.hidden && !lost && !signal.aborted;
  }

  function frameCamera() {
    let pan = 0;
    let travel = 0;
    if (root) {
      root.getWorldPosition(rootPosition);
      ground.subVectors(rootPosition, rootRest);
      pan = ground.dot(cameraRight) * .57;
      travel = smoothstep(Math.hypot(ground.x, ground.z), .14, 1.45);
    }
    const lift = .46 * travel;
    camera.position.copy(cameraPosition).addScaledVector(cameraRight, pan).addScaledVector(cameraUp, -lift);
    const halfHeight = 1.71 + .33 * travel;
    const halfWidth = halfHeight * width / height;
    camera.left = -halfWidth;
    camera.right = halfWidth;
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
    if (root) {
      ground.set(rootPosition.x, rootRest.y, rootPosition.z).project(camera);
      groundRest.copy(rootRest).project(camera);
      const x = (ground.x - groundRest.x) * width / 2 - pan * width / (halfWidth * 2);
      const y = (groundRest.y - ground.y - lift / halfHeight) * height / 2;
      shadow.style.transform = `translate(${x}px, ${y}px) scale(${1.71 / halfHeight})`;
    }
  }

  function render() {
    if (!canRender()) return;
    frameCamera();
    renderer.render(scene, camera);
    if (!stage.classList.contains("is-live")) stage.classList.add("is-live");
  }

  function resize() {
    if (signal.aborted) return;
    const bounds = stage.getBoundingClientRect();
    width = bounds.width;
    height = bounds.height;
    if (width && height && !lost) renderer.setSize(width, height, false);
    render();
  }

  function queueFrame() {
    if (!frame && canRender()) frame = requestAnimationFrame(step);
  }

  function aimHead() {
    if (!head) return;
    lookRotation.set(pitch, yaw, 0);
    head.quaternion.copy(headRest).multiply(lookQuaternion.setFromEuler(lookRotation));
  }

  function resetPose() {
    if (action) {
      action.reset();
      mixer.update(0);
    }
    yaw = 0;
    pitch = 0;
    lastLook = 0;
    aimHead();
  }

  function interrupt() {
    cancelAnimationFrame(frame);
    frame = 0;
    if (fetchState) {
      fetchState = undefined;
      onInterrupt();
    }
    resetPose();
    shadow.style.transform = "";
    render();
  }

  function stepLook(now) {
    if (!head || preference.matches) return;
    let targetYaw = 0;
    let targetPitch = 0;
    if (pointer) {
      const bounds = stage.getBoundingClientRect();
      targetYaw = .23 * clamp((pointer.x - bounds.left - width * .5) / (width * .65), -1, 1);
      targetPitch = .15 * clamp((pointer.y - bounds.top - height * .38) / (height * .72), -1, 1);
    }
    const blend = 1 - Math.exp(-Math.min(now - (lastLook || now - 16), 48) / 105);
    const nextYaw = THREE.MathUtils.lerp(yaw, targetYaw, blend);
    const nextPitch = THREE.MathUtils.lerp(pitch, targetPitch, blend);
    const moving = Math.abs(nextYaw - targetYaw) > .001 || Math.abs(nextPitch - targetPitch) > .001;
    yaw = moving ? nextYaw : targetYaw;
    pitch = moving ? nextPitch : targetPitch;
    lastLook = moving ? now : 0;
    aimHead();
    render();
    if (moving) queueFrame();
  }

  function step(now) {
    frame = 0;
    if (!canRender()) return;
    if (!fetchState) {
      stepLook(now);
      return;
    }

    const current = fetchState;
    const time = clamp((now - current.start) / 1000, 0, clip.duration);
    action.time = time;
    mixer.update(0);
    if (now - current.start < 160) {
      const resting = 1 - smoothstep(now - current.start, 0, 160);
      yaw = current.yaw * resting;
      pitch = current.pitch * resting;
    } else {
      yaw = 0;
      pitch = 0;
    }
    aimHead();
    render();
    if (!current.delivered && time >= handoffTime) {
      current.delivered = true;
      current.onHandoff();
    }
    if (time < clip.duration) {
      queueFrame();
      return;
    }

    fetchState = undefined;
    lastLook = 0;
    current.onComplete();
    if (pointer) queueFrame();
  }

  function clearPointer() {
    pointer = undefined;
    if (!fetchState && (yaw || pitch)) queueFrame();
  }

  window.addEventListener("pointermove", event => {
    if (event.pointerType !== "mouse" || !head || preference.matches || !canRender()) return;
    pointer = { x: event.clientX, y: event.clientY };
    if (!fetchState) queueFrame();
  }, { passive: true, signal });
  window.addEventListener("pointerout", event => {
    if (!event.relatedTarget) clearPointer();
  }, { signal });
  window.addEventListener("pointercancel", clearPointer, { signal });
  window.addEventListener("blur", clearPointer, { signal });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clearPointer();
      interrupt();
    } else {
      render();
    }
  }, { signal });
  preference.addEventListener("change", event => {
    if (event.matches) {
      clearPointer();
      interrupt();
    }
  }, { signal });
  canvas.addEventListener("webglcontextlost", event => {
    event.preventDefault();
    lost = true;
    stage.classList.remove("is-live");
    clearPointer();
    interrupt();
  }, { signal });
  canvas.addEventListener("webglcontextrestored", () => {
    lost = false;
    resize();
  }, { signal });

  const observer = new ResizeObserver(resize);
  observer.observe(stage);
  const visibility = new IntersectionObserver(([entry]) => {
    inView = entry.isIntersecting;
    if (!inView) {
      clearPointer();
      interrupt();
    } else {
      render();
    }
  });
  visibility.observe(stage);
  resize();

  return {
    available: () => Boolean(action) && canRender(),
    fetch(onHandoff, onComplete) {
      action.reset();
      fetchState = { start: performance.now(), yaw, pitch, onHandoff, onComplete, delivered: false };
      queueFrame();
    },
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      visibility.disconnect();
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      disposeModel(model);
      renderer.dispose();
      renderer.forceContextLoss();
    }
  };
}
