import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: '../../api/openapi.yaml',
  output: 'src/api/generated',
  plugins: [
    '@hey-api/typescript',
    {
      name: '@hey-api/client-fetch',
      runtimeConfigPath: './src/api/client-config.ts',
      throwOnError: true,
    },
    {
      name: '@hey-api/sdk',
      operations: { strategy: 'flat' },
      responseStyle: 'data',
    },
  ],
})
