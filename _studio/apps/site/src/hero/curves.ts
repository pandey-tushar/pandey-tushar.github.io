/* The knot, as arithmetic. One source of truth for the build-time poster and
   the runtime scene, so the two cannot drift apart.

   fig8 is what the hero shows at rest; tref is what it morphs into on the
   first chapter. Both are lifted unchanged from the shipped page. */

export type Vec3 = [number, number, number];

export const fig8 = (t: number): Vec3 => [
  (2 + Math.cos(2 * t)) * Math.cos(3 * t),
  (2 + Math.cos(2 * t)) * Math.sin(3 * t),
  Math.sin(4 * t),
];

export const tref = (t: number): Vec3 => [
  Math.sin(t) + 2 * Math.sin(2 * t),
  Math.cos(t) - 2 * Math.cos(2 * t),
  -Math.sin(3 * t),
];

export interface Rest {
  fov: number;
  cameraZ: number;
  scale: number;
  offsetX: number;
  rotX: number;
  rotY: number;
  tubeRadius: number;
}

/* The scene at rest: the same numbers the reduced-motion branch of the live
   page settles on, so the poster is the frame the 3D would have drawn.
   Narrow viewports centre the knot and shrink it, exactly as the scene does
   below 900px. */
export const rest: Rest = {
  fov: 42,
  cameraZ: 9,
  scale: 0.95,
  offsetX: 2.2,
  rotX: 0.15,
  rotY: 0.6,
  tubeRadius: 0.3,
};

export const restNarrow: Rest = { ...rest, scale: 0.8, offsetX: 0 };

/** cyan to violet to magenta, the same ramp the tube shader walks */
export function ramp(u: number, stops: [Vec3, Vec3, Vec3]): Vec3 {
  const t = ((u % 1) + 1) % 1 * 2;
  const [a, b] = t < 1 ? [stops[0], stops[1]] : [stops[1], stops[2]];
  const k = t < 1 ? t : t - 1;
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
}

/** group transform then camera, matching the scene graph exactly */
export function place(p: Vec3, r: Rest = rest): Vec3 {
  const { scale, offsetX, rotX, rotY, cameraZ } = r;
  let [x, y, z] = [p[0] * scale, p[1] * scale, p[2] * scale];
  /* three's XYZ euler builds Rx * Ry * Rz, so the y turn is applied first */
  const cy = Math.cos(rotY), sy = Math.sin(rotY);
  [x, z] = [x * cy + z * sy, -x * sy + z * cy];
  const cx = Math.cos(rotX), sx = Math.sin(rotX);
  [y, z] = [y * cx - z * sx, y * sx + z * cx];
  return [x + offsetX, y, z - cameraZ];
}

/** view space to pixels; returns null behind the camera */
export function project(v: Vec3, w: number, h: number, r: Rest = rest): { x: number; y: number; d: number } | null {
  if (v[2] >= -0.05) return null;
  const f = 1 / Math.tan((r.fov * Math.PI) / 360);
  const d = -v[2];
  return { x: (((f * v[0]) / d / (w / h)) * 0.5 + 0.5) * w, y: (0.5 - (f * v[1]) / d / 2) * h, d };
}

/** projected stroke width of the tube at that depth, in pixels */
export const widthAt = (d: number, h: number, r: Rest = rest): number =>
  (r.tubeRadius * r.scale * (1 / Math.tan((r.fov * Math.PI) / 360)) * h) / d;
