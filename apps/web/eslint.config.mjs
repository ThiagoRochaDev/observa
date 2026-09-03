// eslint-config-next 16.x já exporta configs no formato flat nativo (ver
// node_modules/eslint-config-next/dist/index.d.ts: `Linter.Config[]`), então
// só espalha direto — NÃO usar `FlatCompat`/`.extends()` aqui: o compat trata
// o export como config no formato antigo (eslintrc) e quebra com "Converting
// circular structure to JSON" (bug de incompatibilidade entre FlatCompat e o
// export flat + `configs.flat` auto-referenciado do eslint-plugin-react).
import nextConfig from "eslint-config-next";

const eslintConfig = [
  ...nextConfig,
  {
    ignores: [".next/**", "node_modules/**"],
  },
];

export default eslintConfig;
