declare module "three/examples/jsm/loaders/GLTFLoader.js" {
  export type GLTF = {
    scene: object & {
      clone: (recursive?: boolean) => GLTF["scene"];
    };
  };

  export class GLTFLoader {
    load(
      url: string,
      onLoad: (gltf: GLTF) => void,
      onProgress?: ((event: ProgressEvent) => void) | undefined,
      onError?: ((error: unknown) => void) | undefined
    ): void;
  }
}
