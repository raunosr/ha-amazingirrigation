import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

export default {
  input: "src/amazing-irrigation-card.ts",
  output: {
    file: "../custom_components/amazing_irrigation/frontend/amazing-irrigation-card.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [
    resolve(),
    typescript({ tsconfig: "./tsconfig.json", exclude: ["test/**"] }),
    terser(),
  ],
};
