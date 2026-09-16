import { readFileSync } from "node:fs";
export const pixel = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==",
  "base64",
);
// A deliberately tiny GLB fixture exercises asset lifecycle; it is not a car reconstruction.
export function fixtureGLB() {
  if (process.env.E2E_GLB_PATH) return readFileSync(process.env.E2E_GLB_PATH);
  const binary = Buffer.alloc(36);
  [-0.5, 0, 0, 0.5, 0, 0, 0, 0.6, 0].forEach((v, i) =>
    binary.writeFloatLE(v, i * 4),
  );
  const json = Buffer.from(
    JSON.stringify({
      asset: { version: "2.0" },
      scene: 0,
      scenes: [{ nodes: [0] }],
      nodes: [
        {
          name: "front_wing.fixture",
          mesh: 0,
          extras: { component: "front_wing" },
        },
      ],
      meshes: [{ primitives: [{ attributes: { POSITION: 0 }, material: 0 }] }],
      materials: [
        {
          pbrMetallicRoughness: { baseColorFactor: [0.7, 0.02, 0.04, 1] },
          doubleSided: true,
        },
      ],
      buffers: [{ byteLength: 36 }],
      bufferViews: [{ buffer: 0, byteLength: 36 }],
      accessors: [
        {
          bufferView: 0,
          componentType: 5126,
          count: 3,
          type: "VEC3",
          min: [-0.5, 0, 0],
          max: [0.5, 0.6, 0],
        },
      ],
    }),
  );
  const padded = Buffer.concat([
    json,
    Buffer.alloc((4 - (json.length % 4)) % 4, 32),
  ]);
  const header = Buffer.alloc(20);
  header.write("glTF");
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(28 + padded.length + 36, 8);
  header.writeUInt32LE(padded.length, 12);
  header.writeUInt32LE(0x4e4f534a, 16);
  const binHeader = Buffer.alloc(8);
  binHeader.writeUInt32LE(36);
  binHeader.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, padded, binHeader, binary]);
}
